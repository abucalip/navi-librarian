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
                TextField("Type a command, album or artist", text: query)
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
                VStack(spacing: 0) {
                    ForEach(Array(results.enumerated()), id: \.element.id) { i, c in
                        row(c, selected: i == state.palette.highlight, zine: zine)
                            .onTapGesture { state.perform(c) }
                    }
                }
                .padding(6)
            }
        }
        .frame(width: 560)
        .background { if zine || RenderMode.offscreenScreenshot { shape.fill(Color(white: 0.95)) } else { shape.fill(.regularMaterial) } }
        .environment(\.colorScheme, zine || RenderMode.offscreenScreenshot ? .light : colorScheme)
        .overlay { shape.stroke(zine ? Color.black : Color.primary.opacity(0.12), lineWidth: zine ? 2 : 1) }
        .background { if zine { Rectangle().fill(Color.black).offset(x: 6, y: 6) } }
        .shadow(color: .black.opacity(zine ? 0 : 0.25), radius: zine ? 0 : 24, x: 0, y: zine ? 0 : 10)
        .onAppear { focused = true }
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isModal)
    }

    private func run(_ results: [PaletteCommand]) {
        guard results.indices.contains(state.palette.highlight) else { return }
        state.perform(results[state.palette.highlight])
    }

    private func row(_ c: PaletteCommand, selected: Bool, zine: Bool) -> some View {
        HStack {
            Text(c.title).lineLimit(1)
            Spacer(minLength: 12)
            Text(c.hint).font(.system(size: 11)).foregroundStyle(selected ? .white.opacity(0.8) : .secondary)
        }
        .padding(.horizontal, 10).padding(.vertical, 7)
        .foregroundStyle(selected ? Color.white : Color.primary)
        .background(selected ? Color.accentColor : .clear, in: RoundedRectangle(cornerRadius: zine ? 0 : 8, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
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
