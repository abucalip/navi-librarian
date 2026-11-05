import SwiftUI

/// The "this is playing" mark: moving bars while the song plays, still bars while it is paused.
struct PlayingBars: View {
    let active: Bool
    var body: some View {
        Image(systemName: "waveform")
            .symbolEffect(.variableColor.iterative.dimInactiveLayers, options: .repeating, isActive: active)
            .accessibilityLabel(active ? "Playing" : "Paused")
    }
}
