import AppKit
import SwiftUI

/// Window chrome owned by the theme: the system title bar and buttons are hidden, content runs to the edges,
/// the whole background drags the window. The window stays `.titled | .resizable` so macOS keeps resize, the
/// shadow, full screen and keyboard handling; a truly borderless window would lose all of them.
struct WindowConfigurator: NSViewRepresentable {
    /// Whether a press at this point (from the top left of the window) may drag the window. Asked at every press, so an area
    /// that reads drags itself (the Up Next list) can say no. Default: the whole window drags.
    var canDragAt: (CGPoint, CGSize) -> Bool = { _, _ in true }

    final class Coordinator {
        var canDragAt: (CGPoint, CGSize) -> Bool = { _, _ in true }
        var monitor: Any?
        deinit { if let monitor { NSEvent.removeMonitor(monitor) } }
    }
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSView {
        let v = NSView()
        context.coordinator.canDragAt = canDragAt
        DispatchQueue.main.async { Self.configure(v.window); install(on: v, context.coordinator) }
        return v
    }
    func updateNSView(_ nsView: NSView, context: Context) {
        context.coordinator.canDragAt = canDragAt
        DispatchQueue.main.async { Self.configure(nsView.window); install(on: nsView, context.coordinator) }
    }
    /// Before each press is dispatched, the window is made draggable or not for that press.
    private func install(on view: NSView, _ c: Coordinator) {
        guard c.monitor == nil, let window = view.window else { return }
        c.monitor = NSEvent.addLocalMonitorForEvents(matching: .leftMouseDown) { [weak window, weak c] event in
            guard let window, let c, event.window === window, let content = window.contentView else { return event }
            let size = content.bounds.size
            let p = CGPoint(x: event.locationInWindow.x, y: size.height - event.locationInWindow.y)
            window.isMovableByWindowBackground = c.canDragAt(p, size)
            return event
        }
    }
    @MainActor static func configure(_ w: NSWindow?) {
        guard let w else { return }
        w.titlebarAppearsTransparent = true
        w.titleVisibility = .hidden
        w.styleMask.insert(.fullSizeContentView)
        w.isMovableByWindowBackground = true
        w.backgroundColor = .windowBackgroundColor
        w.isOpaque = true
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

/// What a row's grab area needs to report a drag (see `ReorderRow`): a SwiftUI drag that starts after a few points, in
/// window coordinates so it is not disturbed by the row moving under the pointer. The window itself is kept from moving
/// over this area by `WindowConfigurator.canDragAt`.
struct ReorderGrab: ViewModifier {
    var onBegan: () -> Void = {}
    var onMoved: (CGFloat) -> Void = { _ in }
    var onEnded: (CGFloat) -> Void = { _ in }
    @State private var begun = false
    func body(content: Content) -> some View {
        content.contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 4, coordinateSpace: .global)
                .onChanged { v in
                    if !begun { begun = true; onBegan() }
                    onMoved(v.translation.height)
                }
                .onEnded { v in begun = false; onEnded(v.translation.height) })
    }
}

/// A list row that can be dragged up or down to a new place. The row follows the pointer; on release it moves by
/// the whole rows it was dragged over. The grab area (the part that is not a button or menu) takes `grab`.
struct ReorderRow<Content: View>: View {
    let index: Int
    let count: Int
    var enabled = true
    let move: (Int, Int) -> Void
    @ViewBuilder let content: (ReorderGrab?) -> Content
    @State private var dy: CGFloat = 0
    @State private var active = false
    @State private var height: CGFloat = 52

    /// The place a drag of `dy` points ends at.
    static func target(from index: Int, dy: CGFloat, rowHeight: CGFloat, count: Int) -> Int {
        guard rowHeight > 0, count > 0 else { return index }
        return min(max(index + Int((dy / rowHeight).rounded()), 0), count - 1)
    }

    var body: some View {
        content(enabled ? ReorderGrab(
            onBegan: { active = true },
            onMoved: { dy = $0 },
            onEnded: { final in
                let to = Self.target(from: index, dy: final, rowHeight: height, count: count)
                dy = 0; active = false
                if to != index { move(index, to) }
            }) : nil)
            .offset(y: dy)
            .zIndex(active ? 1 : 0)
            .opacity(active ? 0.85 : 1)
            .shadow(color: .black.opacity(active ? 0.2 : 0), radius: 6, y: 2)
            .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { height = $0 }
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
