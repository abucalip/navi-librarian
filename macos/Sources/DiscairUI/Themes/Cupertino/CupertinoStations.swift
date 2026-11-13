import DiscairLibrarian
import SwiftUI

/// The Radio page, mockup A2 "Tuner" (docs/design/macos-radio/mockups.html; docs/RADIO_PLAYBACK_PROPOSAL.md S2-1 item 7):
/// the title, the tag chips, the station list (logo, name, state in words, first tag, star) and the fixed On Air panel.
/// Nothing plays yet (live playback is S2-2), so a row click only selects it and the panel says so. Edit Tags (item 8) opens from a row's right-click menu.
struct CupertinoStations: View {
    let state: AppState
    @State private var selectedID: String?
    @State private var editingTags: RadioStation?

    init(state: AppState, selected: String? = nil) {
        self.state = state
        _selectedID = State(initialValue: selected)
    }

    private var model: StationsModel { state.stations }

    /// Below this content width the On Air panel moves under the list (S2.7).
    static let sideBySideWidth: CGFloat = 880
    static let panelWidth: CGFloat = 330

    var body: some View {
        GeometryReader { geo in
            let sideBySide = geo.size.width >= Self.sideBySideWidth
            VStack(alignment: .leading, spacing: CU.Space.m) {
                header
                if model.phase == .loaded, !model.isEmpty { chips }
                if let note = model.actionNote { noteLine(note) }
                content(sideBySide: sideBySide)
            }
            .padding(.horizontal, CU.Space.xl)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }

    // MARK: Header and chips

    private var header: some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            Text("Radio").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
            if let summary { Text(summary).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary) }
        }
        .padding(.top, CU.Space.xs)
    }

    private var summary: String? {
        guard model.phase == .loaded, !model.isEmpty else { return nil }
        let n = model.stations.count
        return n == 1 ? "1 station" : "\(n) stations"
    }

    private var chips: some View {
        HStack(spacing: 6) {
            ForEach(model.chips) { chip in
                let on = (chip.tag?.lowercased()) == model.tagFilter?.lowercased()
                Button { model.select(tag: chip.tag) } label: {
                    Text(chip.label).cuRole(CU.Font.callout)
                        .foregroundStyle(on ? CU.content : CU.textSecondary)
                        .padding(.horizontal, 11).padding(.vertical, 3)
                        .background(on ? CU.text : CU.bgFill, in: Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(chip.tag == nil ? "All stations" : "Tag \(chip.label)")
                .accessibilityAddTraits(on ? .isSelected : [])
            }
            Spacer(minLength: 0)
        }
    }

    private func noteLine(_ note: String) -> some View {
        Text(note).cuRole(CU.Font.callout).foregroundStyle(CU.danger).accessibilityLabel("Problem: \(note)")
    }

    // MARK: Body

    @ViewBuilder private func content(sideBySide: Bool) -> some View {
        switch model.phase {
        case .idle, .loading:
            Text("Reading the stations…").cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
        case .failed(let message, let retryable):
            VStack(alignment: .leading, spacing: CU.Space.s) {
                Text(message).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
                if retryable { Button("Try again") { Task { await model.reload() } }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true)) }
            }
            .padding(.top, CU.Space.s)
        case .loaded where model.isEmpty:
            Text("No stations yet. Add one in Navidrome and it appears here.")
                .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
        case .loaded:
            if sideBySide {
                HStack(alignment: .top, spacing: CU.Space.l) {
                    ScrollView { list.padding(.bottom, CU.Space.xl) }.scrollEdgeEffectStyle(.hard, for: .top)
                    OnAirPanel().frame(width: Self.panelWidth)
                }
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: CU.Space.m) { list; OnAirPanel() }.padding(.bottom, CU.Space.xl)
                }
                .scrollEdgeEffectStyle(.hard, for: .top)
            }
        }
    }

    private var list: some View {
        let shown = model.visibleStations
        return LazyVStack(spacing: 0) {
            ForEach(Array(shown.enumerated()), id: \.element.id) { i, station in
                let selected = station.id == selectedID
                let previousSelected = i > 0 && shown[i - 1].id == selectedID
                StationRow(station: station, status: model.status(for: station), selected: selected,
                           showsRule: i > 0 && !selected && !previousSelected,
                           select: { selectedID = station.id },
                           toggleFavourite: { Task { await model.setFavourite(station, on: !station.favourite) } },
                           editTags: { editingTags = station })
            }
        }
        .focusable()
        .onKeyPress(.downArrow) { move(by: 1, in: shown) }
        .onKeyPress(.upArrow) { move(by: -1, in: shown) }
        .sheet(item: $editingTags) { station in
            StationTagsSheet(station: station) { tags in Task { await model.setTags(station, to: tags) } }
        }
    }

    private func move(by step: Int, in shown: [RadioStation]) -> KeyPress.Result {
        guard !shown.isEmpty else { return .ignored }
        let current = shown.firstIndex { $0.id == selectedID }
        let next = min(max((current ?? (step > 0 ? -1 : shown.count)) + step, 0), shown.count - 1)
        selectedID = shown[next].id
        return .handled
    }
}

