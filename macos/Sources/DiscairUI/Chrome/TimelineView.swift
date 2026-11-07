import DiscairLibrarian
import SwiftUI

/// The timeline (Phase 7 client gate): one artist's albums and events down a year (or decade) rail, oldest first. Albums
/// you own are in colour; anything not in the library is white with a dashed border (the rule of the graph and the atlas).
/// An item with no stated date is never placed: it waits behind "show" at the bottom.
struct TimelineView: View {
    let state: AppState
    let style: GraphStyle
    private var timeline: TimelineModel { state.timeline }

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                header
                if let note = timeline.note { Text(note).foregroundStyle(style.muted).padding(.top, 4) }
                rail
                footer
            }
            .padding(.horizontal, 28).padding(.bottom, 20)
            inspector.frame(width: 290)
        }
        .task { await state.loadTimeline() }
    }

    // MARK: Header and footer

    private var header: some View {
        @Bindable var t = timeline
        return HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text("Timeline").font(style.title).lineLimit(1).accessibilityAddTraits(.isHeader)
            if let person = timeline.person { Text(person.name).font(.system(size: 12, weight: .semibold)).foregroundStyle(style.muted) }
            Spacer()
            if timeline.loading { ProgressView().controlSize(.small) }
            Picker("Group by", selection: $t.byDecade) { Text("By year").tag(false); Text("By decade").tag(true) }
                .pickerStyle(.segmented).frame(width: 190).labelsHidden()
        }
        .padding(.top, 4)
    }

    private var footer: some View {
        HStack(spacing: 14) {
            Label("In library: colour", systemImage: "circle.fill")
            Label("Not in library: dashed", systemImage: "circle.dashed")
            Text("Dates are as MusicBrainz states them · nothing is dated from a file tag")
            Spacer()
            if timeline.truncated { Text("Showing the first items only.") }
        }
        .labelStyle(.titleAndIcon).font(.system(size: 11)).foregroundStyle(style.muted)
    }

    // MARK: Rail

    private var rail: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 8) {
                ForEach(timeline.groups) { group in
                    ForEach(Array(group.items.enumerated()), id: \.element.id) { index, item in
                        row(item, label: index == 0 ? group.label : nil)
                    }
                }
                if !timeline.undated.isEmpty { undatedBlock }
            }
        }
        .frame(maxWidth: .infinity, minHeight: 420, maxHeight: .infinity)
    }

    private func row(_ item: TimelineItem, label: String?) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Text(label ?? "").font(.system(size: 16, weight: .bold)).monospacedDigit().foregroundStyle(style.ink)
                .frame(width: 64, alignment: .trailing)
            card(item)
        }
    }

    private func card(_ item: TimelineItem) -> some View {
        let owned = item.owned
        let picked = item.id == timeline.selectedID
        return Button { timeline.selectedID = item.id } label: {
            VStack(alignment: .leading, spacing: 3) {
                Text(item.entity.name).font(.system(size: 14, weight: .semibold)).lineLimit(2)
                Text([item.kind == "event" ? (item.eventKind ?? "event") : "album", owned ? "owned" : "not in library",
                      TimelineGrouping.display(item.date)].joined(separator: " · "))
                    .font(.system(size: 11)).foregroundStyle(style.muted)
                if item.cancelled { Text("cancelled").font(.system(size: 11, weight: .semibold)).foregroundStyle(style.muted) }
            }
            .padding(10).frame(maxWidth: .infinity, alignment: .leading)
            .background(owned ? style.accent.opacity(0.14) : style.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .strokeBorder(picked ? style.accent : style.ink.opacity(owned ? 0.15 : 0.5),
                                  style: StrokeStyle(lineWidth: picked ? 3 : 1.5, dash: owned ? [] : [4, 3]))
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(item.entity.name), \(TimelineGrouping.display(item.date)), \(owned ? "in your library" : "not in your library")")
    }

    @ViewBuilder private var undatedBlock: some View {
        @Bindable var t = timeline
        HStack(alignment: .top, spacing: 14) {
            Text("?").font(.system(size: 16, weight: .bold)).foregroundStyle(style.muted).frame(width: 64, alignment: .trailing)
            VStack(alignment: .leading, spacing: 6) {
                Button { t.showsUndated.toggle() } label: {
                    Text("\(timeline.undated.count) item\(timeline.undated.count == 1 ? "" : "s") with no stated date · \(timeline.showsUndated ? "hide" : "show")")
                        .font(.system(size: 13)).underline()
                }
                .buttonStyle(.plain).foregroundStyle(style.muted)
                if timeline.showsUndated { ForEach(timeline.undated) { card($0) } }
            }
        }
    }

    // MARK: Inspector

    private var inspector: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                if let item = timeline.selected { selectedPanel(item) } else { idlePanel }
            }
            .padding(18)
        }
        .background(style.card)
    }

    private var idlePanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Timeline").font(.system(size: 18, weight: .bold))
            Text("Choose an album or event to see why it is here and where the date comes from.").foregroundStyle(style.muted)
            if let cov = timeline.coverage {
                Text(cov == "loaded" ? "MusicBrainz data: loaded." : "MusicBrainz data: not on the server yet.").font(.system(size: 11)).foregroundStyle(style.muted)
            }
        }
    }

    @ViewBuilder private func selectedPanel(_ item: TimelineItem) -> some View {
        Text(item.entity.name).font(.system(size: 18, weight: .bold))
        Text([TimelineGrouping.display(item.date), item.owned ? "owned" : "not in library"].joined(separator: " · "))
            .font(.system(size: 12)).foregroundStyle(style.muted)
        if !item.why.isEmpty {
            VStack(alignment: .leading, spacing: 3) {
                Text("Why here").font(.system(size: 12, weight: .semibold))
                Text(item.why).font(.system(size: 12))
                ForEach(Array(item.evidence.enumerated()), id: \.offset) { _, e in
                    Text("\(e.source) · \(e.evidenceClass) · \(e.matchQuality)").font(.system(size: 10)).foregroundStyle(style.muted)
                }
            }
            .padding(10).frame(maxWidth: .infinity, alignment: .leading)
            .background(.background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        if item.kind == "album", item.owned, let album = GraphNodeFace.ownedAlbum(item.entity.name, library: state.library) {
            Button("Open album") { state.open(album: album) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
        }
        if !timeline.notLoadedText.isEmpty { Text(timeline.notLoadedText).font(.system(size: 11)).foregroundStyle(style.muted) }
    }
}
