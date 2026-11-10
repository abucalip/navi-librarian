import DiscairLibrarian
import SwiftUI

/// Discover: "The Classifieds". No mockup exists; it uses Zine's parts. The lists keep the Librarian's order, and
/// every entry keeps Get, Save and Not for me as text buttons.
struct ZineDiscover: View {
    let state: AppState
    private var model: DiscoveryModel { state.discovery }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Discover").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("The Classifieds").padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            HStack(spacing: 10) {
                ForEach(DiscoveryModel.Kind.allCases) { k in
                    let on = model.selected == k
                    Button(k.title) { model.selected = k; Task { await model.load(k) } }
                        .buttonStyle(ZineButtonStyle(kind: on ? .yellow : .plain, small: true))
                        .accessibilityAddTraits(on ? .isSelected : [])
                }
            }
            content
        }
        .task { await model.load(model.selected) }
    }

    @ViewBuilder private var content: some View {
        let k = model.selected
        let p = model.page(k)
        let albums = state.visible(p.albums)
        switch p.phase {
        case .idle, .loading: Mono("Loading \(k.title)…")
        case .failed(let m):
            VStack(alignment: .leading, spacing: 8) {
                Text(m).font(Z.serif(14))
                Button("Try again") { Task { await model.load(k, force: true) } }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
            }
        case .loaded:
            if albums.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text(p.message ?? "Nothing here.").font(Z.serif(14))
                    if k != .saved {
                        Button(p.building ? "Building…" : "Build this list") { Task { await model.build(k) } }
                            .buttonStyle(ZineButtonStyle(kind: .yellow, small: true)).disabled(p.building)
                    }
                }
            }
            ForEach(albums) { a in row(a) }
        }
    }

    private func row(_ a: AlbumItem) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Button { state.open(album: a) } label: { CoverView(album: a).frame(width: 84).zBorder(3) }
                .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            VStack(alignment: .leading, spacing: 5) {
                Button { state.open(album: a) } label: { Text(a.title).font(Z.an(22)).textCase(.uppercase).lineLimit(1) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
                Button { state.openArtist(named: a.artist) } label: { Mono(a.artist, bold: true) }.buttonStyle(ZineLinkStyle())
                if let r = a.reason { Text(r).font(Z.serif(13)).lineLimit(2) }
                if !a.suggestedTracks.isEmpty { Mono("Try: " + a.suggestedTracks.prefix(3).joined(separator: ", "), size: 10).lineLimit(1) }
                DiscoverPeek(album: a, hovered: state.discovery.hoveredAlbum == a.id)
                HStack(spacing: 8) {
                    Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                        .buttonStyle(ZineButtonStyle(kind: .yellow, small: true)).disabled(!state.acquisition.canGet(a))
                        .help(state.acquisition.detail(for: a)).accessibilityHint(state.acquisition.detail(for: a))
                    Button(state.acquisition.isSaved(a) ? "Saved" : "Save") { state.actions.save(album: a) }
                        .buttonStyle(ZineButtonStyle(small: true)).disabled(state.acquisition.isSaved(a))
                    Button("Not for me") { state.actions.notForMe(album: a) }.buttonStyle(ZineButtonStyle(small: true))
                }
                .padding(.top, 3)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
        .background(Z.white).zBorder(3)
        .onHover { on in
            let model = state.discovery
            if on { model.hoveredAlbum = a.id } else if model.hoveredAlbum == a.id { model.hoveredAlbum = nil }
        }
        .accessibilityElement(children: .contain)
    }
}
