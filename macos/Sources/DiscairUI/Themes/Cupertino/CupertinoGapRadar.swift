import SwiftUI

/// Gap Radar (contract 6.4): artists you own albums of that have albums missing, each on a year axis with the owned
/// ones solid and the missing ones dashed with a Get. The order is the biggest gap first. Mockup: the artist screen's
/// radar (`R.cupertino.artist`), given a screen of its own. Missing picks carry no year, so they follow a divider.
struct CupertinoGapRadar: View {
    let state: AppState
    private var lib: LibraryModel { state.library }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Gap Radar").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                Text("Artists you own, with the albums the Librarian says are missing.").foregroundStyle(CU.muted)
                if lib.gapRadar.isEmpty {
                    Text(lib.gapLoading ? "Reading your artists…" : (lib.picksNote ?? "No gaps found: every recommended album by your artists is already here."))
                        .foregroundStyle(CU.muted).padding(.top, 8)
                }
                ForEach(lib.gapRadar) { artist in card(artist) }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task { await state.loadGapRadar() }
    }

    private func card(_ g: GapArtist) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Button { state.openArtist(named: g.name) } label: { Text(g.name).font(CU.title(22)).lineLimit(1) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(g.name)")
                Text(g.summary).foregroundStyle(CU.muted)
                Spacer(minLength: 8)
                ProgressView(value: g.completeness).frame(width: 90).tint(CU.accent).accessibilityHidden(true)
                if g.missing.count > 1 {
                    Button("Get \(g.missing.count) missing") { state.getAllMissing(g) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                }
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 14) {
                    ForEach(g.dated) { a in tile(a) }
                    if !g.undatedOwned.isEmpty || !g.undatedMissing.isEmpty {
                        Rectangle().fill(CU.muted.opacity(0.3)).frame(width: 1, height: 96).padding(.horizontal, 4)
                            .accessibilityHidden(true)
                        ForEach(g.undatedOwned + g.undatedMissing) { a in tile(a) }
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .padding(16)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .contain)
    }

    private func tile(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Button { if a.owned { state.open(album: a) } } label: {
                CoverView(album: a).frame(width: 96).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .opacity(a.owned ? 1 : 0.35)
                    .overlay { if !a.owned { RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(Color(white: 0.53), style: StrokeStyle(lineWidth: 2, dash: [5, 4])).padding(-3) } }
            }
            .buttonStyle(.plain).accessibilityLabel(a.owned ? "Open \(a.title)" : "\(a.title), missing")
            Text(a.title).font(.system(size: 12, weight: .semibold)).lineLimit(1)
            Text(a.owned ? (a.yearText.isEmpty ? "Owned" : a.yearText) : (a.year > 0 ? "\(a.yearText) · Missing" : "Missing"))
                .font(.system(size: 11)).foregroundStyle(CU.muted).lineLimit(1)
            if !a.owned {
                Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                    .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.acquisition.canGet(a))
                    .help(state.acquisition.detail(for: a))
            }
        }
        .frame(width: 96, alignment: .leading)
    }
}
