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
    /// Peaks (0...1) drawn as bars behind the fill. Nil keeps the plain bar: no waveform is ever invented.
    var peaks: [Float]? = nil
    var label: String
    var valueText: (Double) -> String = { "\(Int($0 * 100)) percent" }
    var onCommit: (Double) -> Void

    @State private var dragging: Double?
    static let waveformHeight: CGFloat = 26

    var body: some View {
        GeometryReader { g in
            let shown = dragging ?? value
            ZStack(alignment: .leading) {
                if let peaks, !peaks.isEmpty {
                    WaveformBars(peaks: peaks).fill(track)
                    WaveformBars(peaks: peaks).fill(fill)
                        .mask(alignment: .leading) { Rectangle().frame(width: max(0, g.size.width * min(max(shown, 0), 1))) }
                } else {
                    shape.fill(track)
                    shape.fill(fill).frame(width: max(0, g.size.width * min(max(shown, 0), 1)))
                }
            }
            .frame(height: peaks?.isEmpty == false ? Self.waveformHeight : height).frame(maxHeight: .infinity)
        }
        .frame(height: max(peaks?.isEmpty == false ? Self.waveformHeight : height, 16))
        // The AppKit surface takes the press, the drag and the release (a SwiftUI gesture under the window-drag guard never saw them).
        .overlay(PointerSurface(
            onDown: { p, s in dragging = Self.fraction(p, s) },
            onDrag: { p, s in dragging = Self.fraction(p, s) },
            onUp: { p, s in dragging = nil; onCommit(Self.fraction(p, s)) }))
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

    static func fraction(_ p: CGPoint, _ s: CGSize) -> Double { min(max(Double(p.x / max(s.width, 1)), 0), 1) }

    private var shape: AnyShape { rounded ? AnyShape(Capsule()) : AnyShape(Rectangle()) }
}

/// One bar per slice of the width (at most one per two points), each as tall as the peak it stands for, mirrored on the centre line.
struct WaveformBars: Shape {
    let peaks: [Float]

    func path(in rect: CGRect) -> Path {
        var path = Path()
        guard !peaks.isEmpty, rect.width > 0 else { return path }
        let count = max(1, min(peaks.count, Int(rect.width / 2)))
        let step = rect.width / CGFloat(count)
        for i in 0..<count {
            let lo = i * peaks.count / count, hi = max(lo + 1, (i + 1) * peaks.count / count)
            let peak = CGFloat(peaks[lo..<min(hi, peaks.count)].max() ?? 0)
            let h = max(2, peak * rect.height)
            path.addRoundedRect(in: CGRect(x: CGFloat(i) * step + step * 0.15, y: rect.midY - h / 2, width: step * 0.7, height: h),
                                cornerSize: CGSize(width: step * 0.35, height: step * 0.35))
        }
        return path
    }
}
