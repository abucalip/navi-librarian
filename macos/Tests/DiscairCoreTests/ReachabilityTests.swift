import Testing
import Foundation
@testable import DiscairCore

struct FakeProber: Prober {
    let outcomes: [String: ProbeOutcome]   // keyed by host
    let log: ProbeLog
    func probe(_ url: URL) async -> ProbeOutcome {
        log.add(url.host ?? "")
        return outcomes[url.host ?? ""] ?? .failed(.serverUnreachable)
    }
}
final class ProbeLog: @unchecked Sendable {
    private let lock = NSLock(); private var hosts: [String] = []
    func add(_ h: String) { lock.withLock { hosts.append(h) } }
    var all: [String] { lock.withLock { hosts } }
}

let wifi = NetworkInterface(name: "en0", isUp: true, addresses: ["192.168.1.20", "fe80::1"])
let loopback = NetworkInterface(name: "lo0", isUp: true, isLoopback: true, addresses: ["127.0.0.1"])
let tsUp = NetworkInterface(name: "utun4", isUp: true, addresses: ["100.101.102.103", "fd7a:115c:a1e0::1234"])

@Suite("Tailscale detection") struct TailscaleDetectorTests {
    @Test func detectsAnUpUtunWithATailscaleAddress() {
        #expect(TailscaleDetector.isConnected([wifi, loopback, tsUp]))
        #expect(TailscaleDetector.isConnected([NetworkInterface(name: "utun2", isUp: true, addresses: ["fd7a:115c:a1e0:ab12::1"])]))
    }
    @Test func ignoresLookAlikes() {
        #expect(!TailscaleDetector.isConnected([wifi, loopback]))
        #expect(!TailscaleDetector.isConnected([NetworkInterface(name: "utun4", isUp: false, addresses: ["100.101.102.103"])]))
        #expect(!TailscaleDetector.isConnected([NetworkInterface(name: "en5", isUp: true, addresses: ["100.101.102.103"])]))
        #expect(!TailscaleDetector.isConnected([NetworkInterface(name: "utun3", isUp: true, addresses: ["10.8.0.2"])]))
        #expect(!TailscaleDetector.isConnected([NetworkInterface(name: "utun3", isUp: true, addresses: ["fe80::1", "100.63.0.1"])]))
    }
    @Test func anyNetwork() {
        #expect(TailscaleDetector.hasAnyNetwork([wifi, loopback]))
        #expect(!TailscaleDetector.hasAnyNetwork([loopback]))
        #expect(!TailscaleDetector.hasAnyNetwork([NetworkInterface(name: "en0", isUp: false, addresses: ["192.168.1.20"])]))
        #expect(!TailscaleDetector.hasAnyNetwork([NetworkInterface(name: "en0", isUp: true, addresses: ["169.254.3.4", "fe80::1"])]))
        #expect(!TailscaleDetector.hasAnyNetwork([]))
    }
    @Test func systemReadDoesNotCrash() {
        #expect(NetworkInterfaces.current().contains { $0.isLoopback })
    }
}

@Suite("Profile selection") struct ProfileResolverTests {
    let home = try! Profile(name: "Home", librarianURL: "http://192.168.1.87:8080", navidromeURL: "http://192.168.1.87:4533")
    let away = try! Profile(name: "Away", librarianURL: "https://lib.t1.ts.net", navidromeURL: "https://navi.t1.ts.net")

    func resolver(_ up: Set<String>, nics: [NetworkInterface], log: ProbeLog = ProbeLog()) -> ProfileResolver {
        let outcomes = Dictionary(uniqueKeysWithValues: up.map { ($0, ProbeOutcome.reachable) })
        return ProfileResolver(prober: FakeProber(outcomes: outcomes, log: log), interfaces: { nics })
    }
    var both: ProfileList { var l = ProfileList(); try! l.add(away); try! l.add(home); return l }

    @Test func lanWinsWhenBothAreUp() async throws {
        let log = ProbeLog()
        let r = resolver(["192.168.1.87", "lib.t1.ts.net", "navi.t1.ts.net"], nics: [wifi, tsUp], log: log)
        let sel = try await r.select(from: both)
        #expect(sel.profile == home && !sel.isManualOverride)
        #expect(!log.all.contains("lib.t1.ts.net"))
    }
    @Test func fallsBackToTailscale() async throws {
        let r = resolver(["lib.t1.ts.net", "navi.t1.ts.net"], nics: [wifi, tsUp])
        #expect(try await r.select(from: both).profile == away)
    }
    @Test func bothServersMustAnswer() async throws {
        let r = resolver(["lib.t1.ts.net"], nics: [wifi, tsUp])
        await #expect(throws: DiscairError.serverUnreachable) { try await r.select(from: both) }
    }
    @Test func tailscaleNotConnectedIsReportedWithoutProbingIt() async {
        let log = ProbeLog()
        let r = resolver([], nics: [wifi], log: log)   // LAN down, Tailscale interface absent
        await #expect(throws: DiscairError.tailscaleNotConnected) { try await r.select(from: both) }
        #expect(!log.all.contains("lib.t1.ts.net"))
    }
    @Test func unreachableWhenNoTailscaleProfileExists() async {
        var l = ProfileList(); try! l.add(home)
        let r = resolver([], nics: [wifi])
        await #expect(throws: DiscairError.serverUnreachable) { try await r.select(from: l) }
    }
    @Test func noNetwork() async {
        let r = resolver(["192.168.1.87"], nics: [loopback])
        await #expect(throws: DiscairError.noNetwork) { try await r.select(from: both) }
    }
    @Test func manualOverrideSkipsProbing() async throws {
        let log = ProbeLog()
        var l = both; l.overrideID = away.id
        let r = resolver(["192.168.1.87"], nics: [wifi], log: log)
        let sel = try await r.select(from: l)
        #expect(sel.profile == away && sel.isManualOverride && log.all.isEmpty)
    }
    @Test func overrideThatNoLongerExists() async {
        var l = both; l.overrideID = UUID()
        await #expect(throws: ProfileError.notFound) { try await resolver([], nics: [wifi]).select(from: l) }
    }
    @Test func checkReportsTheSpecificFailure() async {
        #expect(await resolver([], nics: [wifi]).check(away) == .tailscaleNotConnected)
        #expect(await resolver([], nics: [loopback]).check(home) == .noNetwork)
        #expect(await resolver(["192.168.1.87"], nics: [wifi]).check(home) == nil)
        #expect(await resolver([], nics: [wifi]).check(home) == .serverUnreachable)
    }
}
