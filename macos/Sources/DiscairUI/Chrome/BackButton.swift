import SwiftUI

/// "‹ Albums": the way back from an album or artist page to the list it was opened from. The title names the
/// destination so VoiceOver and the label agree. One look per theme.
struct BackButton: View {
    var title: String
    /// Over the dark artist banner (Cupertino): white text on a translucent capsule.
    var onDark = false
    let action: () -> Void

    var body: some View {
        Button(action: action) { Label(title, systemImage: "chevron.left") }
            .buttonStyle(CapsuleButtonStyle(small: true, translucent: onDark))
        .accessibilityLabel("Back to \(title)")
    }
}
