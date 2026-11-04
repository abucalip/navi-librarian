import DiscairAudio
import SwiftUI

extension View {
    /// Drag (or click) on an EQ band track: the height maps to -12 .. +12 dB, the middle is 0. The buttons stay as the
    /// other way to change a band.
    func eqBandDrag(trackHeight: CGFloat, onChange: @escaping (Double) -> Void) -> some View {
        self.frame(width: 30, height: trackHeight)
            .contentShape(Rectangle())
            .blocksWindowDrag()
            .gesture(DragGesture(minimumDistance: 0, coordinateSpace: .local).onChanged {
                onChange(EQBandDrag.gain(y: $0.location.y, trackHeight: trackHeight))
            })
    }
}

enum EQBandDrag {
    static func gain(y: CGFloat, trackHeight: CGFloat) -> Double {
        let mid = Double(trackHeight) / 2
        return min(max((mid - Double(y)) / mid * eqMaxGainDB, -eqMaxGainDB), eqMaxGainDB)
    }
}
