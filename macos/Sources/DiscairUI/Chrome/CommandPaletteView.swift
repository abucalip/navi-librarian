import SwiftUI

/// The ⌘K palette: a search field over a short list. Type, arrow up or down, Return to run, Escape to close.
/// One look for both themes, tinted by the theme (rounded and translucent in Cupertino, square and bordered in Zine).
struct CommandPaletteView: View {
    @Bindable var state: AppState
    @FocusState private var focused: Bool
    @Environment(\.colorScheme) private var colorScheme
    private var query: Binding<String> { Binding(get: { state.palette.query }, set: { state.palette.query = $0 }) }

    var body: some View {
        let results = state.paletteResults()
        let zine = state.themeID == .zine
        let shape = RoundedRectangle(cornerRadius: zine ? 0 : 14, style: .continuous)
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary).accessibilityHidden(true)
                TextField("Search artists, albums, songs and pages", text: query)
                    .textFieldStyle(.plain)
                    .font(.system(size: 16))
                    .focused($focused)
                    .accessibilityLabel("Command palette")
                    .onSubmit { run(results) }
                    .onKeyPress(.downArrow) { state.palette.move(1, count: results.count); return .handled }
                    .onKeyPress(.upArrow) { state.palette.move(-1, count: results.count); return .handled }
                    .onKeyPress(.escape) { state.palette.close(); return .handled }
            }
            .padding(14)
            Divider()
            if results.isEmpty {
                Text("Nothing matches “\(state.palette.query)”").foregroundStyle(.secondary).padding(20)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        ForEach(Array(results.enumerated()), id: \.element.id) { i, c in
                            if i == 0 || results[i - 1].section != c.section {
                                Text(c.section).font(.system(size: 11, weight: .bold)).textCase(.uppercase).tracking(0.8).foregroundStyle(.secondary)
                                    .padding(.horizontal, 10).padding(.top, i == 0 ? 2 : 10).padding(.bottom, 3)
                                    .accessibilityAddTraits(.isHeader)
                            }
                            row(c, selected: i == state.palette.highlight, zine: zine)
                        }
                    }
                    .padding(6)
                }
                .frame(maxHeight: 460).fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(width: 560)
        .background { if zine || RenderMode.offscreenScreenshot { shape.fill(Color(white: 0.95)) } else { shape.fill(.regularMaterial) } }
        .environment(\.colorScheme, zine || RenderMode.offscreenScreenshot ? .light : colorScheme)
        .overlay { shape.stroke(zine ? Color.black : Color.primary.opacity(0.12), lineWidth: zine ? 2 : 1) }
        .background { if zine { Rectangle().fill(Color.black).offset(x: 6, y: 6) } }
        .shadow(color: .black.opacity(zine ? 0 : 0.25), radius: zine ? 0 : 24, x: 0, y: zine ? 0 : 10)
        .onAppear { focused = true }
        // On appear the field is often not in the window yet, or the top bar field still holds the focus, so the first request is
        // lost. Ask again once the view has settled.
        .task {
            for delay in [0, 60, 200] as [Int] {
                try? await Task.sleep(for: .milliseconds(delay))
                guard !Task.isCancelled else { return }
                focused = true
            }
        }
        .task(id: state.palette.query) { await state.searchSongHits(state.palette.query) }
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isModal)
    }

    private func run(_ results: [PaletteCommand]) {
        guard results.indices.contains(state.palette.highlight) else { return }
        state.perform(results[state.palette.highlight])
    }

    private func row(_ c: PaletteCommand, selected: Bool, zine: Bool) -> some View {
        let primary: Color = selected ? .white : .primary
        let quiet: Color = selected ? .white.opacity(0.78) : .secondary
        return HStack(spacing: 10) {
            leading(c, zine: zine)
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
        .background(selected ? Color.accentColor : .clear, in: RoundedRectangle(cornerRadius: zine ? 0 : 8, style: .continuous))
        .contentShape(Rectangle())
        .onTapGesture { state.perform(c) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(c.title)
        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
    }

    /// Artwork for albums and songs, the photo for an artist, a small icon for pages and playback.
    @ViewBuilder private func leading(_ c: PaletteCommand, zine: Bool) -> some View {
        let size: CGFloat = 36
        switch c.kind {
        case .album, .song:
            if let a = c.album ?? c.song?.albumItem {
                CoverView(album: a).frame(width: size, height: size).clipShape(RoundedRectangle(cornerRadius: zine ? 0 : 5, style: .continuous))
            }
        case .artist:
            ArtistPhoto(name: c.name, size: size)
        case .screen, .playback:
            Image(systemName: c.kind == .playback ? "playpause" : "arrow.turn.down.right").font(.system(size: 13))
                .frame(width: size, height: size).background(Color.primary.opacity(0.07), in: RoundedRectangle(cornerRadius: zine ? 0 : 5, style: .continuous))
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
