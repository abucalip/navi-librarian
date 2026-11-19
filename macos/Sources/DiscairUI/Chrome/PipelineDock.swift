import SwiftUI

/// The notes for a Get that has ended (imported or failed): bottom left over every screen, gone after 30 seconds. The
/// Pipeline card (active Gets) sits bottom right above the player bar; Downloads has the full list.
struct PipelineDockView: View {
    @Bindable var state: AppState
    /// The card's measured height. The page scroll views leave this much room above the player bar (D3.1).
    var onCardHeight: (CGFloat) -> Void = { _ in }
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
            // The card lives in the overlay below; the notes for a Get that started or finished fade by themselves.
        }
        .frame(width: Self.width, alignment: .leading)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
        .padding(.leading, 246)
        .padding(.bottom, CupertinoPlayerBar.height + PipelineDockPlacement.barGap)
        .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 1.2), value: toasts.map(\.id))
        .allowsHitTesting(!toasts.isEmpty)
        .overlay(alignment: .bottomTrailing) { pipeline }
    }

    /// The Pipeline card: bottom right, just above the player bar. Hidden on Downloads (which lists everything) and when idle.
    @ViewBuilder private var pipeline: some View {
        let content = state.acquisition.dock
        if PipelineDockPlacement.shows(screen: state.screen, content: content) {
            card(content)
                .frame(width: Self.width + 20)
                .padding(.trailing, PipelineDockPlacement.trailingMargin(queueOpen: state.queueOpen))
                .padding(.bottom, CupertinoPlayerBar.height + PipelineDockPlacement.barGap)
                .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { height in onCardHeight(height) }
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

/// Where the Pipeline card sits and how much room the pages leave for it (D3.1). Pure, so the rules are tested without a window.
@MainActor
enum PipelineDockPlacement {
    /// Between the card and the player bar, in points.
    static let barGap: CGFloat = 14
    /// Between the card and the window's trailing edge, and between the card and the queue when it is open.
    static let margin: CGFloat = 16

    /// The card shows over every screen except Downloads (which lists the jobs) and Now Playing.
    static func shows(screen: Screen, content: PipelineDockContent) -> Bool {
        !content.isEmpty && screen != .downloads && screen != .nowPlaying
    }

    /// From the page's bottom edge (the player bar's top) to the card's top, plus one margin.
    /// The scroll views take this as a bottom content inset, so the last row can scroll clear of the card.
    static func bottomClearance(cardHeight: CGFloat) -> CGFloat {
        barGap + cardHeight + margin
    }

    /// Inside the main column: the queue's width plus the same margin when the queue is open.
    static func trailingMargin(queueOpen: Bool) -> CGFloat {
        queueOpen ? CupertinoQueueInspector.width + margin : margin
    }
}

private struct PipelineDockClearanceKey: EnvironmentKey {
    static let defaultValue: CGFloat = 0
}

extension EnvironmentValues {
    /// The room the page scroll views leave above the player bar while the Pipeline card shows; 0 when it is hidden.
    var pipelineDockClearance: CGFloat {
        get { self[PipelineDockClearanceKey.self] }
        set { self[PipelineDockClearanceKey.self] = newValue }
    }
}
