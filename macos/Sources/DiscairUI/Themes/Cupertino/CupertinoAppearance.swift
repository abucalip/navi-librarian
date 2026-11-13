import SwiftUI

/// Settings > Appearance: the theme (Cupertino is the only one), Day or Night, and the accent colour as a hue slider with a
/// button back to the default. A change rebuilds the window (`RootView`), so the slider shows its colour live in the preview
/// panel while it moves and applies it to the app when the owner lets go.
struct CupertinoAppearance: View {
    let state: AppState
    /// The hue being dragged or nudged, not yet applied to the app.
    @State private var pending: Double?
    @State private var dragging = false

    private var appearance: AppearanceModel { state.appearance }
    private var hue: Double { pending ?? appearance.sliderHue }
    private var shown: CUPalette { CUPalette.make(appearance.mode, accentHue: pending ?? appearance.accentHue) }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            themePanel
            modePanel
            accentPanel
        }
    }

    // MARK: Theme

    private var themePanel: some View {
        CUPanel("Theme") {
            HStack(spacing: CU.Space.m) {
                RoundedRectangle(cornerRadius: CU.Space.s, style: .continuous)
                    .fill(CU.backdrop)
                    .overlay(alignment: .leading) { RoundedRectangle(cornerRadius: 4, style: .continuous).fill(CU.bgPanel).frame(width: 14).padding(4) }
                    .frame(width: 56, height: 40)
                    .overlay(RoundedRectangle(cornerRadius: CU.Space.s, style: .continuous).stroke(CU.separatorStrong, lineWidth: 1))
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: CU.Space.xs) {
                    Text("Cupertino").cuRole(CU.Font.headline).foregroundStyle(CU.text)
                    Text("Glass sidebar, opaque content, bold titles. The only theme.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                }
                Spacer(minLength: CU.Space.m)
                Label("In use", systemImage: "checkmark.circle.fill").font(CU.Font.callout.font).foregroundStyle(CU.accentStrong)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Theme: Cupertino, in use")
        }
    }

    // MARK: Day and Night

    private var modePanel: some View {
        CUPanel("Mode") {
            row("Appearance", detail: "Day is the light look. Night is near black. Your accent colour stays when you switch.") {
                CUSegmented(AppearanceMode.allCases.map { (value: $0, label: $0.rawValue) },
                            selection: Binding(get: { appearance.mode }, set: { pending = nil; appearance.setMode($0) }),
                            accessibilityName: "Day or Night")
            }
        }
    }

    // MARK: Accent

    private var accentPanel: some View {
        CUPanel("Accent colour") {
            Text("Used for the main button, the selected row and the highlighted bar in charts.")
                .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            preview
            CUHueSlider(mode: appearance.mode, hue: hue, onChange: { pending = $0 }, onDragging: { dragging = $0 })
                .task(id: pending) {
                    // A key press or a VoiceOver step has no drag end, so it applies after a short pause.
                    guard let value = pending, !dragging else { return }
                    try? await Task.sleep(for: .milliseconds(500))
                    guard !Task.isCancelled, !dragging else { return }
                    appearance.setAccentHue(value)
                    pending = nil
                }
            HStack(spacing: CU.Space.s) {
                Button(appearance.mode == .night ? "Back to coral" : "Back to default") { pending = nil; appearance.resetAccent() }
                    .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                    .disabled(appearance.isDefaultAccent && pending == nil)
                    .accessibilityLabel("Reset the accent colour to the default")
                Text(appearance.isDefaultAccent && pending == nil ? "Default accent" : "Hue \(Int(hue.rounded()))°")
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).monospacedDigit()
            }
        }
    }

    /// A small sample drawn from the palette of the hue being dragged, so the slider is live before it is applied.
    private var preview: some View {
        let p = shown
        return HStack(spacing: CU.Space.m) {
            Text("Get album").font(.system(size: 13, weight: .semibold)).foregroundStyle(p.onAccent.color)
                .padding(.horizontal, CU.Space.m).frame(minHeight: 32).background(p.accent.color, in: Capsule())
            HStack(spacing: CU.Space.s) {
                Image(systemName: "house").font(CU.Icon.row())
                Text("Home").font(.system(size: 13, weight: .semibold))
            }
            .foregroundStyle(p.accentStrong.color).padding(.horizontal, CU.Space.m).frame(minHeight: 32)
            .background(p.accentTint.color, in: RoundedRectangle(cornerRadius: CU.Shell.rowRadius, style: .continuous))
            HStack(alignment: .bottom, spacing: 4) {
                ForEach(Array([14, 22, 18, 28, 24, 34].enumerated()), id: \.offset) { i, h in
                    RoundedRectangle(cornerRadius: 3, style: .continuous).fill(i == 5 ? p.accent.color : p.chart3.color).frame(width: 12, height: CGFloat(h))
                }
            }
            .frame(height: 34, alignment: .bottom)
            Spacer(minLength: 0)
        }
        .padding(CU.Space.m)
        .background(p.content.color, in: RoundedRectangle(cornerRadius: CU.Space.m, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: CU.Space.m, style: .continuous).stroke(p.separatorStrong.color, lineWidth: 1))
        .accessibilityHidden(true)
    }

    private func row<Control: View>(_ title: String, detail: String, @ViewBuilder control: () -> Control) -> some View {
        HStack(alignment: .center, spacing: CU.Space.l) {
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(title).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                Text(detail).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: CU.Space.m)
            control()
        }
    }
}

