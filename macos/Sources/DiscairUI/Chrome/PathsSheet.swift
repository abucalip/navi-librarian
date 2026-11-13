import DiscairLibrarian
import SwiftUI

/// The Paths sheet of an album or an artist: a tab bar of paths, the server's steps as a list in its own order, and a
/// trailing inspector with the selected step's story. Its size is fixed so nothing is cut off, and its accent is the
/// active theme's, so it reads as part of the theme rather than as a system dialog.
struct PathsSheet: View {
    let state: AppState
    @Bindable var model: PathsSheetModel

    static let size = CGSize(width: 820, height: 520)
    private static let inspectorWidth: CGFloat = 300

    private var accent: Color { CU.accent }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                Text(model.heading).font(.title2.bold()).lineLimit(1).truncationMode(.tail).accessibilityAddTraits(.isHeader)
                tabBar
                Text(model.summary).foregroundStyle(.secondary).lineLimit(2).fixedSize(horizontal: false, vertical: true)
            }
            .padding(.horizontal, 24).padding(.top, 20).padding(.bottom, 12)
            Divider()
            content.frame(maxWidth: .infinity, maxHeight: .infinity)
            Divider()
            footer
        }
        .frame(width: Self.size.width, height: Self.size.height)
        .tint(accent)
    }

    // MARK: Header

    private var tabBar: some View {
        HStack(spacing: 2) {
            ForEach(model.tabLabels, id: \.id) { tab in
                let on = tab.id == model.tabID
                Button {
                    model.choose(tab.id); state.loadPathsTab()
                } label: {
                    Text(tab.label).font(.system(size: 13, weight: on ? .semibold : .regular)).lineLimit(1)
                        .frame(maxWidth: .infinity).padding(.vertical, 5)
                        .background { if on { RoundedRectangle(cornerRadius: 7, style: .continuous).fill(Color(nsColor: .controlBackgroundColor)).shadow(color: .black.opacity(0.18), radius: 1, y: 0.5) } }
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .padding(2)
        .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Color.primary.opacity(0.07)))
    }

    // MARK: Footer

    private var footer: some View {
        HStack {
            Button("Close") { state.paths = nil }.keyboardShortcut(.cancelAction).buttonStyle(SheetButtonStyle(accent: accent))
            Spacer()
            if let step = model.step { Text("Step \(step.id + 1) of \(model.steps.count)").foregroundStyle(.secondary).monospacedDigit() }
            Spacer()
            if model.subject == .album, let album = model.step.flatMap(libraryAlbum) {
                Button { state.paths = nil; state.actions.play(album: album) } label: { Label("Play Album", systemImage: "play.fill") }
                    .buttonStyle(SheetButtonStyle(accent: accent))
            }
            Button(model.step?.target?.label ?? "Open") { open(model.step) }
                .keyboardShortcut(.defaultAction).buttonStyle(SheetButtonStyle(accent: accent, prominent: true)).disabled(model.step?.target == nil)
        }
        .padding(.horizontal, 24).padding(.vertical, 12)
    }

    // MARK: Body

    @ViewBuilder private var content: some View {
        switch model.phase {
        case .loading:
            ProgressView("Finding the paths…")
        case .failed(let message):
            VStack(spacing: 12) {
                Text(message).foregroundStyle(.red).multilineTextAlignment(.center)
                HStack(spacing: 12) {
                    Button("Try Again") { state.loadPathsTab(retry: true) }.buttonStyle(SheetButtonStyle(accent: accent))
                    if model.canRequestUpdate {
                        let librarian = state.session?.librarian
                        Button("Request update") { Task { await model.requestUpdate(librarian: librarian) } }
                            .buttonStyle(SheetButtonStyle(accent: accent)).disabled(model.updating)
                    }
                }
                if let note = model.updateNote { Text(note).font(.caption).foregroundStyle(.secondary) }
            }
            .padding(.horizontal, 32)
        case .ready(let answer):
            if answer.steps.isEmpty {
                Text(model.emptyText).foregroundStyle(.secondary).multilineTextAlignment(.center).padding(.horizontal, 32)
            } else {
                HStack(spacing: 0) {
                    VStack(spacing: 0) {
                        list(answer.steps)
                        if !answer.notes.isEmpty {
                            VStack(alignment: .leading, spacing: 2) {
                                ForEach(answer.notes, id: \.self) { Text($0).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 16).padding(.vertical, 6)
                        }
                    }
                    Divider()
                    inspector.frame(width: Self.inspectorWidth)
                }
            }
        }
    }

    private var albumSheet: Bool { model.subject == .album }

    private func list(_ steps: [PathStep]) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Text("#").frame(width: 22, alignment: .trailing)
                Text(albumSheet ? "Album" : "Step").frame(maxWidth: .infinity, alignment: .leading)
                Text(albumSheet ? "Artist" : "Detail").frame(width: 140, alignment: .leading)
                Text("Why").frame(width: 150, alignment: .leading)
            }
            .font(.system(size: 12, weight: .semibold)).foregroundStyle(.secondary)
            .padding(.horizontal, 12).frame(height: 28)
            Divider()
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(steps) { s in row(s).id(s.id) }
                    }
                }
                .onChange(of: model.selected) { _, new in if let new { withAnimation(.easeOut(duration: 0.12)) { proxy.scrollTo(new) } } }
            }
            .focusable().focusEffectDisabled()
            .onKeyPress(.downArrow) { model.move(by: 1); return .handled }
            .onKeyPress(.upArrow) { model.move(by: -1); return .handled }
            .onKeyPress(.return) { open(model.step); return model.step?.target == nil ? .ignored : .handled }
        }
    }

    private func row(_ s: PathStep) -> some View {
        let on = model.selected == s.id
        return HStack(spacing: 8) {
            Text("\(s.id + 1)").monospacedDigit().foregroundStyle(.secondary).frame(width: 22, alignment: .trailing)
            HStack(spacing: 8) {
                PathRowThumb(step: s, size: 28) { thumb(s, 28) }
                Text(s.name).lineLimit(1).truncationMode(.tail)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Text(s.detail).lineLimit(1).truncationMode(.tail).frame(width: 140, alignment: .leading)
            Text(s.why).foregroundStyle(.secondary).lineLimit(1).truncationMode(.tail).frame(width: 150, alignment: .leading)
        }
        .padding(.horizontal, 12).frame(height: 40)
        .background(on ? accent.opacity(0.14) : (s.id.isMultiple(of: 2) ? Color.clear : Color.primary.opacity(0.035)))
        .contentShape(Rectangle())
        .onTapGesture { model.selected = s.id }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(on ? .isSelected : [])
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

    // MARK: Inspector

    @ViewBuilder private var inspector: some View {
        if let s = model.step {
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    thumb(s, 104)
                    if model.tabID == AlbumPathTab.sameRoom.id, model.subject == .album, let cover = s.cover {
                        SameRoomPhotos(startTitle: model.title, startArtist: model.artist, otherTitle: cover.title, otherArtist: cover.artist)
                    }
                    Text(s.name).font(.headline).lineLimit(2).fixedSize(horizontal: false, vertical: true)
                    Text([s.detail, s.year.map(String.init) ?? "", s.owned ? "In your library" : "Not in your library"].filter { !$0.isEmpty }.joined(separator: " · "))
                        .foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    if let play = s.play { card { Text("YOUR LISTENING").font(.caption2.weight(.semibold)).foregroundStyle(.secondary); Text(play).fontWeight(.semibold) } }
                    if !s.story.isEmpty || s.evidence != nil {
                        card {
                            ForEach(Array(s.story.enumerated()), id: \.offset) { _, paragraph in
                                Text(Self.attributed(paragraph)).font(.callout).fixedSize(horizontal: false, vertical: true)
                            }
                            if let e = s.evidence { Text(e).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
                        }
                    } else {
                        ForEach(Array(s.reasons.prefix(3).enumerated()), id: \.offset) { _, r in
                            card {
                                Text(r.eyebrow.uppercased()).font(.caption2.weight(.semibold)).foregroundStyle(.secondary)
                                if let via = r.via { Text(via).fontWeight(.semibold) }
                                Text(r.text).font(.callout).fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                    if let by = s.artistName, s.target != .artist(name: by) {
                        Button("Open Artist") { state.paths = nil; state.openArtist(named: by) }.buttonStyle(SheetButtonStyle(accent: accent))
                    }
                }
                .padding(16).frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color.primary.opacity(0.03))
        } else {
            Text("Select a step to see why it is here.").foregroundStyle(.secondary).multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, maxHeight: .infinity).padding(24)
        }
    }

    private func card<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 6, content: content)
            .padding(12).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(Color.primary.opacity(0.12), lineWidth: 0.5))
    }

    /// A story as one styled run: people and places bold, albums, songs and works italic.
    static func attributed(_ spans: [StorySpan]) -> AttributedString {
        var out = AttributedString()
        for span in spans {
            var piece = AttributedString(span.text)
            switch span.kind {
            case .plain: break
            case .name: piece.inlinePresentationIntent = .stronglyEmphasized
            case .title: piece.inlinePresentationIntent = .emphasized
            }
            out += piece
        }
        return out
    }

    // MARK: Library lookups

    /// The cover's album item. A step the server names only by title and artist borrows its Navidrome ids from the library
    /// album of that name; one outside the library is marked not owned so its cover is looked up by artist and title.
    private func item(_ c: PathStep.AlbumCover) -> AlbumItem {
        let hue = Double(abs(c.title.hashValue % 360))
        if c.coverArt != nil || c.albumID != nil {
            return AlbumItem(id: -1, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: hue, remoteID: c.albumID, coverArt: c.coverArt)
        }
        if let a = library(title: c.title, artist: c.artist) {
            return AlbumItem(id: -1, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: hue,
                             remoteID: a.remoteID, coverArt: a.coverArt ?? a.remoteID.map { "al-\($0)" })
        }
        return AlbumItem(id: 0, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: false, hue: hue)
    }

    /// Every album in the library, not only the page of them the library screen shows.
    private var libraryAlbums: [AlbumItem] { state.library.searchableAlbums }

    private func library(title: String, artist: String) -> AlbumItem? {
        libraryAlbums.first { LibrarySearch.fold($0.title) == LibrarySearch.fold(title) && LibrarySearch.fold($0.artist) == LibrarySearch.fold(artist) }
    }

    /// The step's album in the library, by Navidrome id or by title and artist. An album the server marks as outside the library has none.
    private func libraryAlbum(_ s: PathStep) -> AlbumItem? {
        guard s.owned, case .album(let title, let artist, let id)? = s.target else { return nil }
        return libraryAlbums.first {
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

/// The sheet's buttons: a bordered pill, or a pill filled with the theme's accent. Drawn by hand so the accent shows in every
/// context (the system prominent style takes the system colour and does not render offscreen).
private struct SheetButtonStyle: ButtonStyle {
    let accent: Color
    var prominent = false
    @Environment(\.isEnabled) private var enabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 14, weight: .semibold))
            .foregroundStyle(prominent ? CU.onAccent : Color.primary)
            .padding(.horizontal, 14).padding(.vertical, 6)
            .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(prominent ? accent : Color(nsColor: .controlBackgroundColor)))
            .overlay(RoundedRectangle(cornerRadius: 9, style: .continuous).stroke(prominent ? Color.clear : Color.primary.opacity(0.25), lineWidth: 1))
            .opacity(!enabled ? 0.45 : configuration.isPressed ? 0.8 : 1)
    }
}
