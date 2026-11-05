import DiscairLibrarian
import SwiftUI

/// Discover: the Librarian's lists in the order it gives them (For you, Classics, New releases, Saved). No mockup
/// exists; it follows Cupertino's rules. Every row keeps Get, Save and Not for me as text buttons.
struct CupertinoDiscover: View {
    let state: AppState
    private var model: DiscoveryModel { state.discovery }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text("Discover").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                HStack(spacing: 8) {
                    ForEach(DiscoveryModel.Kind.allCases) { k in
                        let on = model.selected == k
                        Button(k.title) { model.selected = k; Task { await model.load(k) } }
                            .buttonStyle(CapsuleButtonStyle(primary: on, small: true))
                            .accessibilityAddTraits(on ? .isSelected : [])
                    }
                }
                content
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task { await model.load(model.selected) }
    }

    @ViewBuilder private var content: some View {
        let k = model.selected
        let p = model.page(k)
        let albums = state.visible(p.albums)
        switch p.phase {
        case .idle, .loading:
            HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Loading \(k.title)…") }.foregroundStyle(CU.muted).padding(.top, 8)
        case .failed(let m):
            VStack(alignment: .leading, spacing: 8) {
                Text(m).foregroundStyle(CU.muted)
                Button("Try again") { Task { await model.load(k, force: true) } }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
            }.padding(.top, 8)
        case .loaded:
            if albums.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text(p.message ?? "Nothing here.").foregroundStyle(CU.muted)
                    if k != .saved {
                        Button(p.building ? "Building…" : "Build this list") { Task { await model.build(k) } }
                            .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(p.building)
                    }
                }.padding(.top, 8)
            }
            ForEach(albums) { a in row(a) }
        }
    }

    private func row(_ a: AlbumItem) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Button { state.open(album: a) } label: {
                CoverView(album: a).frame(width: 84).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .shadow(color: .black.opacity(0.15), radius: 5, y: 3)
            }
            .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            VStack(alignment: .leading, spacing: 4) {
                Button { state.open(album: a) } label: { Text(a.title).font(.system(size: 16, weight: .semibold)).lineLimit(1) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
                Button(a.artist) { state.openArtist(named: a.artist) }.buttonStyle(.plain).foregroundStyle(CU.muted)
                if let r = a.reason { Text(r).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(2) }
                if !a.suggestedTracks.isEmpty {
                    Text("Try: " + a.suggestedTracks.prefix(3).joined(separator: ", ")).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
                }
                HStack(spacing: 6) {
                    Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.acquisition.canGet(a))
                        .help(state.acquisition.detail(for: a)).accessibilityHint(state.acquisition.detail(for: a))
                    Button(state.acquisition.isSaved(a) ? "Saved" : "Save") { state.actions.save(album: a) }
                        .buttonStyle(CapsuleButtonStyle(small: true)).disabled(state.acquisition.isSaved(a))
                    Button("Not for me") { state.actions.notForMe(album: a) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                }
                .padding(.top, 4)
            }
            Spacer(minLength: 0)
        }
        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .accessibilityElement(children: .contain)
    }
}
