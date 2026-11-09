import DiscairLibrarian
import SwiftUI

/// The Paths sheet of an album or an artist: a segmented control of paths, the server's steps as a table in its own order,
/// and a trailing inspector with the selected step's reasons. Plain system styling so it reads the same under every theme,
/// like the sonic path sheet.
struct PathsSheet: View {
    let state: AppState
    @Bindable var model: PathsSheetModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                Text(model.heading).font(.title2.bold()).lineLimit(1).accessibilityAddTraits(.isHeader)
                Picker("Path", selection: Binding(get: { model.tabID }, set: { model.choose($0); state.loadPathsTab() })) {
                    ForEach(model.tabLabels, id: \.id) { Text($0.label).tag($0.id) }
                }
                .pickerStyle(.segmented).labelsHidden()
                Text(model.summary).foregroundStyle(.secondary).lineLimit(2)
            }
            .padding(.horizontal, 24).padding(.top, 20).padding(.bottom, 12)
            Divider()
            content.frame(height: 340)
            Divider()
            HStack {
                Button("Close") { state.paths = nil }.keyboardShortcut(.cancelAction)
                Spacer()
                if let step = model.step { Text("Step \(step.id + 1) of \(model.steps.count)").foregroundStyle(.secondary).monospacedDigit() }
                Spacer()
                if model.subject == .album {
                    Button("Play Album") { if let a = model.step.flatMap(libraryAlbum) { state.paths = nil; state.actions.play(album: a) } }
                        .disabled(model.step.flatMap(libraryAlbum) == nil)
                }
                Button(model.step?.target?.label ?? "Open") { open(model.step) }
                    .keyboardShortcut(.defaultAction).disabled(model.step?.target == nil)
            }
            .padding(.horizontal, 24).padding(.vertical, 12)
        }
        .frame(width: 820)
    }

    @ViewBuilder private var content: some View {
        switch model.phase {
        case .loading:
            ProgressView("Finding the paths…").frame(maxWidth: .infinity, maxHeight: .infinity)
        case .failed(let message):
            VStack(spacing: 12) {
                Text(message).foregroundStyle(.red).multilineTextAlignment(.center)
                Button("Try Again") { state.loadPathsTab(retry: true) }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity).padding(.horizontal, 32)
        case .ready(let answer):
            if answer.steps.isEmpty {
                Text(model.emptyText).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity, maxHeight: .infinity).padding(.horizontal, 32)
            } else {
                HStack(spacing: 0) {
                    VStack(spacing: 0) {
                        table(answer.steps)
                        ForEach(answer.notes, id: \.self) {
                            Text($0).font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal, 12).padding(.vertical, 4)
                        }
                    }
                    Divider()
                    inspector.frame(width: 300)
                }
            }
        }
    }

    private func table(_ steps: [PathStep]) -> some View {
        Table(steps, selection: $model.selected) {
            TableColumn("#") { Text("\($0.id + 1)").monospacedDigit().foregroundStyle(.secondary) }.width(28)
            TableColumn(model.subject == .album ? "Album" : "Step") { s in
                HStack(spacing: 8) {
                    thumb(s, 28)
                    Text(s.name).lineLimit(1)
                }
            }
            TableColumn(model.subject == .album ? "Artist" : "Detail") { Text($0.detail).lineLimit(1) }
            TableColumn("Why") { Text($0.why).foregroundStyle(.secondary).lineLimit(1) }
        }
        .alternatingRowBackgrounds()
        .onKeyPress(.return) { open(model.step); return model.step?.target == nil ? .ignored : .handled }
    }

    @ViewBuilder private func thumb(_ s: PathStep, _ size: CGFloat) -> some View {
        if let c = s.cover {
            CoverView(album: item(c), px: Int(size * 2)).frame(width: size, height: size).clipShape(RoundedRectangle(cornerRadius: size / 7, style: .continuous))
        } else {
            Image(systemName: s.symbol).font(.system(size: size * 0.5)).foregroundStyle(.secondary).frame(width: size, height: size)
                .background(.quaternary, in: RoundedRectangle(cornerRadius: size / 7, style: .continuous))
                .accessibilityHidden(true)
        }
    }

    @ViewBuilder private var inspector: some View {
        if let s = model.step {
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    thumb(s, 120)
                    Text(s.name).font(.headline)
                    Text([s.detail, s.year.map(String.init) ?? "", s.owned ? "In your library" : "Not in your library"].filter { !$0.isEmpty }.joined(separator: " · "))
                        .foregroundStyle(.secondary)
                    ForEach(Array(s.reasons.prefix(3).enumerated()), id: \.offset) { _, r in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(r.eyebrow.uppercased()).font(.caption2.weight(.semibold)).foregroundStyle(.secondary)
                            if let via = r.via { Text(via).fontWeight(.semibold) }
                            Text(r.text).font(.callout)
                        }
                        .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                        .background(.background.secondary, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                        .accessibilityElement(children: .combine)
                    }
                    if let e = s.evidence { Text(e).font(.caption).foregroundStyle(.secondary) }
                    if let by = s.artistName, s.target != .artist(name: by) {
                        Button("Open Artist") { state.paths = nil; state.openArtist(named: by) }
                    }
                }
                .padding(16).frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(.background.secondary.opacity(0.4))
        } else {
            Text("Select a step to see why it is here.").foregroundStyle(.secondary).multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, maxHeight: .infinity).padding(24)
        }
    }

    private func item(_ c: PathStep.AlbumCover) -> AlbumItem {
        AlbumItem(id: -1, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: true,
                  hue: Double(abs(c.title.hashValue % 360)), remoteID: c.albumID, coverArt: c.coverArt)
    }

    /// The step's album in the library, by Navidrome id or by title and artist.
    private func libraryAlbum(_ s: PathStep) -> AlbumItem? {
        guard case .album(let title, let artist, let id)? = s.target else { return nil }
        return state.library.albums.first {
            ($0.remoteID != nil && $0.remoteID == id) || (LibrarySearch.fold($0.title) == LibrarySearch.fold(title) && LibrarySearch.fold($0.artist) == LibrarySearch.fold(artist))
        }
    }

    private func open(_ s: PathStep?) {
        guard let s, let target = s.target else { return }
        state.paths = nil
        switch target {
        case .artist(let name): state.openArtist(named: name)
        case .album(let title, let artist, _):
            // An album outside the library opens as one the page can look up (its Get button works there).
            state.open(album: libraryAlbum(s) ?? AlbumItem(id: -1, title: title, artist: artist, year: 0, genre: "", format: "", owned: false, hue: Double(abs(title.hashValue % 360))))
        }
    }
}
