import AppKit
import SwiftUI

/// Window chrome owned by the theme: the system title bar and buttons are hidden, content runs to the edges,
/// the whole background drags the window. The window stays `.titled | .resizable` so macOS keeps resize, the
/// shadow, full screen and keyboard handling; a truly borderless window would lose all of them.
struct WindowConfigurator: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let v = NSView()
        DispatchQueue.main.async { Self.configure(v.window) }
        return v
    }
    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async { Self.configure(nsView.window) }
    }
    @MainActor static func configure(_ w: NSWindow?) {
        guard let w else { return }
        w.titlebarAppearsTransparent = true
        w.titleVisibility = .hidden
        w.styleMask.insert(.fullSizeContentView)
        w.isMovableByWindowBackground = true
        w.backgroundColor = .clear
        for b in [NSWindow.ButtonType.closeButton, .miniaturizeButton, .zoomButton] {
            w.standardWindowButton(b)?.isHidden = true
        }
    }
}

/// The theme's own traffic lights (close, minimise, zoom). Labelled for VoiceOver.
struct TrafficLights: View {
    var colors: [Color] = [Color(red: 1, green: 0.37, blue: 0.34), Color(red: 1, green: 0.74, blue: 0.18), Color(red: 0.16, green: 0.78, blue: 0.25)]
    var size: CGFloat = 12
    var body: some View {
        HStack(spacing: 8) {
            light(colors[0], "Close") { NSApp.keyWindow?.close() }
            light(colors[1], "Minimise") { NSApp.keyWindow?.miniaturize(nil) }
            light(colors[2], "Zoom") { NSApp.keyWindow?.zoom(nil) }
        }
    }
    private func light(_ c: Color, _ label: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) { Circle().fill(c).frame(width: size, height: size) }
            .buttonStyle(.plain)
            .accessibilityLabel(label)
    }
}
