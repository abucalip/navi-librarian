import SwiftUI

/// "Offline, showing the saved library" with a Retry button. Drawn in the Cupertino language; `RootView`
/// puts it above the window content while the screens show a saved copy.
struct OfflineBanner: View {
    let state: AppState
    let text: String
    @State private var retrying = false

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "wifi.slash").foregroundStyle(CU.accent).accessibilityHidden(true)
            Text(text).font(.system(size: 13)).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 8)
            retry.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
        }
        .padding(.horizontal, 16).padding(.vertical, 8)
        .background(CU.bgPanel)
        .overlay(alignment: .bottom) { Rectangle().fill(CU.bgFill).frame(height: 1) }
        .accessibilityElement(children: .contain)
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
