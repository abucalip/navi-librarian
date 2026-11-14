import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

final class FakeRadioSettingsSource: RadioSettingsSource, @unchecked Sendable {
    private let lock = NSLock()
    private var _scrobbling = RadioScrobbling(enabled: false, configured: true)
    private var _appURL = "http://100.64.0.1:8689"
    private var _fail: DiscairError?
    private var _failRead: DiscairError?
    private var _calls: [String] = []
    var scrobbling: RadioScrobbling { get { lock.withLock { _scrobbling } } set { lock.withLock { _scrobbling = newValue } } }
    var appURL: String { get { lock.withLock { _appURL } } set { lock.withLock { _appURL = newValue } } }
    var fail: DiscairError? { get { lock.withLock { _fail } } set { lock.withLock { _fail = newValue } } }
    var failRead: DiscairError? { get { lock.withLock { _failRead } } set { lock.withLock { _failRead = newValue } } }
    var calls: [String] { lock.withLock { _calls } }
    private func note(_ s: String) { lock.withLock { _calls.append(s) } }

    func radioScrobbling() async throws -> RadioScrobbling { note("get scrobbling"); if let e = failRead { throw e }; return scrobbling }
    func setRadioScrobbling(_ on: Bool) async throws -> RadioScrobbling {
        note("set scrobbling \(on)")
        if let e = fail { throw e }
        scrobbling = RadioScrobbling(enabled: on, configured: scrobbling.configured)
        return scrobbling
    }
    func radioSettings() async throws -> RadioSettings { note("get settings"); if let e = failRead { throw e }; return RadioSettings(appURL: appURL) }
    func uploadRadioLogo(station: String, data: Data, contentType: String) async throws {
        note("upload \(station) \(data.count) \(contentType)")
        if let e = fail { throw e }
    }
    func resetRadioLogo(station: String) async throws { note("reset \(station)"); if let e = fail { throw e } }
}

@MainActor
@Suite("Radio settings model") struct RadioSettingsModelTests {
    func make() -> (RadioSettingsModel, FakeRadioSettingsSource) {
        let source = FakeRadioSettingsSource()
        let model = RadioSettingsModel()
        model.configure(source: source)
        return (model, source)
    }

    @Test func loadingReadsTheSwitchAndTheAddress() async {
        let (m, s) = make()
        #expect(m.phase == .idle && m.appAddressText == "…")
        s.scrobbling = RadioScrobbling(enabled: true, configured: true)
        await m.load()
        #expect(m.phase == .loaded && m.scrobblingOn && m.canSwitchScrobbling)
        #expect(m.appAddressText == "http://100.64.0.1:8689")
    }

    @Test func aBlankAddressReadsNotSet() async {
        let (m, s) = make()
        s.appURL = ""
        await m.load()
        #expect(m.appAddressText == "Not set")
    }

    @Test func withoutLastFmTheSwitchIsDisabledWithTheReason() async {
        let (m, s) = make()
        s.scrobbling = RadioScrobbling(enabled: false, configured: false)
        await m.load()
        #expect(!m.canSwitchScrobbling && m.scrobblingDetail == "Last.fm is not set up on the server")
        await m.setScrobbling(true)
        #expect(!s.calls.contains("set scrobbling true") && !m.scrobblingOn)       // nothing is sent
    }

    @Test func turningTheSwitchOnIsSentAndKept() async {
        let (m, s) = make()
        await m.load()
        await m.setScrobbling(true)
        #expect(s.calls.last == "set scrobbling true" && m.scrobblingOn && m.note == nil)
    }

    @Test func aRefusalPutsTheSwitchBackAndKeepsTheServersSentence() async {
        let (m, s) = make()
        await m.load()
        s.fail = .server(status: 409, message: "Last.fm needs to be set up first.")
        await m.setScrobbling(true)
        #expect(!m.scrobblingOn && m.note == "Last.fm needs to be set up first.")
        s.fail = nil
        await m.setScrobbling(true)
        #expect(m.scrobblingOn && m.note == nil)
    }

    @Test func aFailedReadSaysSoAndNeverShowsAnAddress() async {
        let (m, s) = make()
        s.failRead = .server(status: 500, message: nil)
        await m.load()
        guard case .failed(let text) = m.phase else { Issue.record("expected a failure"); return }
        #expect(!text.isEmpty && !text.contains("100.64"))
        #expect(m.appURL == nil)
    }

    @Test func changingALogoSendsTheImageAndTellsTheLogoStore() async {
        let (m, s) = make()
        var told: [String] = []
        m.onLogoChanged = { told.append($0) }
        await m.changeLogo(station: "7", image: Data(repeating: 1, count: 1000), contentType: "image/png")
        #expect(s.calls == ["upload 7 1000 image/png"] && told == ["7"] && m.note == nil)
    }

    @Test func anImageOverTwoMegabytesIsNotSent() async {
        let (m, s) = make()
        var told: [String] = []
        m.onLogoChanged = { told.append($0) }
        await m.changeLogo(station: "7", image: Data(count: radioLogoUploadLimit + 1))
        #expect(s.calls.isEmpty && told.isEmpty && m.note == "The image is too large. Choose one up to 2 MB.")
        await m.changeLogo(station: "7", image: Data(count: radioLogoUploadLimit))
        #expect(s.calls.count == 1)                                                     // exactly 2 MB is allowed
        await m.changeLogo(station: "7", image: Data())
        #expect(m.note == "The image is empty.")
    }

    @Test func aRefusedLogoKeepsTheOldOneAndSaysWhy() async {
        let (m, s) = make()
        var told: [String] = []
        m.onLogoChanged = { told.append($0) }
        s.fail = .server(status: 415, message: "That is not an image the server can use.")
        await m.changeLogo(station: "7", image: Data(count: 10))
        #expect(told.isEmpty && m.note == "That is not an image the server can use." && m.busyLogos.isEmpty)
    }

    @Test func resetClearsTheOverrideAndTellsTheLogoStore() async {
        let (m, s) = make()
        var told: [String] = []
        m.onLogoChanged = { told.append($0) }
        await m.resetLogo(station: "3")
        #expect(s.calls == ["reset 3"] && told == ["3"])
        s.fail = .server(status: 404, message: nil)
        await m.resetLogo(station: "4")
        #expect(told == ["3"] && m.note != nil)
    }

    @Test func disconnectingForgetsEverything() async {
        let (m, _) = make()
        await m.load()
        m.configure(source: nil)
        #expect(m.phase == .idle && m.scrobbling == nil && m.appURL == nil)
    }
}
