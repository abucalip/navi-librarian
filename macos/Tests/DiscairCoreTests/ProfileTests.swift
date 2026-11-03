import Testing
import Foundation
@testable import DiscairCore

@Suite("Profiles") struct ProfileTests {
    func lan(_ name: String = "Home") throws -> Profile {
        try Profile(name: name, librarianURL: "http://192.168.1.87:8080", navidromeURL: "http://192.168.1.87:4533")
    }
    func tailscale(_ name: String = "Away") throws -> Profile {
        try Profile(name: name, librarianURL: "https://lib.tail1.ts.net", navidromeURL: "https://navi.tail1.ts.net")
    }

    @Test func inferredNetwork() throws {
        #expect(try lan().network == .lan)
        #expect(try tailscale().network == .tailscale)
        #expect(try Profile(name: "x", librarianURL: "https://lib.example.com", navidromeURL: "https://navi.example.com").network == .other)
        #expect(try Profile(name: "x", librarianURL: "http://100.64.1.1:8080", navidromeURL: "http://100.64.1.1:4533").network == .tailscale)
    }

    @Test func validation() throws {
        #expect(throws: ProfileError.emptyName) { try Profile(name: "  ", librarianURL: "https://a.example", navidromeURL: "https://b.example") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .publicHTTP)) {
            try Profile(name: "Bad", librarianURL: "http://example.com", navidromeURL: "https://b.example")
        }
        #expect(try lan().isUnencrypted)
        #expect(try !tailscale().isUnencrypted)
        #expect(try tailscale().usesTailscaleAddress)
        #expect(try !lan().usesTailscaleAddress)
    }

    @Test func duplicateNamesAreRejectedIgnoringCase() throws {
        var list = ProfileList()
        try list.add(try lan("Home"))
        #expect(throws: ProfileError.duplicateName) { try list.add(try tailscale("HOME")) }
    }

    @Test func probeOrderIsLanThenTailscaleThenOther() throws {
        var list = ProfileList()
        let other = try Profile(name: "Other", librarianURL: "https://lib.example.com", navidromeURL: "https://navi.example.com")
        try list.add(other); try list.add(try tailscale("Away")); try list.add(try lan("Home")); try list.add(try lan("Office"))
        #expect(list.probeOrder.map(\.name) == ["Home", "Office", "Away", "Other"])
    }

    @Test func removingTheOverrideProfileClearsTheOverride() throws {
        var list = ProfileList()
        let home = try lan(); try list.add(home); list.overrideID = home.id
        list.remove(id: home.id)
        #expect(list.overrideID == nil && list.profiles.isEmpty)
    }

    @Test func storeRoundTripAndTamperedFile() throws {
        let dir = FileManager.default.temporaryDirectory.appending(path: "discair-tests-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: dir) }
        let store = ProfileStore(fileURL: dir.appending(path: "profiles.json"))
        #expect(try store.load() == ProfileList())
        var list = ProfileList(); let home = try lan(); try list.add(home); list.overrideID = home.id
        try store.save(list)
        #expect(try store.load() == list)

        // A hand-edited file that points at a public http address must not load.
        let original = try String(contentsOf: store.fileURL, encoding: .utf8)
        let json = original.replacingOccurrences(of: "http://192.168.1.87:8080", with: "http://example.com")
        #expect(json != original)
        try json.write(to: store.fileURL, atomically: true, encoding: .utf8)
        #expect(throws: (any Error).self) { try store.load() }
    }

    @Test func profilesHoldNoSecrets() throws {
        let data = try JSONEncoder().encode(try lan())
        let text = String(decoding: data, as: UTF8.self).lowercased()
        #expect(!text.contains("password") && !text.contains("token"))
    }
}
