import DiscairLibrarian
import SwiftUI

/// The Radio page, mockup A2 "Tuner" (docs/design/macos-radio/mockups.html; docs/RADIO_PLAYBACK_PROPOSAL.md S2-1 item 7):
/// the title, the tag chips, the station list (logo, name, state in words, first tag, star) and the fixed On Air panel.
/// Nothing plays yet (live playback is S2-2), so a row click only selects it and the panel says so. Edit Tags is item 8.
struct CupertinoStations: View {
    let state: AppState
    @State private var selectedID: String?

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
                           toggleFavourite: { Task { await model.setFavourite(station, on: !station.favourite) } })
            }
        }
        .focusable()
        .onKeyPress(.downArrow) { move(by: 1, in: shown) }
        .onKeyPress(.upArrow) { move(by: -1, in: shown) }
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
