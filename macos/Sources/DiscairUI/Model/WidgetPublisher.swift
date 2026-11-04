import AppKit
import DiscairAudio
import DiscairCore
import Foundation
import WidgetKit

/// Hands the playing song to the Notification Center widget: writes `NowPlayingSnapshot` (and a small cover) to the
/// shared folder and asks WidgetKit to redraw. Called from `SystemMedia.update()`, so it sees every change the media keys
/// see. The widget moves its own progress bar from the position and the time it was written, so nothing is written on
/// every tick; only a new song, play or pause, a seek, or a cover that has just arrived.
@MainActor
final class WidgetPublisher {
    private let folder: URL
    private let reload: () -> Void
    private var last: NowPlayingSnapshot?
    private var lastCoverID: String?
    /// Widget covers are small: the largest widget shows it at about 160 points.
    nonisolated static let coverPixels = 320

    init(folder: URL = NowPlayingShare.defaultFolder,
         reload: @escaping () -> Void = { WidgetCenter.shared.reloadTimelines(ofKind: NowPlayingShare.widgetKind) }) {
        self.folder = folder
        self.reload = reload
    }

    /// `item` nil, or nothing loaded, clears the widget.
    func publish(item: QueueItem?, duration: Double, position: Double, playing: Bool, cover: NSImage?) {
        guard let item else {
            guard last != nil else { return }
            NowPlayingShare.clear(in: folder); last = nil; lastCoverID = nil
            reload()
            return
        }
        let coverJPEG = cover.flatMap { Self.jpeg($0) }
        let coverKey = coverJPEG == nil ? nil : item.coverArt
        let snap = NowPlayingSnapshot(title: item.title, artist: item.artist, album: item.album, duration: duration,
                                      position: position, isPlaying: playing, coverFile: coverJPEG == nil ? nil : NowPlayingShare.coverName)
        if let last, last.sameState(as: snap), lastCoverID == coverKey { return }
        do {
            try NowPlayingShare.write(snap, cover: coverJPEG, in: folder)
            last = snap; lastCoverID = coverKey
            reload()
        } catch {
            // The widget is a convenience; a full disk or a locked folder must never reach playback.
        }
    }

    nonisolated static func jpeg(_ image: NSImage) -> Data? {
        guard let tiff = image.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff) else { return nil }
        let longest = max(rep.pixelsWide, rep.pixelsHigh)
        guard longest > 0 else { return nil }
        let scale = min(1, Double(coverPixels) / Double(longest))
        let w = max(1, Int(Double(rep.pixelsWide) * scale)), h = max(1, Int(Double(rep.pixelsHigh) * scale))
        guard let out = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                                         hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0),
              let ctx = NSGraphicsContext(bitmapImageRep: out) else { return nil }
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = ctx
        image.draw(in: NSRect(x: 0, y: 0, width: w, height: h), from: .zero, operation: .copy, fraction: 1)
        NSGraphicsContext.restoreGraphicsState()
        return out.representation(using: .jpeg, properties: [.compressionFactor: 0.8])
    }
}
