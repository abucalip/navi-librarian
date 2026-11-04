import DiscairCore
import Foundation
import Testing
@testable import DiscairUI

private final class FakeMounter: ShareMounter, @unchecked Sendable {
    private let lock = NSLock()
    private var _calls: [(URL, String?)] = []
    private var _passwords: [String] = []
    var outcome: ShareMountOutcome = .mounted
    /// Called when a mount "succeeds", so a test can make the folder appear.
    var onMount: (@Sendable () -> Void)?
    var calls: [(URL, String?)] { lock.withLock { _calls } }
    func mount(_ address: URL, credential: Credential?) async -> ShareMountOutcome {
        lock.withLock { _calls.append((address, credential?.username)) }
        if outcome == .mounted { onMount?() }
        return outcome
    }
}

private final class Folder: @unchecked Sendable {
    private let lock = NSLock()
    private var _there = false
    var there: Bool { get { lock.withLock { _there } } set { lock.withLock { _there = newValue } } }
}

@MainActor
@Suite struct ShareModelTests {
    private func make(enabled: Bool = true, address: String = "smb://192.168.1.87/media",
                      mounter: FakeMounter = FakeMounter(), folder: Folder = Folder(),
                      secrets: InMemorySecretStore = InMemorySecretStore()) -> (ShareModel, FakeMounter, Folder) {
        let defaults = UserDefaults(suiteName: "share-test-\(UUID().uuidString)")!
        let m = ShareModel(defaults: defaults, secrets: secrets, mounter: mounter, folderExists: { _ in folder.there })
        m.save(address: address, serverRoot: "/music", localRoot: "/Volumes/media/library/music")
        if enabled { m.setEnabledWithoutMounting() }
        return (m, mounter, folder)
    }

    @Test func offByDefaultAndNeverMounts() async {
        let m = ShareModel(defaults: UserDefaults(suiteName: "share-test-\(UUID().uuidString)")!,
                           secrets: InMemorySecretStore(), mounter: FakeMounter(), folderExists: { _ in false })
        #expect(m.status == .off && !m.settings.enabled)
        await m.mountNow()
        #expect(m.status == .off)
    }

    @Test func mountsWithTheSavedLoginAndBecomesReadyWhenTheFolderAppears() async throws {
        let secrets = InMemorySecretStore()
        let (m, mounter, folder) = make(secrets: secrets)
        try m.saveLogin(username: "nas", password: "pw")
        mounter.onMount = { folder.there = true }
        await m.mountNow()
        #expect(m.status == .ready && m.isReady)
        #expect(mounter.calls.count == 1 && mounter.calls[0].1 == "nas")
        #expect(mounter.calls[0].0.absoluteString == "smb://192.168.1.87/media")
    }

    @Test func anAlreadyMountedFolderIsNotMountedAgain() async {
        let (m, mounter, folder) = make()
        folder.there = true
        await m.mountNow()
        #expect(m.status == .ready && mounter.calls.isEmpty)
    }

    @Test func aFailureTurnsSMBOffQuietlyWithAReason() async {
        let (m, mounter, _) = make()
        mounter.outcome = .failed(.loginRefused)
        await m.mountNow()
        #expect(m.status == .unavailable(ShareMountFailure.loginRefused.summary))
        #expect(!m.isReady && m.statusLine.contains("Playback is not affected"))
    }

    @Test func mountedButWrongFolderIsReportedNotTrusted() async {
        let (m, _, _) = make()      // mount "succeeds" but the folder never appears
        await m.mountNow()
        guard case .unavailable(let why) = m.status else { Issue.record("expected unavailable"); return }
        #expect(why.contains("/Volumes/media/library/music"))
    }

    @Test func noAddressMeansNeedsAddress() async {
        let (m, mounter, _) = make(address: "")
        await m.mountNow()
        #expect(m.status == .needsAddress && mounter.calls.isEmpty)
    }

    @Test func badAddressOrRootsAreRefusedAndNotSaved() {
        let (m, _, _) = make()
        m.save(address: "http://nas/media", serverRoot: "/music", localRoot: "/Volumes/x")
        #expect(m.settingsError != nil && m.settings.address == "smb://192.168.1.87/media")
        m.save(address: "smb://nas/media", serverRoot: "music", localRoot: "/Volumes/x")
        #expect(m.settingsError != nil && m.settings.serverRoot == "/music")
        m.save(address: "smb://me:pw@nas/media", serverRoot: "/music", localRoot: "/Volumes/x")
        #expect(m.settingsError?.contains("username and password") == true)
    }

    @Test func settingsAreRemembered() {
        let defaults = UserDefaults(suiteName: "share-test-\(UUID().uuidString)")!
        let a = ShareModel(defaults: defaults, secrets: InMemorySecretStore(), mounter: FakeMounter(), folderExists: { _ in false })
        a.save(address: "smb://h/s", serverRoot: "/music", localRoot: "/Volumes/s/m")
        let b = ShareModel(defaults: defaults, secrets: InMemorySecretStore(), mounter: FakeMounter(), folderExists: { _ in false })
        #expect(b.settings.address == "smb://h/s" && b.settings.localRoot == "/Volumes/s/m")
    }

    @Test func theLoginNeverLandsInTheStoredSettings() throws {
        let defaults = UserDefaults(suiteName: "share-test-\(UUID().uuidString)")!
        let m = ShareModel(defaults: defaults, secrets: InMemorySecretStore(), mounter: FakeMounter(), folderExists: { _ in false })
        try m.saveLogin(username: "nas-user", password: "hunter2-secret")
        m.save(address: "smb://h/s", serverRoot: "/music", localRoot: "/Volumes/s/m")
        let raw = String(data: defaults.data(forKey: "discair.libraryShare") ?? Data(), encoding: .utf8) ?? ""
        #expect(!raw.contains("hunter2") && !raw.contains("nas-user"))
        #expect(m.username == "nas-user")
        #expect(throws: SettingsError.emptyLogin) { try m.saveLogin(username: "", password: "x") }
    }

    @Test func wrongPathShapesKeepSMBOffWithAHint() async {
        let (m, _, folder) = make()
        folder.there = true
        await m.mountNow()
        m.noteServerPaths(["AM (Jewel Case)/01-01 - Do I Wanna Know?.flac"])
        #expect(m.pathHint != nil && !m.isReady)
        #expect(m.localURL(forServerPath: "/music/a/b.flac") == nil)
        m.noteServerPaths(["/music/a/b.flac"])
        #expect(m.pathHint == nil && m.isReady)
        #expect(m.localURL(forServerPath: "/music/a/b.flac")?.path == "/Volumes/media/library/music/a/b.flac")
        #expect(m.localURL(forServerPath: "/music/../b.flac") == nil)
    }

    @Test func profileChangeDoesNotRemountAShareThatIsUp() async {
        let (m, mounter, folder) = make()
        folder.there = true
        await m.mountNow()
        m.startIfNeeded()
        try? await Task.sleep(for: .milliseconds(50))
        #expect(mounter.calls.isEmpty)
    }
}
