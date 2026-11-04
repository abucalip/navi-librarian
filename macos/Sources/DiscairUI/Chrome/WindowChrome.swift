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

/// The window drags by its background, so a control that reads mouse drags (seek bar, volume, EQ band, a draggable row)
/// must take the mouse itself: a SwiftUI gesture under an AppKit blocker never saw the press. These views are AppKit
/// views laid over the control; they handle the mouse directly and are never a window-drag area.
final class PointerNSView: NSView {
    /// Position in the view, from the top left, and the view's size.
    var onDown: (CGPoint, CGSize) -> Void = { _, _ in }
    var onDrag: (CGPoint, CGSize) -> Void = { _, _ in }
    var onUp: (CGPoint, CGSize) -> Void = { _, _ in }
    override var isFlipped: Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    private func point(_ e: NSEvent) -> CGPoint { convert(e.locationInWindow, from: nil) }
    override func mouseDown(with event: NSEvent) { onDown(point(event), bounds.size) }
    override func mouseDragged(with event: NSEvent) { onDrag(point(event), bounds.size) }
    override func mouseUp(with event: NSEvent) { onUp(point(event), bounds.size) }
}

/// Reports a press, a drag and the release on the view it covers (a click is a press and a release at one place).
struct PointerSurface: NSViewRepresentable {
    var onDown: (CGPoint, CGSize) -> Void = { _, _ in }
    var onDrag: (CGPoint, CGSize) -> Void
    var onUp: (CGPoint, CGSize) -> Void

    func makeNSView(context: Context) -> PointerNSView { PointerNSView() }
    func updateNSView(_ v: PointerNSView, context: Context) { v.onDown = onDown; v.onDrag = onDrag; v.onUp = onUp }
}

/// The part of a row you grab to reorder it. Starts an AppKit drag of `id` (as plain text, which `dropDestination(for:
/// String.self)` takes) once the pointer has moved a few points. Only this part, not the whole row, so the buttons and
/// menu in the row keep their own clicks.
final class RowDragNSView: NSView, NSDraggingSource {
    var payload = ""
    var label = ""
    private var pressed: NSPoint?
    override var mouseDownCanMoveWindow: Bool { false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func mouseDown(with event: NSEvent) { pressed = event.locationInWindow }
    override func mouseUp(with event: NSEvent) { pressed = nil }
    override func mouseDragged(with event: NSEvent) {
        guard let start = pressed, hypot(event.locationInWindow.x - start.x, event.locationInWindow.y - start.y) > 4, !payload.isEmpty else { return }
        pressed = nil
        let item = NSPasteboardItem()
        item.setString(payload, forType: .string)
        let dragging = NSDraggingItem(pasteboardWriter: item)
        dragging.setDraggingFrame(bounds, contents: dragImage())
        beginDraggingSession(with: [dragging], event: event, source: self)
    }
    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation { .move }

    private func dragImage() -> NSImage {
        let text = label
        return NSImage(size: bounds.size, flipped: false) { r in
            NSColor.black.withAlphaComponent(0.12).setFill()
            NSBezierPath(roundedRect: r, xRadius: 9, yRadius: 9).fill()
            (text as NSString).draw(at: NSPoint(x: 12, y: max(0, (r.height - 16) / 2)), withAttributes: [.font: NSFont.systemFont(ofSize: 13, weight: .semibold), .foregroundColor: NSColor.labelColor])
            return true
        }
    }
}

struct RowDragSurface: NSViewRepresentable {
    let id: String
    let label: String
    func makeNSView(context: Context) -> RowDragNSView { RowDragNSView() }
    func updateNSView(_ v: RowDragNSView, context: Context) { v.payload = id; v.label = label }
}

struct RowDragSource: ViewModifier {
    let id: String?
    var label = ""
    func body(content: Content) -> some View {
        if let id { content.contentShape(Rectangle()).overlay(RowDragSurface(id: id, label: label)) } else { content }
    }
}

/// The theme's own traffic lights (close, minimise, zoom). Like the system ones, the symbols (x, minus, arrows) show
/// while the pointer is over the group. Labelled for VoiceOver.
struct TrafficLights: View {
    var colors: [Color] = [Color(red: 1, green: 0.37, blue: 0.34), Color(red: 1, green: 0.74, blue: 0.18), Color(red: 0.16, green: 0.78, blue: 0.25)]
    var size: CGFloat = 12
    /// Show the symbols without hovering (screenshot tests).
    var showSymbols = false
    @State private var hovering = false
    var body: some View {
        HStack(spacing: 8) {
            light(colors[0], "Close", symbol: "xmark") { NSApp.keyWindow?.close() }
            light(colors[1], "Minimise", symbol: "minus") { NSApp.keyWindow?.miniaturize(nil) }
            light(colors[2], "Zoom", symbol: "arrow.up.left.and.arrow.down.right") { NSApp.keyWindow?.zoom(nil) }
        }
        .onHover { hovering = $0 }
    }
    private func light(_ c: Color, _ label: String, symbol: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Circle().fill(c).frame(width: size, height: size)
                .overlay {
                    Image(systemName: symbol).font(.system(size: size * 0.55, weight: .heavy)).foregroundStyle(.black.opacity(0.55))
                        .opacity(hovering || showSymbols ? 1 : 0)
                }
                .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}
