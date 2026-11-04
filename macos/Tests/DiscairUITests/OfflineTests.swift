import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
import AppKit
import SwiftUI
@testable import DiscairUI

private final class ToggleTransport: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var on = true
    var online: Bool { get { lock.withLock { on } } set { lock.withLock { on = newValue } } }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        guard online else { throw URLError(.cannotConnectToHost) }
        let body: String
        switch request.url!.lastPathComponent {
        case "getAlbumList2": body = #""albumList2":{"album":[{"id":"al-1","name":"Laughing Stock","artist":"Talk Talk","artistId":"ar-1","year":1991}]}"#
        case "getArtists": body = #""artists":{"index":[{"artist":[{"id":"ar-1","name":"Talk Talk","albumCount":1}]}]}"#
        case "getAlbum": body = #""album":{"id":"al-1","name":"Laughing Stock","song":[{"id":"s1","title":"Myrrhman","duration":412,"suffix":"flac"}]}"#
        case "getArtist": body = #""artist":{"id":"ar-1","name":"Talk Talk","album":[{"id":"al-1","name":"Laughing Stock","artist":"Talk Talk","year":1991}]}"#
        case "search3": body = #""searchResult3":{"song":[{"id":"s1","title":"Myrrhman","artist":"Talk Talk"}]}"#
        default: body = ""
        }
        let json = #"{"subsonic-response":{"status":"ok","version":"1.16.1",\#(body)}}"#
        return (Data(json.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

private func tempRoot() -> URL { FileManager.default.temporaryDirectory.appending(path: "discair-pages-\(UUID().uuidString)") }

private func client(_ t: ToggleTransport) throws -> NavidromeClient {
    try NavidromeClient(baseURL: URL(string: "https://navi.example.ts.net")!, credential: Credential(username: "o", password: "pw"), transport: t)
}

struct PageCacheTests {
    @Test func savesAndReadsBackWithTheSaveTime() {
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        let c = PageCache(root: tempRoot(), scope: "a", now: { t0 })
        c.put("home", ["x", "y"])
        let hit = c.get("home", as: [String].self)
        #expect(hit?.value == ["x", "y"] && hit?.savedAt == t0)
        #expect(c.get("other", as: [String].self) == nil)
    }

    @Test func anotherScopeNeverReadsIt() {
        let root = tempRoot()
        PageCache(root: root, scope: "a").put("home", [1])
        #expect(PageCache(root: root, scope: "b").get("home", as: [Int].self) == nil)
    }

    @Test func keysCannotEscapeTheFolder() {
        let root = tempRoot()
        let c = PageCache(root: root, scope: "a")
        c.put("../../evil", [1])
        let names = (try? FileManager.default.contentsOfDirectory(atPath: c.directory.path)) ?? []
        #expect(names.count == 1 && names[0].hasSuffix(".json") && !names[0].contains(".."))
    }

    @Test func clearRemovesEveryScope() {
        let root = tempRoot()
        PageCache(root: root, scope: "a").put("home", [1]); PageCache(root: root, scope: "b").put("home", [1])
        PageCache(root: root, scope: "a").clear()
        #expect(PageCache(root: root, scope: "b").get("home", as: [Int].self) == nil)
    }

    @Test func oldestFilesGoWhenThereAreTooMany() {
        let c = PageCache(root: tempRoot(), scope: "a")
        for i in 0..<(PageCache.maxFiles + 5) { c.put("k\(i)", [i]) }
        let n = (try? FileManager.default.contentsOfDirectory(atPath: c.directory.path).count) ?? 0
        #expect(n <= PageCache.maxFiles)
    }
}

@MainActor
struct OfflineLibraryTests {
    @Test func aDroppedServerKeepsTheLibraryFromTheSavedCopy() async throws {
        let t = ToggleTransport(), root = tempRoot()
        let m = LibraryModel(); m.configureCache(scope: "u", root: root)
        let nav = try client(t)
        await m.load(navidrome: nav, librarian: nil)
        #expect(m.phase == .loaded && m.savedCopyDate == nil && m.recent.map(\.title) == ["Laughing Stock"])
        t.online = false
        let again = LibraryModel(); again.configureCache(scope: "u", root: root)    // a fresh launch with no network
        await again.load(navidrome: nav, librarian: nil)
        #expect(again.phase == .loaded && again.recent.map(\.title) == ["Laughing Stock"])
        #expect(again.savedCopyDate != nil && again.savedCopyReason == DiscairError.serverUnreachable.summary)
        t.online = true
        await again.load(navidrome: nav, librarian: nil)
        #expect(again.savedCopyDate == nil)                                            // a good read clears the notice
    }

    @Test func withNothingSavedTheFailureIsShown() async throws {
        let t = ToggleTransport(); t.online = false
        let m = LibraryModel(); m.configureCache(scope: "u", root: tempRoot())
        await m.load(navidrome: try client(t), librarian: nil)
        #expect(m.phase == .failed(DiscairError.serverUnreachable.summary) && m.savedCopyDate == nil)
    }

    @Test func aRefusedLoginIsNotTreatedAsOffline() async throws {
        let root = tempRoot()
        let seed = LibraryModel(); seed.configureCache(scope: "u", root: root)
        await seed.load(navidrome: try client(ToggleTransport()), librarian: nil)
        let m = LibraryModel(); m.configureCache(scope: "u", root: root)
        m.fallBackForTest(.unauthorised(message: nil))
        #expect(m.savedCopyDate == nil)
        if case .failed = m.phase {} else { Issue.record("expected a failure") }
    }

    @Test func albumArtistAndSongPagesFallBackToTheirSavedCopies() async throws {
        let t = ToggleTransport(), root = tempRoot()
        let m = LibraryModel(); m.configureCache(scope: "u", root: root)
        let nav = try client(t)
        await m.load(navidrome: nav, librarian: nil)
        await m.loadTracks(for: m.recent[0], navidrome: nav)
        await m.loadArtist(m.artists[0], navidrome: nav)
        await m.loadSongs(navidrome: nav)
        t.online = false
        let off = LibraryModel(); off.configureCache(scope: "u", root: root)
        await off.load(navidrome: nav, librarian: nil)
        await off.loadTracks(for: off.recent[0], navidrome: nav)
        #expect(off.tracks.map(\.title) == ["Myrrhman"])
        await off.loadArtist(off.artists[0], navidrome: nav)
        #expect(off.artistOwnedCount == 1)
        await off.loadSongs(navidrome: nav)
        #expect(off.songs.map(\.title) == ["Myrrhman"] && off.songsError == nil)
    }

    @Test func signOutDeletesTheSavedPages() async throws {
        let root = tempRoot()
        let m = LibraryModel(); m.configureCache(scope: "u", root: root)
        await m.load(navidrome: try client(ToggleTransport()), librarian: nil)
        m.clearSavedPages()
        let other = LibraryModel(); other.configureCache(scope: "u", root: root)
        #expect(!other.showSavedCopy(reason: "x"))
    }
}

@MainActor
struct OfflineBannerTests {
    @Test func noticeNamesTheReasonAndTheAgeAndBothThemesRenderIt() async throws {
        let t = ToggleTransport(), root = tempRoot()
        let state = AppState(themeID: .cupertino, screen: .home)
        #expect(state.offlineNotice == nil)
        state.library.configureCache(scope: "u", root: root)
        await state.library.load(navidrome: try client(t), librarian: nil)
        #expect(state.offlineNotice == nil)                       // fresh data: no banner
        t.online = false
        await state.library.load(navidrome: try client(t), librarian: nil)
        let notice = try #require(state.offlineNotice)
        #expect(notice.hasPrefix("Offline. The server did not answer.") && notice.contains("saved"))
        for theme in ThemeID.allCases {
            state.themeID = theme
            let host = NSHostingView(rootView: OfflineBanner(state: state, text: notice).frame(width: 900))
            host.frame = NSRect(x: 0, y: 0, width: 900, height: 60)
            #expect(host.fittingSize.height > 20, "\(theme)")
        }
    }
}
