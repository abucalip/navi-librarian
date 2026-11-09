import AppKit
import SwiftUI

/// Space plays or pauses, wherever the window is, unless the key is meant for typing (a text field is being edited) or for a
/// control that has the keyboard focus. Installed once for the window; removed with it.
struct SpaceBarPlayPause: NSViewRepresentable {
    let toggle: @MainActor () -> Void

    /// True when this key press is a bare space the app should take.
    static func shouldHandle(keyCode: UInt16, modifiers: NSEvent.ModifierFlags, firstResponder: NSResponder?) -> Bool {
        guard keyCode == 49, modifiers.intersection(.deviceIndependentFlagsMask).subtracting([.capsLock]).isEmpty else { return false }
        if firstResponder is NSText || firstResponder is NSControl { return false }
        return true
    }

    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        context.coordinator.install(view: view, toggle: toggle)
        return view
    }
    func updateNSView(_ nsView: NSView, context: Context) { context.coordinator.toggle = toggle }
    static func dismantleNSView(_ nsView: NSView, coordinator: Coordinator) { coordinator.remove() }

    @MainActor final class Coordinator {
        var toggle: @MainActor () -> Void = {}
        private var monitor: Any?
        func install(view: NSView, toggle: @escaping @MainActor () -> Void) {
            self.toggle = toggle
            monitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self, weak view] event in
                guard let view, let window = view.window, event.window === window, window.isKeyWindow,
                      SpaceBarPlayPause.shouldHandle(keyCode: event.keyCode, modifiers: event.modifierFlags, firstResponder: window.firstResponder),
                      !event.isARepeat else { return event }
                MainActor.assumeIsolated { self?.toggle() }
                return nil
            }
        }
        func remove() { if let monitor { NSEvent.removeMonitor(monitor) }; monitor = nil }
    }
}
