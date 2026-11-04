import SwiftUI

/// Gap Radar in Zine's language: "Missing Issues", one strip per artist, owned covers solid and missing ones as dashed
/// hatched coupons with a Get. No mockup exists for this screen; it reuses the Artist page's parts. Missing picks carry
/// no year, so they follow the dated issues.
struct ZineGapRadar: View {
    let state: AppState
    private var lib: LibraryModel { state.library }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Gap Radar").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("Missing back issues, biggest gap first").padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            if lib.gapRadar.isEmpty {
                Mono(lib.gapLoading ? "Reading your artists…" : (lib.picksNote ?? "No gaps found: every recommended album by your artists is already here."))
            }
            ForEach(lib.gapRadar) { g in strip(g) }
        }
        .task { await state.loadGapRadar() }
    }

    private func strip(_ g: GapArtist) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Button { state.openArtist(named: g.name) } label: { Text(g.name).font(Z.an(30)).textCase(.uppercase).lineLimit(1) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(g.name)")
                Mono(g.summary)
                Spacer(minLength: 8)
                if g.missing.count > 1 {
                    Button("Get \(g.missing.count) missing") { state.getAllMissing(g) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                }
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 14) {
                    ForEach(g.dated + g.undatedOwned + g.undatedMissing) { a in issue(a) }
                }
                .padding(.trailing, 6).padding(.bottom, 6)
            }
        }
        .padding(.bottom, 10)
        .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 2) }
        .accessibilityElement(children: .contain)
    }

    private func issue(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            if a.owned {
                Button { state.open(album: a) } label: { ZineCover(album: a, width: 104) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            } else {
                VStack(spacing: 4) {
                    Mono("Missing")
                    Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                        .buttonStyle(ZineButtonStyle(kind: .yellow, small: true)).disabled(!state.acquisition.canGet(a))
                        .help(state.acquisition.detail(for: a)).accessibilityLabel("Get \(a.title)")
                }
                .frame(width: 104, height: 104)
                .background(Z.paper).zBorder(3, dashed: true)
            }
            Text(a.title).font(Z.an(13)).textCase(.uppercase).lineLimit(2).frame(width: 104, alignment: .leading)
            Mono(a.line([a.yearText, a.owned ? "" : "missing"]), size: 10)
        }
        .frame(width: 112, alignment: .leading)
    }
}