/// A slider across the hues. Its track shows each hue as the accent it would give in this mode. Dragging reports the hue
/// live (`onChange`); the caller applies it when the drag ends. Arrow keys and VoiceOver step by 5 and 10 degrees.
struct CUHueSlider: View {
    let mode: AppearanceMode
    let hue: Double
    var onChange: (Double) -> Void
    var onDragging: (Bool) -> Void
    @State private var dragStarted = false
    @FocusState private var focused: Bool

    private static let thumb: CGFloat = 24
    private static let trackHeight: CGFloat = 16

    private var stops: [Color] { (0...12).map { CUPalette.make(mode, accentHue: Double($0) * 30).accent.color } }

    var body: some View {
        GeometryReader { g in
            let travel = max(g.size.width - Self.thumb, 1)
            ZStack(alignment: .leading) {
                Capsule().fill(LinearGradient(colors: stops, startPoint: .leading, endPoint: .trailing))
                    .frame(height: Self.trackHeight).padding(.horizontal, Self.thumb / 2 - 4)
                Circle().fill(CUPalette.make(mode, accentHue: hue).accent.color)
                    .overlay(Circle().stroke(CU.text, lineWidth: 2.5))
                    .frame(width: Self.thumb, height: Self.thumb)
                    .offset(x: travel * hue / 360)
                    .shadow(color: CU.shadowInk.opacity(0.25), radius: 2, y: 1)
            }
            .frame(maxHeight: .infinity)
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0)
                .onChanged { v in
                    if !dragStarted { dragStarted = true; onDragging(true) }
                    onChange(min(max((v.location.x - Self.thumb / 2) / travel, 0), 1) * 360)
                }
                .onEnded { _ in dragStarted = false; onDragging(false) })
        }
        .frame(height: 32)
        .focusable().focused($focused)
        .onKeyPress(.leftArrow) { onChange(hue - 5); return .handled }
        .onKeyPress(.rightArrow) { onChange(hue + 5); return .handled }
        .accessibilityElement()
        .accessibilityLabel("Accent colour")
        .accessibilityValue("Hue \(Int(hue.rounded())) degrees")
        .accessibilityAdjustableAction { direction in
            switch direction {
            case .increment: onChange(hue + 10)
            case .decrement: onChange(hue - 10)
            @unknown default: break
            }
        }
    }
}
