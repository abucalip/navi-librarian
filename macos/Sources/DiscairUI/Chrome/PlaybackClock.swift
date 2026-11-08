import SwiftUI

/// A time readout that redraws on its own schedule from the player's audio clock, so it keeps moving even when the
/// model's own tick is late. `format` turns the current position into the text.
struct PlaybackClock<Content: View>: View {
    let player: PlayerModel
    @ViewBuilder let content: (Double) -> Content

    var body: some View {
        SwiftUI.TimelineView(.periodic(from: .now, by: 0.25)) { context in
            content(player.displayPosition(at: context.date))
        }
    }
}