/// One station: logo 34 pt, name over a sentence, the first tag, the star. The playing (here: selected) row has the accent tint.
private struct StationRow: View {
    let station: RadioStation
    let status: StationRules.Status
    let selected: Bool
    let showsRule: Bool
    let select: () -> Void
    let toggleFavourite: () -> Void
    let editTags: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Button(action: select) {
                HStack(spacing: 10) {
                    StationLogo(station: station, size: 34)
                    VStack(alignment: .leading, spacing: 0) {
                        Text(station.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                        Text(status.text).cuRole(CU.Font.callout)
                            .foregroundStyle(statusColour).fontWeight(status.isLiveTitle ? .semibold : .regular).lineLimit(1)
                    }
                    Spacer(minLength: CU.Space.s)
                    if let tag = station.tags.first {
                        Text(tag).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                            .padding(.horizontal, 11).padding(.vertical, 3)
                            .background(CU.bgFill, in: Capsule())
                    }
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("\(station.name), \(status.text)")
            .accessibilityAddTraits(selected ? .isSelected : [])
            Button(action: toggleFavourite) {
                Image(systemName: station.favourite ? "star.fill" : "star").font(.system(size: 15))
                    .foregroundStyle(station.favourite ? CU.accent : CU.textTertiary).frame(width: 24, height: 24)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(station.favourite ? "Favourite, on" : "Favourite, off")
        }
        .padding(.horizontal, CU.Space.s).padding(.vertical, 6)
        .background(selected ? CU.accentTint : .clear, in: RoundedRectangle(cornerRadius: CU.Shell.rowRadius, style: .continuous))
        .overlay(alignment: .top) { if showsRule { Rectangle().fill(CU.separator).frame(height: 1) } }
        .contextMenu {
            Button("Edit Tags…", action: editTags)
            Button(station.favourite ? "Remove from Favourites" : "Add to Favourites", action: toggleFavourite)
        }
        .accessibilityAction(named: "Edit Tags", editTags)
    }

    private var statusColour: Color {
        if status.isLiveTitle { return CU.accent }
        if status.text == "Station unreachable" { return CU.danger }
        return CU.textSecondary
    }
}

/// The fixed panel on the right. Until live playback exists (S2-2) it only says nothing is playing.
private struct OnAirPanel: View {
    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text("On air").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
            Text("Nothing playing. Choose a station.").cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
        }
        .padding(14)
        .frame(maxWidth: .infinity, minHeight: 120, alignment: .topLeading)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .accessibilityElement(children: .combine)
    }
}

