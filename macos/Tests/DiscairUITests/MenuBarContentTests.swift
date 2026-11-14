import DiscairAudio
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

/// S2-5: what the menu bar item says and which buttons its popover shows. The item itself in the real menu bar is not testable.
@MainActor
struct MenuBarContentTests {
    private func live(_ phase: LiveSession.Phase = .playing) -> LiveSession {
        LiveSession(stationID: "1", name: "FIP", logoPath: "", startedAt: Date(), phase: phase)
    }
    private let song = RadioNow(state: .ok, rawTitle: "Talk Talk - Life's What You Make It", artist: "Talk Talk", title: "Life's What You Make It", playID: 4)
    private func item(_ title: String, _ artist: String = "Portishead", album: String = "Dummy") -> QueueItem {
        QueueItem(songID: title, title: title, artist: artist, album: album)
    }

    @Test func aStationShowsTheRadioSymbolAndTheSong() {
        let c = MenuBarContent(live: live(), liveNow: song, current: nil, showTitle: true)
        #expect(c.kind == .station && c.symbol == "radio")
        #expect(c.labelTitle == "Talk Talk — Life's What You Make It".prefix(29) + "…" || c.labelTitle == "Talk Talk — Life's What You Make It")
        #expect(c.caption == "FIP" && c.headline == "Life's What You Make It" && c.detail == "Talk Talk")
    }

    @Test func aStationWithNoSongShowsItsName() {
        let c = MenuBarContent(live: live(), liveNow: RadioNow(state: .noMetadata), current: nil, showTitle: true)
        #expect(c.labelTitle == "FIP" && c.headline == "FIP" && c.detail == "This station sends no song titles.")
    }

    @Test func aLibrarySongShowsTheNoteAndArtistDashTitle() {
        let c = MenuBarContent(live: nil, liveNow: nil, current: item("Glory Box"), showTitle: true)
        #expect(c.kind == .song && c.symbol == "music.note")
        #expect(c.labelTitle == "Portishead — Glory Box")
        #expect(c.caption == "Dummy" && c.headline == "Glory Box" && c.detail == "Portishead")
    }

    @Test func nothingPlayingShowsTheNoteAndNoTitle() {
        let c = MenuBarContent(live: nil, liveNow: nil, current: nil, showTitle: true)
        #expect(c.kind == .idle && c.symbol == "music.note" && c.labelTitle == nil)
        #expect(!c.showsStop && !c.showsPlayPause && !c.showsNext && !c.showsDownload && !c.showsRetry)
    }

    @Test func showTitleOffLeavesTheSymbolAlone() {
        #expect(MenuBarContent(live: live(), liveNow: song, current: nil, showTitle: false).labelTitle == nil)
        #expect(MenuBarContent(live: nil, liveNow: nil, current: item("Glory Box"), showTitle: false).labelTitle == nil)
    }

    @Test func theTitleIsCutAtThirtyCharactersWithAnEllipsis() {
        let long = String(repeating: "a", count: 31)
        let cut = MenuBarContent.cut(long)
        #expect(cut.count == 30 && cut.hasSuffix("…"))
        #expect(MenuBarContent.cut(String(repeating: "a", count: 30)).count == 30)
        #expect(!MenuBarContent.cut(String(repeating: "a", count: 30)).hasSuffix("…"))
        #expect(MenuBarContent.cut("Short") == "Short")
        let c = MenuBarContent(live: live(), liveNow: song, current: nil, showTitle: true)
        #expect((c.labelTitle ?? "").count <= 30)
    }

    @Test func radioHasStopAndDownloadButNoNext() {
        let c = MenuBarContent(live: live(), liveNow: song, current: item("Ignored"), showTitle: true)
        #expect(c.showsStop && c.showsDownload)
        #expect(!c.showsPlayPause && !c.showsNext && !c.showsRetry)
    }

    @Test func aLibrarySongHasPlayPauseAndNextButNoStopOrDownload() {
        let c = MenuBarContent(live: nil, liveNow: nil, current: item("Glory Box"), showTitle: true)
        #expect(c.showsPlayPause && c.showsNext)
        #expect(!c.showsStop && !c.showsDownload && !c.showsRetry)
    }

    @Test func anUnreachableStationOffersRetryAndNoDownload() {
        let c = MenuBarContent(live: live(.unreachable), liveNow: song, current: nil, showTitle: true)
        #expect(c.showsRetry && c.showsStop && !c.showsDownload)
        #expect(c.headline == "FIP" && c.detail == "Station unreachable")
        #expect(c.labelTitle == "FIP")
    }

    @Test func aStationThatIsConnectingShowsTheNameNotAnOldSong() {
        let c = MenuBarContent(live: live(.connecting), liveNow: song, current: nil, showTitle: true)
        #expect(c.headline == "FIP" && c.detail == "Connecting…" && !c.showsDownload)
    }

    @Test func theSwitchesAreOnByDefault() {
        let defaults = UserDefaults(suiteName: "menubar-test-\(UUID().uuidString)")!
        #expect(defaults.object(forKey: MenuBarSettings.showKey) == nil)
        #expect(MenuBarSettings.showKey == "discair.menubar.show" && MenuBarSettings.showTitleKey == "discair.menubar.showTitle")
    }

    private func freshDefaults() -> UserDefaults { UserDefaults(suiteName: "menubar-vis-\(UUID().uuidString)")! }

    @Test func visibilityIsOnWhenNothingIsSaved() {
        #expect(MenuBarVisibility(defaults: freshDefaults()).isInserted)
    }

    @Test func visibilityWritesOnlyARealChange() {
        let defaults = freshDefaults()
        let v = MenuBarVisibility(defaults: defaults)
        v.isInserted = true   // what the scene writes back while it starts
        #expect(defaults.object(forKey: MenuBarSettings.showKey) == nil)
        v.isInserted = false
        #expect(defaults.bool(forKey: MenuBarSettings.showKey) == false)
    }

    @Test func visibilityFollowsTheSettingsSwitch() {
        let defaults = freshDefaults()
        let v = MenuBarVisibility(defaults: defaults)
        defaults.set(false, forKey: MenuBarSettings.showKey)   // Settings > Radio writes through @AppStorage
        v.refresh()
        #expect(!v.isInserted)
        defaults.removeObject(forKey: MenuBarSettings.showKey)
        v.refresh()
        #expect(v.isInserted)
    }
}
