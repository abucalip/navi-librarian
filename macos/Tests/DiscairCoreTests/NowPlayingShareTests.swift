import Foundation
import Testing
@testable import DiscairCore

@Suite struct NowPlayingShareTests {
    private func folder() -> URL { FileManager.default.temporaryDirectory.appending(path: "np-\(UUID().uuidString)") }
    private let t0 = Date(timeIntervalSince1970: 1_000)

    private func snap(playing: Bool = true, position: Double = 30) -> NowPlayingSnapshot {
        NowPlayingSnapshot(title: "Such a Shame", artist: "Talk Talk", album: "It's My Life",
                           duration: 240, position: position, isPlaying: playing, updatedAt: t0)
    }

    @Test func positionMovesWhilePlayingAndStaysWhenPaused() {
        #expect(snap().position(at: t0.addingTimeInterval(10)) == 40)
        #expect(snap(playing: false).position(at: t0.addingTimeInterval(10)) == 30)
    }

    @Test func positionIsClampedToTheSong() {
        #expect(snap().position(at: t0.addingTimeInterval(1_000)) == 240)
        #expect(snap().position(at: t0.addingTimeInterval(-50)) == 30)   // a clock set back never rewinds
    }

    @Test func progressIntervalSpansTheWholeSong() throws {
        let now = t0.addingTimeInterval(10)
        let r = try #require(snap().progressInterval(at: now))
        #expect(r.lowerBound == now.addingTimeInterval(-40))
        #expect(r.upperBound.timeIntervalSince(r.lowerBound) == 240)
        var unknown = snap(); unknown.duration = 0
        #expect(unknown.progressInterval(at: now) == nil)
    }

    @Test func expectedEndOnlyWhilePlayingWithALength() {
        #expect(snap().expectedEnd == t0.addingTimeInterval(215))      // 240 - 30 left, plus 5 s of grace
        #expect(snap(playing: false).expectedEnd == nil)
        var unknown = snap(); unknown.duration = 0
        #expect(unknown.expectedEnd == nil)
    }

    @Test func sameStateIgnoresTheClockButNotASeekOrPause() {
        var later = snap(position: 40); later.updatedAt = t0.addingTimeInterval(10)
        #expect(snap().sameState(as: later))
        var seeked = snap(position: 120); seeked.updatedAt = t0.addingTimeInterval(10)
        #expect(!snap().sameState(as: seeked))
        var paused = later; paused.isPlaying = false
        #expect(!snap().sameState(as: paused))
    }

    @Test func writeThenReadRoundTripsWithCover() throws {
        let dir = folder(); defer { try? FileManager.default.removeItem(at: dir) }
        try NowPlayingShare.write(snap(), cover: Data([1, 2, 3]), in: dir)
        let back = try #require(NowPlayingShare.read(in: dir))
        #expect(back.title == "Such a Shame")
        #expect(back.coverFile == NowPlayingShare.coverName)
        #expect(NowPlayingShare.coverData(for: back, in: dir) == Data([1, 2, 3]))
    }

    @Test func clearRemovesBothFilesAndReadIsNil() throws {
        let dir = folder(); defer { try? FileManager.default.removeItem(at: dir) }
        try NowPlayingShare.write(snap(), cover: Data([1]), in: dir)
        NowPlayingShare.clear(in: dir)
        #expect(NowPlayingShare.read(in: dir) == nil)
        #expect(!FileManager.default.fileExists(atPath: dir.appending(path: NowPlayingShare.coverName).path))
    }

    @Test func aCoverNameFromTheFileIsNotFollowedOutsideTheFolder() throws {
        let dir = folder(); defer { try? FileManager.default.removeItem(at: dir) }
        var s = snap(); s.coverFile = "../../secret"
        #expect(NowPlayingShare.coverData(for: s, in: dir) == nil)
    }

    @Test func garbageOrMissingFileReadsAsNil() throws {
        let dir = folder(); defer { try? FileManager.default.removeItem(at: dir) }
        #expect(NowPlayingShare.read(in: dir) == nil)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try Data("not json".utf8).write(to: dir.appending(path: NowPlayingShare.snapshotName))
        #expect(NowPlayingShare.read(in: dir) == nil)
    }

    // MARK: Live station (S2-2 item 7)

    private func liveSnap() -> NowPlayingSnapshot {
        NowPlayingSnapshot(title: "FIP", artist: "", album: "", duration: 0, position: 0, isPlaying: true, updatedAt: t0, isLive: true)
    }

    @Test func aSnapshotWrittenBeforeRadioStillDecodesAsASong() throws {
        let old = #"{"title":"Such a Shame","artist":"Talk Talk","album":"It's My Life","duration":240,"position":30,"isPlaying":true,"updatedAt":0}"#
        let snap = try JSONDecoder().decode(NowPlayingSnapshot.self, from: Data(old.utf8))
        #expect(snap.isLive == nil && !snap.live)
        #expect(snap.title == "Such a Shame")
    }

    @Test func aLiveSnapshotSurvivesTheRoundTrip() throws {
        let dir = folder(); defer { try? FileManager.default.removeItem(at: dir) }
        try NowPlayingShare.write(liveSnap(), cover: nil, in: dir)
        let back = try #require(NowPlayingShare.read(in: dir))
        #expect(back.live && back.title == "FIP" && back.duration == 0)
        #expect(back.progressInterval(at: t0) == nil)
    }

    @Test func aLiveSnapshotExpiresAfterSixHoursWithoutAnUpdate() {
        #expect(liveSnap().expectedEnd == t0.addingTimeInterval(NowPlayingSnapshot.liveLifetime))
        #expect(NowPlayingSnapshot.liveLifetime == 6 * 3600)
    }

    @Test func aStationAndASongAreNeverTheSameState() {
        var song = liveSnap(); song.isLive = nil
        #expect(!liveSnap().sameState(as: song))
        #expect(liveSnap().sameState(as: liveSnap()))
    }
}
