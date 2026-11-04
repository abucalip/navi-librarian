import SwiftUI

/// The Pipeline dock: acquisition progress in a persistent tray while listening (contract section 6.5). Bottom right
/// over every screen except Downloads, which already shows the full list. Tap the header to open Downloads; the chevron
/// folds it to one line. One per theme, drawn in that theme's language.
struct PipelineDockView: View {
    @Bindable var state: AppState
    @State private var folded = false

    var body: some View {
        let content = state.acquisition.dock
        VStack(alignment: .trailing, spacing: 0) {
            Spacer(minLength: 0)
            HStack(spacing: 0) {
                Spacer(minLength: 0)
                if !content.isEmpty && state.screen != .downloads {
                    card(content)
                        .frame(width: 300)
                        .padding(.trailing, 16)
                        .padding(.bottom, 96) // clear of both themes' player strips
                        .transition(.move(edge: .trailing).combined(with: .opacity))
                }
            }
        }
        .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 0.18), value: content.isEmpty)
        .animation(RenderMode.offscreenScreenshot ? nil : .easeOut(duration: 0.18), value: folded)
    }

    @ViewBuilder private func card(_ c: PipelineDockContent) -> some View {
        switch state.themeID {
        case .cupertino:
            VStack(alignment: .leading, spacing: 8) {
                header(c, font: .system(size: 12, weight: .semibold), color: CU.ink)
                if !folded { ForEach(c.rows) { row($0) } ; overflow(c) }
            }
            .padding(12)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(CU.fill, lineWidth: 1))
            .shadow(color: .black.opacity(0.14), radius: 12, y: 4)
            .accessibilityElement(children: .contain)
            .accessibilityLabel("Pipeline, \(c.headline)")
        case .zine:
            VStack(alignment: .leading, spacing: 8) {
                header(c, font: Z.mono(11, bold: true), color: Z.ink)
                if !folded { ForEach(c.rows) { row($0) } ; overflow(c) }
            }
            .padding(12)
            .background(Z.paper)
            .zBorder(3)
            .background(Z.ink.offset(x: 4, y: 4))
            .accessibilityElement(children: .contain)
            .accessibilityLabel("Pipeline, \(c.headline)")
        }
    }

    private func header(_ c: PipelineDockContent, font: Font, color: Color) -> some View {
        HStack(spacing: 8) {
            Button { state.screen = .downloads } label: {
                HStack(spacing: 6) {
                    Text(state.themeID == .zine ? "PIPELINE" : "Pipeline").font(font)
                    Text(c.headline).font(font).opacity(0.7)
                }
                .foregroundStyle(color)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Open Downloads, \(c.headline)")
            Spacer(minLength: 0)
            Button { folded.toggle() } label: {
                Image(systemName: folded ? "chevron.up" : "chevron.down").font(.system(size: 11, weight: .bold))
                    .foregroundStyle(color)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(folded ? "Show the downloads" : "Fold the downloads")
        }
    }

    private func row(_ r: PipelineDockContent.Row) -> some View {
        let zine = state.themeID == .zine
        return VStack(alignment: .leading, spacing: 3) {
            Text(r.title).font(zine ? Z.serif(13, bold: true) : .system(size: 13, weight: .medium)).lineLimit(1)
            HStack(spacing: 6) {
                Text(r.waiting ? "Waiting · \(r.status)" : r.status)
                    .font(zine ? Z.mono(10) : .system(size: 11)).opacity(0.7).lineLimit(1)
            }
            bar(r, zine: zine)
        }
        .accessibilityElement(children: .combine)
    }

    private func bar(_ r: PipelineDockContent.Row, zine: Bool) -> some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Rectangle().fill(zine ? Z.ink.opacity(0.12) : CU.fill)
                Rectangle().fill(zine ? Z.red : CU.accent)
                    .frame(width: g.size.width * (r.fraction ?? (r.waiting ? 0 : 0.12)))
            }
            .clipShape(RoundedRectangle(cornerRadius: zine ? 0 : 2))
        }
        .frame(height: 4)
        .accessibilityHidden(true)
    }

    @ViewBuilder private func overflow(_ c: PipelineDockContent) -> some View {
        if c.more > 0 {
            Text("and \(c.more) more").font(state.themeID == .zine ? Z.mono(10) : .system(size: 11)).opacity(0.7)
        }
    }
}
