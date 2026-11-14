import SwiftUI

/// A time readout driven by the player's own clock: it re-renders whenever `PlayerModel.position` is written (4 Hz while
/// playing, and on pause and seek), and carries the last reading forward by the time since it was taken (at most 2 s, see
/// `displayPosition`), so a late tick does not freeze the readout. It owns no timer: a paused player costs nothing.
struct PlaybackClock<Content: View>: View {
    let player: PlayerModel
    @ViewBuilder let content: (Double) -> Content

    var body: some View {
        content(player.displayPosition())
    }
}
