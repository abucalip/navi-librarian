import DiscairAudio
import SwiftUI

extension View {
    /// Drag (or click) on an EQ band track: the height maps to -12 .. +12 dB, the middle is 0. The buttons stay as the
    /// other way to change a band.
    func eqBandDrag(trackHeight: CGFloat, onChange: @escaping (Double) -> Void) -> some View {
        self.frame(width: 30, height: trackHeight)
            .contentShape(Rectangle())
            .overlay(PointerSurface(
                onDown: { p, _ in onChange(EQBandDrag.gain(y: p.y, trackHeight: trackHeight)) },
                onDrag: { p, _ in onChange(EQBandDrag.gain(y: p.y, trackHeight: trackHeight)) },
                onUp: { _, _ in }))
    }
}

enum EQBandDrag {
    static func gain(y: CGFloat, trackHeight: CGFloat) -> Double {
        let mid = Double(trackHeight) / 2
        return min(max((mid - Double(y)) / mid * eqMaxGainDB, -eqMaxGainDB), eqMaxGainDB)
    }
}
