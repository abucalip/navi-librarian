import SwiftUI

/// "Offline, showing the saved library" with a Retry button. One per theme, drawn in that theme's language; `RootView`
/// puts it above the window content while the screens show a saved copy.
struct OfflineBanner: View {
    let state: AppState
    let text: String
    @State private var retrying = false

    var body: some View {
        switch state.themeID {
        case .cupertino:
            HStack(spacing: 10) {
                Image(systemName: "wifi.slash").foregroundStyle(CU.accent).accessibilityHidden(true)
                Text(text).font(.system(size: 13)).foregroundStyle(CU.ink).fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 8)
                retry.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
            }
            .padding(.horizontal, 16).padding(.vertical, 8)
            .background(CU.card)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.fill).frame(height: 1) }
            .accessibilityElement(children: .contain)
        case .zine:
            HStack(spacing: 12) {
                Text(text).font(Z.serif(13)).fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 8)
                retry.buttonStyle(ZineButtonStyle(small: true))
            }
            .padding(.horizontal, 16).padding(.vertical, 8)
            .background(Z.yellow)
            .zBorder(3)
            .accessibilityElement(children: .contain)
        }
    }

    private var retry: some View {
        Button(retrying ? "Trying…" : "Retry") {
            retrying = true
            Task { await state.retryConnection(); retrying = false }
        }
        .disabled(retrying)
        .accessibilityLabel("Retry the connection")
    }
}
