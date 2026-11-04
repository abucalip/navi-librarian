import SwiftUI

/// A horizontal bar you can drag or click, with keyboard and VoiceOver adjustment (up and down in 5% steps). Used for the
/// seek bar and the volume, so neither depends on a gesture alone. `onCommit` runs when the drag ends or a step is made;
/// while dragging the bar shows the dragged value, not the playing one.
struct DragBar: View {
    let value: Double
    var height: CGFloat = 5
    var track: Color = .white.opacity(0.3)
    var fill: Color = .white
    var rounded = true
    var label: String
    var valueText: (Double) -> String = { "\(Int($0 * 100)) percent" }
    var onCommit: (Double) -> Void

    @State private var dragging: Double?

    var body: some View {
        GeometryReader { g in
            let shown = dragging ?? value
            ZStack(alignment: .leading) {
                shape.fill(track)
                shape.fill(fill).frame(width: max(0, g.size.width * min(max(shown, 0), 1)))
            }
            .frame(height: height).frame(maxHeight: .infinity)
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0)
                .onChanged { dragging = min(max($0.location.x / max(g.size.width, 1), 0), 1) }
                .onEnded {
                    let v = min(max($0.location.x / max(g.size.width, 1), 0), 1)
                    dragging = nil
                    onCommit(v)
                })
        }
        .frame(height: max(height, 16))
        .focusable()
        .accessibilityElement()
        .accessibilityLabel(label)
        .accessibilityValue(valueText(dragging ?? value))
        .accessibilityAdjustableAction { dir in
            switch dir {
            case .increment: onCommit(min(value + 0.05, 1))
            case .decrement: onCommit(max(value - 0.05, 0))
            @unknown default: break
            }
        }
        .onKeyPress(.rightArrow) { onCommit(min(value + 0.05, 1)); return .handled }
        .onKeyPress(.leftArrow) { onCommit(max(value - 0.05, 0)); return .handled }
    }

    private var shape: AnyShape { rounded ? AnyShape(Capsule()) : AnyShape(Rectangle()) }
}
