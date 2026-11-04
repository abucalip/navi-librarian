import Foundation
import Testing
@testable import DiscairCore

@Suite struct LibraryShareTests {
    @Test func acceptsAPlainShareAddress() throws {
        #expect(try ShareAddress.validate(" smb://192.168.1.87/media ").absoluteString == "smb://192.168.1.87/media")
        #expect(try ShareAddress.validate("SMB://nas.local/music").host == "nas.local")
    }

    @Test func refusesBadAddresses() {
        #expect(throws: ShareAddressError.notAnSMBAddress) { try ShareAddress.validate("http://nas/media") }
        #expect(throws: ShareAddressError.notAnSMBAddress) { try ShareAddress.validate("") }
        #expect(throws: ShareAddressError.notAnSMBAddress) { try ShareAddress.validate("smb:///media") }
        #expect(throws: ShareAddressError.missingShare) { try ShareAddress.validate("smb://nas") }
        #expect(throws: ShareAddressError.missingShare) { try ShareAddress.validate("smb://nas/media/library") }
        #expect(throws: ShareAddressError.missingShare) { try ShareAddress.validate("smb://nas/media?x=1") }
        #expect(throws: ShareAddressError.embeddedCredentials) { try ShareAddress.validate("smb://me:pw@nas/media") }
        #expect(throws: ShareAddressError.embeddedCredentials) { try ShareAddress.validate("smb://me@nas/media") }
    }

    private let mapper = SongPathMapper(serverRoot: "/music", localRoot: "/Volumes/media/library/music")!

    @Test func mapsServerPathsToTheMount() {
        #expect(mapper.map("/music/Pink Floyd/The Wall/01 In The Flesh_.flac")
                == .local(URL(fileURLWithPath: "/Volumes/media/library/music/Pink Floyd/The Wall/01 In The Flesh_.flac")))
    }

    @Test func rootsIgnoreATrailingSlash() {
        let m = SongPathMapper(serverRoot: "/music/", localRoot: "/Volumes/media/library/music/")!
        #expect(m.serverRoot == "/music" && m.localRoot == "/Volumes/media/library/music")
        #expect(m.map("/music/a/b.flac") == .local(URL(fileURLWithPath: "/Volumes/media/library/music/a/b.flac")))
    }

    @Test func aRebuiltNameIsNotGuessed() {
        // Navidrome without "Report Real Path": Artist/Album/disc-track - Title.ext
        #expect(mapper.map("AM (Jewel Case)/01-01 - Do I Wanna Know?.flac") == .unsafe)
        #expect(mapper.map("/other/a/b.flac") == .outsideServerRoot)
    }

    @Test func aSiblingFolderWithTheSamePrefixDoesNotMatch() {
        #expect(mapper.map("/musical/a/b.flac") == .outsideServerRoot)
        #expect(mapper.map("/music") == .outsideServerRoot)
        #expect(mapper.map("/music/") == .unsafe)
    }

    @Test func traversalAndOddNamesAreRefused() {
        #expect(mapper.map("/music/../etc/passwd") == .unsafe)
        #expect(mapper.map("/music/a/../../b.flac") == .unsafe)
        #expect(mapper.map("/music/a//b.flac") == .unsafe)
        #expect(mapper.map("/music/./b.flac") == .unsafe)
        #expect(mapper.map("/music/a/b\0.flac") == .unsafe)
    }

    @Test func unusableRootsAreRefused() {
        #expect(SongPathMapper(serverRoot: "music", localRoot: "/Volumes/x") == nil)
        #expect(SongPathMapper(serverRoot: "/", localRoot: "/Volumes/x") == nil)
        #expect(SongPathMapper(serverRoot: "/music", localRoot: "/Volumes/../x") == nil)
        #expect(SongPathMapper(serverRoot: "", localRoot: "/Volumes/x") == nil)
    }

    @Test func detectsReportRealPathBeingOff() {
        #expect(mapper.looksRight(["/music/a/b.flac"]))
        #expect(!mapper.looksRight(["AM/01 - x.flac", "Artist/Album/02 - y.mp3"]))
        #expect(!mapper.looksRight([]))
    }

    @Test func mountFailuresAreNamedWithoutAddressesOrLogins() {
        #expect(ShareMountFailure.from(status: 80) == .loginRefused)
        #expect(ShareMountFailure.from(status: 13) == .loginRefused)
        #expect(ShareMountFailure.from(status: 2) == .shareNotFound)
        #expect(ShareMountFailure.from(status: 60) == .timedOut)
        #expect(ShareMountFailure.from(status: 65) == .unreachable)
        #expect(ShareMountFailure.from(status: 9999) == .other(9999))
        for f in [ShareMountFailure.loginRefused, .shareNotFound, .unreachable, .timedOut, .other(5)] {
            #expect(!f.summary.contains("smb://") && !f.summary.isEmpty)
        }
    }

    @Test func settingsRoundTripAndDefaultsAreOff() throws {
        let d = ShareSettings()
        #expect(!d.enabled && d.address.isEmpty && d.serverRoot == "/music" && d.localRoot == "/Volumes/media/library/music")
        let back = try JSONDecoder().decode(ShareSettings.self, from: JSONEncoder().encode(ShareSettings(enabled: true, address: "smb://h/s")))
        #expect(back.enabled && back.address == "smb://h/s")
    }

    @Test func theShareLoginHasItsOwnSlot() throws {
        let store = InMemorySecretStore()
        try store.save(Credential(username: "nas", password: "pw1"), for: .smb)
        try store.save(Credential(username: "navi", password: "pw2"), for: .navidrome)
        #expect(try store.credential(for: .smb)?.username == "nas")
        try store.delete(.smb)
        #expect(try store.credential(for: .smb) == nil)
        #expect(try store.credential(for: .navidrome)?.username == "navi")
    }
}
