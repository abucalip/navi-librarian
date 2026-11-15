import AppKit
import SwiftUI

/// The "this is playing" mark: moving bars while the song plays, still bars while it is paused.
///
/// The moving bars are an AppKit symbol effect on an `NSImageView`. SwiftUI's own `.symbolEffect(..., options: .repeating)`
/// re-rendered the whole window's display list on the main thread every frame for as long as the row existed (album rows are not
/// lazy, so even when scrolled out of sight): about 30 points of CPU on an album page, and the main thread was left waiting on the
/// render server so often that the player clock lagged and then jumped. In a test window the AppKit effect cost about 2 % against
/// 18 % for the SwiftUI one. The offscreen screenshot, which cannot draw an AppKit view, gets the still SwiftUI symbol.
struct PlayingBars: View {
    let active: Bool
    /// The row's text colour (an AppKit view does not inherit SwiftUI's foreground style).
    let color: Color
    /// The row's font size, so the mark matches the text beside it.
    var pointSize: CGFloat = 13
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Group {
            if RenderMode.offscreenScreenshot {
                Image(systemName: "waveform").font(.system(size: pointSize)).foregroundStyle(color)
            } else {
                SymbolBars(moving: active && !reduceMotion, color: NSColor(color), pointSize: pointSize).fixedSize()
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(active ? "Playing" : "Paused")
    }
}

private struct SymbolBars: NSViewRepresentable {
    let moving: Bool
    let color: NSColor
    let pointSize: CGFloat

    final class Coordinator { var moving = false; var pointSize: CGFloat = 0 }

    /// A symbol effect only runs on a view that is in a window. SwiftUI calls `updateNSView` before the view is attached, so
    /// the first request was dropped and the bars stayed still. The view asks again when it joins a window.
    final class BarsView: NSImageView {
        var wantsMotion = false { didSet { if wantsMotion != oldValue { apply() } } }
        override func viewDidMoveToWindow() { super.viewDidMoveToWindow(); apply() }
        private func apply() {
            removeAllSymbolEffects(options: .default, animated: false)
            guard wantsMotion, window != nil else { return }
            addSymbolEffect(.variableColor.iterative.dimInactiveLayers, options: .repeating, animated: true)
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> NSImageView {
        let view = BarsView()
        view.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: nil)
        view.imageScaling = .scaleNone
        view.setAccessibilityElement(false)
        view.setContentHuggingPriority(.required, for: .horizontal)
        view.setContentHuggingPriority(.required, for: .vertical)
        return view
    }

    func updateNSView(_ view: NSImageView, context: Context) {
        guard let view = view as? BarsView else { return }
        let state = context.coordinator
        if state.pointSize != pointSize {
            view.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: pointSize, weight: .regular)
            state.pointSize = pointSize
        }
        if view.contentTintColor != color { view.contentTintColor = color }
        state.moving = moving
        view.wantsMotion = moving
    }
}
