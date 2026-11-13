import SwiftUI

/// The notes for a Get that has ended (imported or failed): bottom left over every screen, gone after 30 seconds. The
/// Pipeline card (active Gets) sits bottom right above the player bar; Downloads has the full list.
struct PipelineDockView: View {
    @Bindable var state: AppState
    @State private var folded = false

    var body: some View {
        let toasts = state.acquisition.toasts
        // Very bottom left, clear of the sidebar.
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
        .padding(.leading, 246)
        .padding(.bottom, CupertinoPlayerBar.height + 14)
        .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 1.2), value: toasts.map(\.id))
        .allowsHitTesting(!toasts.isEmpty)
        .overlay(alignment: .bottomTrailing) { pipeline }
    }

    /// The Pipeline card: bottom right, just above the player bar. Hidden on Downloads (which lists everything) and when idle.
    @ViewBuilder private var pipeline: some View {
        let content = state.acquisition.dock
        if !content.isEmpty && state.screen != .downloads && state.screen != .nowPlaying {
            card(content)
                .frame(width: Self.width + 20)
                .padding(.trailing, state.queueOpen ? CupertinoQueueInspector.width + 16 : 16)
                .padding(.bottom, CupertinoPlayerBar.height + 14)
                .transition(.move(edge: .trailing).combined(with: .opacity))
                .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 0.18), value: folded)
        }
    }

    static let width: CGFloat = 230

    private func toastCard(_ t: GetToast) -> some View {
        let ok = t.outcome == .imported
        return HStack(alignment: .top, spacing: 8) {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(ok ? Color.green : CU.accent).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 2) {
                Text(t.title).font(.system(size: 12, weight: .semibold)).lineLimit(2)
                Text(t.body).font(.system(size: 11)).opacity(0.75).lineLimit(3)
            }
            Spacer(minLength: 0)
            Button { state.acquisition.dismissToast(t.id) } label: { Image(systemName: "xmark").font(.system(size: 10, weight: .bold)) }
                .buttonStyle(.plain).accessibilityLabel("Dismiss")
        }
        .foregroundStyle(CU.text)
        .padding(10)
        .background(Rectangle().fill(.regularMaterial))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay { RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(CU.bgFill, lineWidth: 1) }
        .shadow(color: .black.opacity(0.14), radius: 10, y: 3)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(t.title). \(t.body)")
    }

    private func card(_ c: PipelineDockContent) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            header(c, font: .system(size: 12, weight: .semibold), color: CU.text)
            if !folded { ForEach(c.rows) { row($0) }; overflow(c) }
        }
        .padding(12)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(CU.bgFill, lineWidth: 1))
        .shadow(color: .black.opacity(0.14), radius: 12, y: 4)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Pipeline, \(c.headline)")
    }

    private func header(_ c: PipelineDockContent, font: Font, color: Color) -> some View {
        HStack(spacing: 8) {
            Button { state.screen = .downloads } label: {
                HStack(spacing: 6) {
                    Text("Pipeline").font(font)
                    Text(c.headline).font(font).opacity(0.7)
                }
                .foregroundStyle(color)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Open Downloads, \(c.headline)")
            Spacer(minLength: 0)
            Button { folded.toggle() } label: {
                Image(systemName: folded ? "chevron.up" : "chevron.down").font(.system(size: 11, weight: .bold)).foregroundStyle(color)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(folded ? "Show the downloads" : "Fold the downloads")
        }
    }

    private func row(_ r: PipelineDockContent.Row) -> some View {
        return VStack(alignment: .leading, spacing: 3) {
            Text(r.title).font(.system(size: 13, weight: .medium)).lineLimit(1)
            Text(r.waiting ? "Waiting · \(r.status)" : r.status)
                .font(.system(size: 11)).opacity(0.7).lineLimit(1)
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Rectangle().fill(CU.bgFill)
                    Rectangle().fill(CU.accent).frame(width: g.size.width * (r.fraction ?? (r.waiting ? 0 : 0.12)))
                }
                .clipShape(RoundedRectangle(cornerRadius: 2))
            }
            .frame(height: 4).accessibilityHidden(true)
        }
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder private func overflow(_ c: PipelineDockContent) -> some View {
        if c.more > 0 {
            Text("and \(c.more) more").font(.system(size: 11)).opacity(0.7)
        }
    }
}