/// Edit Tags (E5): the station's tags as removable chips and a field. Return adds a tag, Save sends the whole list, Cancel closes.
struct StationTagsSheet: View {
    let station: RadioStation
    let save: ([String]) -> Void
    @State private var draft: TagDraft
    @Environment(\.dismiss) private var dismiss
    @FocusState private var fieldFocused: Bool

    init(station: RadioStation, save: @escaping ([String]) -> Void) {
        self.station = station
        self.save = save
        _draft = State(initialValue: TagDraft(tags: station.tags))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text("Edit tags").cuRole(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                Text(station.name).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
            }
            VStack(alignment: .leading, spacing: CU.Space.s) {
                FlowTags(tags: draft.tags) { tag in draft.remove(tag) }
                TextField(draft.isFull ? "The list is full" : "Add a tag, then press Return", text: $draft.typed)
                    .textFieldStyle(.plain).font(.system(size: CU.Font.body.size)).foregroundStyle(CU.text)
                    .focused($fieldFocused)
                    .onSubmit { draft.commitTyped(); fieldFocused = true }
                    .accessibilityLabel("New tag")
            }
            .padding(CU.Space.s)
            .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(CU.separator, lineWidth: 1))
            if let problem = draft.problem {
                Text(problem.message).cuRole(CU.Font.callout).foregroundStyle(CU.danger).accessibilityLabel("Problem: \(problem.message)")
            } else {
                Text("\(draft.countLine). Up to \(StationRules.maxTagLength) characters each.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            }
            HStack(spacing: CU.Space.s) {
                Spacer()
                Button("Cancel") { dismiss() }.buttonStyle(CapsuleButtonStyle()).keyboardShortcut(.cancelAction)
                Button("Save") {
                    if let tags = draft.result() { save(tags); dismiss() }
                }
                .buttonStyle(CapsuleButtonStyle(primary: true)).keyboardShortcut(.defaultAction)
            }
        }
        .padding(CU.Space.l)
        .frame(width: 400)
        .background(CU.bgPanel)
        .foregroundStyle(CU.text)
        .onAppear { fieldFocused = true }
    }
}

/// The tags so far, wrapping onto lines, each with a remove button.
private struct FlowTags: View {
    let tags: [String]
    let remove: (String) -> Void

    var body: some View {
        if tags.isEmpty {
            Text("No tags yet.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
        } else {
            WrapLayout(spacing: 6) {
                ForEach(tags, id: \.self) { tag in
                    HStack(spacing: 4) {
                        Text(tag).cuRole(CU.Font.callout).foregroundStyle(CU.text).lineLimit(1)
                        Button { remove(tag) } label: {
                            Image(systemName: "xmark").font(.system(size: 9, weight: .bold)).foregroundStyle(CU.textSecondary).frame(width: 14, height: 14)
                        }
                        .buttonStyle(.plain).accessibilityLabel("Remove tag \(tag)")
                    }
                    .padding(.horizontal, 8).padding(.vertical, 2)
                    .background(CU.bgFill, in: RoundedRectangle(cornerRadius: 6, style: .continuous))
                }
            }
        }
    }
}

/// A minimal left-to-right layout that wraps to the next line.
private struct WrapLayout: Layout {
    var spacing: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        arrange(in: proposal.width ?? .infinity, subviews).size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let laid = arrange(in: bounds.width, subviews)
        for (subview, origin) in zip(subviews, laid.origins) {
            subview.place(at: CGPoint(x: bounds.minX + origin.x, y: bounds.minY + origin.y), proposal: .unspecified)
        }
    }

    private func arrange(in width: CGFloat, _ subviews: Subviews) -> (origins: [CGPoint], size: CGSize) {
        var origins: [CGPoint] = []
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0, maxX: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > 0, x + size.width > width { x = 0; y += rowHeight + spacing; rowHeight = 0 }
            origins.append(CGPoint(x: x, y: y))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            maxX = max(maxX, x - spacing)
        }
        return (origins, CGSize(width: maxX, height: y + rowHeight))
    }
}
