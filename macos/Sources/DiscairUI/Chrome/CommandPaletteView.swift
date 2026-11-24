import DiscairLibrarian
import SwiftUI

/// The ⌘K palette: a search field over a short list. Type, arrow up or down, Return to run, Escape to close.
/// Rounded and translucent, in the Cupertino look.
struct CommandPaletteView: View {
    @Bindable var state: AppState
    @FocusState private var focused: Bool
    @Environment(\.colorScheme) private var colorScheme
    @State private var matches: [PaletteCommand] = []
    @State private var matchedQuery: String?
    @State private var submittedQuery: String?
    @State private var songHits: (query: String, rows: [SongRow])?
    @State private var catalogHits: (query: String, rows: CatalogHits)?
    private var query: Binding<String> { Binding(get: { state.palette.query }, set: { state.palette.query = $0 }) }

    var body: some View {
        let text = state.palette.query
        let request = state.paletteSearchRequest(query: text, songs: songHits?.query == text ? songHits?.rows ?? [] : [],
                                                 catalog: catalogHits?.query == text ? catalogHits?.rows ?? CatalogHits() : CatalogHits())
        let isEmptyQuery = text.trimmingCharacters(in: .whitespaces).isEmpty
        let results = isEmptyQuery ? Array(PaletteCatalog.fixed(playing: request.playing).prefix(9)) : (matchedQuery == text ? matches : [])
        let shape = RoundedRectangle(cornerRadius: 14, style: .continuous)
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary).accessibilityHidden(true)
                TextField("Search artists, albums, songs and pages", text: query)
                    .textFieldStyle(.plain)
                    .font(.system(size: 16))
                    .focused($focused)
                    .accessibilityLabel("Command palette")
                    .onSubmit {
                        if isEmptyQuery || matchedQuery == text { run(results) }
                        else { submittedQuery = text }
                    }
                    .onKeyPress(.downArrow) { state.palette.move(1, count: results.count); return .handled }
                    .onKeyPress(.upArrow) { state.palette.move(-1, count: results.count); return .handled }
                    .onKeyPress(.escape) { state.palette.close(); return .handled }
            }
            .padding(14)
            Divider()
            if results.isEmpty {
                Text(matchedQuery == text ? "Nothing matches “\(text)”" : "Searching…").foregroundStyle(.secondary).padding(20)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        ForEach(Array(results.enumerated()), id: \.element.id) { i, c in
                            if i == 0 || results[i - 1].section != c.section {
                                Text(c.section).font(.system(size: 11, weight: .bold)).textCase(.uppercase).tracking(0.8).foregroundStyle(.secondary)
                                    .padding(.horizontal, 10).padding(.top, i == 0 ? 2 : 10).padding(.bottom, 3)
                                    .accessibilityAddTraits(.isHeader)
                            }
                            row(c, selected: i == state.palette.highlight)
                        }
                    }
                    .padding(6)
                }
                .frame(maxHeight: 460).fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(width: 560)
        .background { if RenderMode.offscreenScreenshot { shape.fill(CU.bgPanel) } else { shape.fill(.regularMaterial) } }
        .environment(\.colorScheme, colorScheme)
        .overlay { shape.stroke(Color.primary.opacity(0.12), lineWidth: 1) }
        .shadow(color: .black.opacity(0.25), radius: 24, x: 0, y: 10)
        .onAppear { focused = true }
        .onChange(of: text) { _, _ in submittedQuery = nil }
        // On appear the field is often not in the window yet, or the top bar field still holds the focus, so the first request is
        // lost. Ask again once the view has settled.
        .task {
            for delay in [0, 60, 200] as [Int] {
                try? await Task.sleep(for: .milliseconds(delay))
                guard !Task.isCancelled else { return }
                focused = true
            }
        }
        .task(id: request) {
            guard !isEmptyQuery else { matchedQuery = nil; return }
            let found = await request.results()
            guard !Task.isCancelled, state.palette.query == text else { return }
            matches = found
            matchedQuery = text
            if submittedQuery == text {
                submittedQuery = nil
                run(found)
            }
        }
        .task(id: text) {
            songHits = nil
            let found = await state.searchSongHits(text)
            guard !Task.isCancelled, state.palette.query == text else { return }
            songHits = (text, found)
        }
        .task(id: text) {
            catalogHits = nil
            let found = await state.searchCatalogHits(text)
            guard !Task.isCancelled, state.palette.query == text else { return }
            catalogHits = (text, found)
        }
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isModal)
    }

    private func run(_ results: [PaletteCommand]) {
        guard results.indices.contains(state.palette.highlight) else { return }
        state.perform(results[state.palette.highlight])
    }

    private func row(_ c: PaletteCommand, selected: Bool) -> some View {
        let primary: Color = selected ? CU.onAccent : .primary
        let quiet: Color = selected ? CU.onAccent.opacity(0.78) : .secondary
        return HStack(spacing: 10) {
            leading(c)
            VStack(alignment: .leading, spacing: 1) {
                Text(c.name.isEmpty ? c.title : c.name).font(.system(size: 14, weight: .medium)).lineLimit(1)
                if !c.detail.isEmpty { Text(c.detail).font(.system(size: 11.5)).foregroundStyle(quiet).lineLimit(1) }
            }
            Spacer(minLength: 12)
            if let second = c.secondary {
                Button { state.perform(PaletteCommand(id: c.id + "-2", title: c.title, hint: c.hint, kind: c.kind, action: second)) } label: {
                    Image(systemName: c.secondaryLabel == "Get" ? "arrow.down.circle" : "play.fill")
                        .font(.system(size: 12, weight: .bold)).foregroundStyle(primary)
                        .frame(width: 26, height: 26).background(primary.opacity(0.14), in: Circle()).contentShape(Circle())
                }
                .buttonStyle(.plain).accessibilityLabel("\(c.secondaryLabel) \(c.name)").help(c.secondaryLabel)
            }
        }
        .padding(.horizontal, 10).padding(.vertical, 5)
        .foregroundStyle(primary)
        .background(selected ? CU.accent : .clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .contentShape(Rectangle())
        .onTapGesture { state.perform(c) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(c.title)
        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
    }

    /// Artwork for albums and songs, the photo for an artist, a small icon for pages and playback.
    @ViewBuilder private func leading(_ c: PaletteCommand) -> some View {
        let size: CGFloat = 36
        switch c.kind {
        case .album, .song:
            if let a = c.album ?? c.song?.albumItem {
                CoverView(album: a).frame(width: size, height: size).clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            }
        case .artist:
            ArtistPhoto(name: c.name, size: size)
        case .screen, .playback:
            Image(systemName: c.kind == .playback ? "playpause" : "arrow.turn.down.right").font(.system(size: 13))
                .frame(width: size, height: size).background(Color.primary.opacity(0.07), in: RoundedRectangle(cornerRadius: 5, style: .continuous))
        }
    }
}

/// Dims the window and shows the palette near the top while it is open.
struct CommandPaletteOverlay: ViewModifier {
    @Bindable var state: AppState
    func body(content: Content) -> some View {
        content.overlay {
            if state.palette.isOpen {
                ZStack(alignment: .top) {
                    Color.black.opacity(0.28).ignoresSafeArea().onTapGesture { state.palette.close() }
                    CommandPaletteView(state: state).padding(.top, 90)
                }
                .transition(.opacity)
            }
        }
        .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 0.12), value: state.palette.isOpen)
    }
}
