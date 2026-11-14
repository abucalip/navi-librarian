import AppKit
import DiscairCore
import SwiftUI
import WidgetKit

/// The Notification Center widget (contract section 10): now playing only, no buttons. The app writes the song to a shared
/// folder (`NowPlayingShare`) and asks WidgetKit to redraw; clicking the widget opens Discair.
@main
struct DiscairWidgetBundle: WidgetBundle {
    var body: some Widget { NowPlayingWidget() }
}

struct NowPlayingWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: NowPlayingShare.widgetKind, provider: NowPlayingProvider()) { entry in
            NowPlayingView(entry: entry)
                .containerBackground(for: .widget) { NowPlayingBackdrop(entry: entry) }
        }
        .configurationDisplayName("Now Playing")
        .description("The song playing in Discair.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

struct NowPlayingEntry: TimelineEntry {
    let date: Date
    let snapshot: NowPlayingSnapshot?
    let cover: NSImage?
}

struct NowPlayingProvider: TimelineProvider {
    private static let sample = NowPlayingSnapshot(title: "Such a Shame", artist: "Talk Talk", album: "It's My Life",
                                                   duration: 245, position: 80, isPlaying: false)

    func placeholder(in context: Context) -> NowPlayingEntry { NowPlayingEntry(date: Date(), snapshot: Self.sample, cover: nil) }

    func getSnapshot(in context: Context, completion: @escaping (NowPlayingEntry) -> Void) {
        completion(context.isPreview ? placeholder(in: context) : Self.entry(at: Date()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<NowPlayingEntry>) -> Void) {
        let now = Date()
        var entries = [Self.entry(at: now)]
        // A song that "plays" past its end means the app is gone: show the idle face then.
        if let end = entries[0].snapshot?.expectedEnd, end > now {
            entries.append(NowPlayingEntry(date: end, snapshot: nil, cover: nil))
        }
        // The app reloads the timeline on every change; nothing else needs to wake the widget.
        completion(Timeline(entries: entries, policy: .never))
    }

    static func entry(at now: Date, folder: URL = NowPlayingShare.defaultFolder) -> NowPlayingEntry {
        guard let snap = NowPlayingShare.read(in: folder) else { return NowPlayingEntry(date: now, snapshot: nil, cover: nil) }
        if let end = snap.expectedEnd, end <= now { return NowPlayingEntry(date: now, snapshot: nil, cover: nil) }
        let cover = NowPlayingShare.coverData(for: snap, in: folder).flatMap { NSImage(data: $0) }
        return NowPlayingEntry(date: now, snapshot: snap, cover: cover)
    }
}

// MARK: Views

private let accent = Color(red: 1.0, green: 0.30, blue: 0.42)   // the app's red-pink

struct NowPlayingBackdrop: View {
    let entry: NowPlayingEntry
    var body: some View {
        ZStack {
            Color(red: 0.09, green: 0.09, blue: 0.10)
            if let cover = entry.cover {
                Image(nsImage: cover).resizable().scaledToFill().blur(radius: 30).opacity(0.55)
            }
        }
    }
}

struct NowPlayingView: View {
    @Environment(\.widgetFamily) private var family
    let entry: NowPlayingEntry

    var body: some View {
        if let snap = entry.snapshot {
            switch family {
            case .systemMedium: medium(snap)
            default: small(snap)
            }
        } else {
            idle
        }
    }

    private func small(_ s: NowPlayingSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .top) {
                CoverView(image: entry.cover, corner: 8).frame(width: 56, height: 56)
                Spacer(minLength: 0)
                if s.live { LiveBadge() } else { StateGlyph(playing: s.isPlaying) }
            }
            Spacer(minLength: 0)
            Text(s.title).font(.system(size: 14, weight: .bold)).lineLimit(2).foregroundStyle(.white)
            if !s.artist.isEmpty { Text(s.artist).font(.system(size: 12)).lineLimit(1).foregroundStyle(.white.opacity(0.7)) }
        }
    }

    private func medium(_ s: NowPlayingSnapshot) -> some View {
        HStack(spacing: 14) {
            CoverView(image: entry.cover, corner: 10).aspectRatio(1, contentMode: .fit)
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    StateGlyph(playing: s.isPlaying)
                    Text(s.live ? "ON AIR" : s.isPlaying ? "NOW PLAYING" : "PAUSED")
                        .font(.system(size: 10, weight: .semibold)).tracking(0.8).foregroundStyle(.white.opacity(0.6))
                }
                Spacer(minLength: 0)
                Text(s.title).font(.system(size: 17, weight: .bold)).lineLimit(2).foregroundStyle(.white)
                // A station with a known song carries the artist and the station name in the same fields (S2-3 item 1).
                if !s.artist.isEmpty { Text(s.artist).font(.system(size: 13)).lineLimit(1).foregroundStyle(.white.opacity(0.8)) }
                if !s.album.isEmpty { Text(s.album).font(.system(size: 12)).lineLimit(1).foregroundStyle(.white.opacity(0.55)) }
                Spacer(minLength: 0)
                // A station has no length: LIVE takes the place of the progress bar.
                if s.live { LiveBadge() } else { progress(s) }
            }
        }
    }

    @ViewBuilder private func progress(_ s: NowPlayingSnapshot) -> some View {
        if let range = s.progressInterval(at: entry.date) {
            if s.isPlaying {
                // WidgetKit animates this itself between redraws.
                ProgressView(timerInterval: range, countsDown: false) { EmptyView() } currentValueLabel: { EmptyView() }
                    .progressViewStyle(.linear).tint(accent)
            } else {
                ProgressView(value: s.position(at: entry.date), total: s.duration).progressViewStyle(.linear).tint(accent.opacity(0.7))
            }
        }
    }

    private var idle: some View {
        VStack(spacing: 6) {
            Image(systemName: "music.note").font(.system(size: 26, weight: .semibold)).foregroundStyle(accent)
            Text("Nothing playing").font(.system(size: 13, weight: .semibold)).foregroundStyle(.white)
            if family == .systemMedium {
                Text("Start a song in Discair.").font(.system(size: 12)).foregroundStyle(.white.opacity(0.6))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct CoverView: View {
    let image: NSImage?
    let corner: CGFloat
    var body: some View {
        Group {
            if let image { Image(nsImage: image).resizable().scaledToFill() }
            else {
                ZStack {
                    Color.white.opacity(0.08)
                    Image(systemName: "music.note").foregroundStyle(.white.opacity(0.5))
                }
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: corner, style: .continuous))
    }
}

/// The LIVE mark (white plate, red text) as the app draws it on the player bar and the mini player.
struct LiveBadge: View {
    var body: some View {
        Text("LIVE").font(.system(size: 10.5, weight: .bold)).tracking(0.8)
            .foregroundStyle(Color(red: 0.70, green: 0.07, blue: 0.24))
            .padding(.horizontal, 6).padding(.vertical, 1)
            .background(.white, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
            .accessibilityLabel("Live")
    }
}

struct StateGlyph: View {
    let playing: Bool
    var body: some View {
        Image(systemName: playing ? "waveform" : "pause.fill")
            .font(.system(size: 11, weight: .bold)).foregroundStyle(accent)
    }
}
