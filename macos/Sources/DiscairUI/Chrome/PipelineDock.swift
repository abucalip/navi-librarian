import SwiftUI

/// The notes for a Get that has ended (imported or failed): bottom left over every screen, gone after 30 seconds. The
/// Pipeline card that used to sit above them is hidden (owner decision); Downloads has the full list.
struct PipelineDockView: View {
    @Bindable var state: AppState

    var body: some View {
        let toasts = state.acquisition.toasts
        let zine = state.themeID == .zine
        // Very bottom left. Zine keeps clear of its player strip along the bottom edge.
        VStack(alignment: .leading, spacing: 8) {
            Spacer(minLength: 0)
            ForEach(toasts) { toast in
                toastCard(toast)
                    .transition(.opacity)
            }
            // The Pipeline card itself is hidden (owner decision); Downloads shows the full list. Only the
            // notes for a Get that started or finished appear, and they fade by themselves.
        }
        .frame(width: Self.width, alignment: .leading)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
        .padding(.leading, zine ? 10 : 246)
        .padding(.bottom, zine ? 70 : CupertinoPlayerBar.height + 14)
        .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 1.2), value: toasts.map(\.id))
        .allowsHitTesting(!toasts.isEmpty)
    }

    static let width: CGFloat = 230

    private func toastCard(_ t: GetToast) -> some View {
        let ok = t.outcome == .imported
        let zine = state.themeID == .zine
        return HStack(alignment: .top, spacing: 8) {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(ok ? Color.green : (zine ? Z.red : CU.accent)).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 2) {
                Text(t.title).font(zine ? Z.serif(13, bold: true) : .system(size: 12, weight: .semibold)).lineLimit(2)
                Text(t.body).font(zine ? Z.mono(10) : .system(size: 11)).opacity(0.75).lineLimit(3)
            }
            Spacer(minLength: 0)
            Button { state.acquisition.dismissToast(t.id) } label: { Image(systemName: "xmark").font(.system(size: 10, weight: .bold)) }
                .buttonStyle(.plain).accessibilityLabel("Dismiss")
        }
        .foregroundStyle(zine ? Z.ink : CU.ink)
        .padding(10)
        .background {
            if zine { Z.paper } else { Rectangle().fill(.regularMaterial) }
        }
        .clipShape(RoundedRectangle(cornerRadius: zine ? 0 : 12, style: .continuous))
        .overlay { if zine { Rectangle().stroke(Z.ink, lineWidth: 3) } else { RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(CU.fill, lineWidth: 1) } }
        .shadow(color: .black.opacity(zine ? 0 : 0.14), radius: 10, y: 3)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(t.title). \(t.body)")
    }
}
