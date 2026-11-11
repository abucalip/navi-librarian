import SwiftUI

// Cupertino controls (redesign M2). Spec: section 4.3 of `docs/redesign.md` and `components--tokens-and-controls`.

// MARK: Panel ground

private struct CUInPanelKey: EnvironmentKey { static let defaultValue = false }

extension EnvironmentValues {
    /// True inside a `CUPanel`: neutral fills switch from `bg.fill` to `bg.fill.onPanel` so they stay visible on the grey ground.
    var cuInPanel: Bool {
        get { self[CUInPanelKey.self] }
        set { self[CUInPanelKey.self] = newValue }
    }
}

/// Grouped panel: `bg.panel`, radius 24, padding 16 (so covers and tiles inside use radius 8). Tonal, never shadowed.
struct CUPanel<Content: View>: View {
    var title: String?
    @ViewBuilder var content: Content

    init(_ title: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            if let title {
                Text(title).cuRole(CU.Font.title3).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
            }
            content
        }
        .padding(CU.Space.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .environment(\.cuInPanel, true)
    }
}

// MARK: Buttons

enum CUButtonSize: Equatable {
    case large, regular, small

    /// Heights from section 4.3: 40, 32, 24.
    var height: CGFloat { self == .large ? 40 : (self == .regular ? 32 : 24) }
    var labelSize: CGFloat { self == .large ? 14 : (self == .regular ? 13 : 12) }
    /// 12 is the one documented exception to the spacing scale (small button padding).
    var horizontalPadding: CGFloat { self == .large ? 24 : (self == .regular ? 16 : 12) }
}

/// Capsule button. Primary: accent fill and white label, one per view. Secondary (default): neutral fill.
/// Tertiary (`outlined`): 1 pt `separator.strong` outline, secondary label. Destructive: danger label on a neutral fill, never a red fill.
struct CapsuleButtonStyle: ButtonStyle {
    var primary = false
    var small = false
    var outlined = false
    var large = false
    /// White text on a 28% white fill, for buttons over a banner image.
    var translucent = false
    var destructive = false
    @Environment(\.cuInPanel) private var inPanel
    @Environment(\.isEnabled) private var isEnabled

    var size: CUButtonSize { large ? .large : (small ? .small : .regular) }

    func makeBody(configuration: Configuration) -> some View {
        let neutral = inPanel ? CU.bgFillOnPanel : CU.bgFill
        configuration.label
            .font(.system(size: size.labelSize, weight: .semibold))
            .lineLimit(1).fixedSize()
            .padding(.horizontal, size.horizontalPadding)
            .frame(minHeight: size.height)
            .foregroundStyle(labelColor)
            .background(fill(neutral: neutral, pressed: configuration.isPressed), in: Capsule())
            .overlay { if outlined && !primary { Capsule(style: .circular).inset(by: 0.5).stroke(CU.separatorStrong, lineWidth: 1) } }
            .opacity(configuration.isPressed && !primary ? 0.8 : 1)
    }

    private var labelColor: Color {
        if !isEnabled { return CU.textTertiary }
        if primary { return CU.onAccent }
        if translucent { return CU.onMedia }
        if destructive { return CU.danger }
        return outlined ? CU.textSecondary : CU.text
    }

    private func fill(neutral: Color, pressed: Bool) -> Color {
        if primary { return isEnabled ? (pressed ? CU.accentStrong : CU.accent) : CU.bgFill }
        if translucent { return CU.onMedia.opacity(0.28) }
        return outlined ? .clear : neutral
    }
}

// MARK: Segmented control

/// Track `bg.fill` (on a panel, `bg.fill.onPanel`), radius 8, padding 2; segment 24 high, the selected one white with a hairline shadow.
struct CUSegmented<Value: Hashable>: View {
    let options: [(value: Value, label: String)]
    @Binding var selection: Value
    var accessibilityName: String?
    /// Segment height: 24, or 28 in a control bar.
    var segmentHeight: CGFloat = 24
    @Environment(\.cuInPanel) private var inPanel

    init(_ options: [(value: Value, label: String)], selection: Binding<Value>, accessibilityName: String? = nil, inControlBar: Bool = false) {
        self.options = options
        self._selection = selection
        self.accessibilityName = accessibilityName
        self.segmentHeight = inControlBar ? 28 : 24
    }

    var body: some View {
        HStack(spacing: 0) {
            ForEach(options, id: \.value) { option in
                let on = option.value == selection
                Button { selection = option.value } label: {
                    Text(option.label)
                        .font(CU.Font.callout.weighted(on ? .semibold : .medium))
                        .foregroundStyle(on ? CU.text : CU.textSecondary)
                        .padding(.horizontal, 16).frame(height: segmentHeight)
                        .background {
                            if on {
                                RoundedRectangle(cornerRadius: 4, style: .continuous).fill(CU.content)
                                    .shadow(color: CU.shadowInk.opacity(0.14), radius: 1.5, y: 1)
                                    .shadow(color: CU.shadowInk.opacity(0.06), radius: 0.5)
                            }
                        }
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .padding(2)   // spec exception: the segmented track is padded 2 (section 4.3)
        .background(inPanel ? CU.bgFillOnPanel : CU.bgFill, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityLabel(accessibilityName ?? "")
    }
}

extension CUSegmented where Value == String {
    init(options: [String], selection: Binding<String>) {
        self.init(options.map { (value: $0, label: $0) }, selection: selection)
    }
}

// MARK: Status

/// What a service or job can be, in the shared vocabulary of section 3. Always an icon and a word, never colour alone.
enum CUStatus: Equatable {
    case connected, loaded, done, paused, notSetUp, notLoaded, unknown, notUpdating, noAnswer
    /// "<reason> rejected", for example "Token rejected".
    case rejected(String)

    enum Kind: Equatable { case success, warning, danger, info, neutral }

    var text: String {
        switch self {
        case .connected: "Connected"
        case .loaded: "Loaded"
        case .done: "Done"
        case .paused: "Paused"
        case .notSetUp: "Not set up"
        case .notLoaded: "Not loaded"
        case .unknown: "Unknown"
        case .notUpdating: "Not updating"
        case .noAnswer: "No answer"
        case .rejected(let reason): "\(reason) rejected"
        }
    }

    var kind: Kind {
        switch self {
        case .connected, .loaded, .done: .success
        case .notUpdating: .warning
        case .rejected, .noAnswer: .danger
        case .paused, .notLoaded: .info
        case .notSetUp, .unknown: .neutral
        }
    }

    /// check-circle (success), triangle (warning), x-circle (danger), info-circle (info), minus (unknown or off).
    var symbol: String {
        switch kind {
        case .success: "checkmark.circle"
        case .warning: "exclamationmark.triangle"
        case .danger: "xmark.circle"
        case .info: "info.circle"
        case .neutral: "minus"
        }
    }

    var color: Color {
        switch kind {
        case .success: CU.success
        case .warning: CU.warning
        case .danger: CU.danger
        case .info: CU.info
        case .neutral: CU.textSecondary
        }
    }
}

struct CUStatusLabel: View {
    let status: CUStatus

    init(_ status: CUStatus) { self.status = status }

    var body: some View {
        HStack(spacing: CU.Space.xs) {
            Image(systemName: status.symbol).font(CU.Icon.small()).accessibilityHidden(true)
            Text(status.text)
        }
        .font(CU.Font.callout.weighted(.semibold))
        .foregroundStyle(status.color)
        .lineLimit(1)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(status.text)
    }
}

// MARK: Error line

/// An inline error in a view's flow: danger colour, a warning icon and the words. Never the accent (the accent is the main action).
/// `onDark` is for a ground that is dark (the player's tint), where danger would not reach contrast; the icon and words still carry it.
struct CUErrorLine: View {
    let message: String
    var onDark = false

    var body: some View {
        Label(message, systemImage: "exclamationmark.triangle.fill")
            .foregroundStyle(onDark ? CU.onMedia : CU.danger)
            .accessibilityLabel("Problem: \(message)")
    }
}

// MARK: Notice

/// Tinted strip, radius 16, padding 8 by 16: icon, bold lead-in, sentence, and one small button at the trailing edge.
struct CUNotice: View {
    enum Kind: Equatable { case info, warning, danger, success }

    let kind: Kind
    let lead: String
    var message: String = ""
    var actionTitle: String?
    var action: (() -> Void)?

    private var symbol: String {
        switch kind {
        case .info: "info.circle"
        case .warning: "exclamationmark.triangle"
        case .danger: "xmark.circle"
        case .success: "checkmark.circle"
        }
    }
    private var color: Color {
        switch kind {
        case .info: CU.info
        case .warning: CU.warning
        case .danger: CU.danger
        case .success: CU.success
        }
    }
    private var tint: Color {
        switch kind {
        case .info: CU.infoTint
        case .warning: CU.warningTint
        case .danger: CU.dangerTint
        case .success: CU.successTint
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: CU.Space.s) {
            Image(systemName: symbol).font(CU.Icon.row()).foregroundStyle(color).padding(.top, 4).accessibilityHidden(true)
            (Text(lead).fontWeight(.semibold) + Text(message.isEmpty ? "" : " " + message))
                .font(CU.Font.body.weighted(.regular)).foregroundStyle(color)
                .frame(maxWidth: .infinity, alignment: .leading)
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .buttonStyle(CapsuleButtonStyle(small: true))
                    .environment(\.cuInPanel, false)
            }
        }
        .padding(.horizontal, CU.Space.m).padding(.vertical, CU.Space.s)
        .background(tint, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .contain)
    }
}

// MARK: Field

/// Label above (11 Semibold secondary), 28 high, radius 8, 1 pt border; focus is a 3 pt accent ring at 28%;
/// an error is a danger border plus an icon and a sentence below. The placeholder is an example, never the label.
struct CUField: View {
    let label: String
    @Binding var text: String
    var placeholder = ""
    var help: String?
    var error: String?
    var secure = false
    var width: CGFloat?
    @FocusState private var focused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            Text(label).font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.textSecondary)
            Group {
                if secure { SecureField(placeholder, text: $text) } else { TextField(placeholder, text: $text) }
            }
            .textFieldStyle(.plain).autocorrectionDisabled()
            .font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.text)
            .focused($focused)
            .padding(.horizontal, CU.Space.s).frame(height: 28)
            .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .strokeBorder(error != nil ? CU.danger : (focused ? CU.accent : CU.separatorStrong), lineWidth: 1)
            }
            .overlay {
                if focused && error == nil {
                    RoundedRectangle(cornerRadius: 8, style: .continuous).inset(by: -2.5).stroke(CU.accent.opacity(0.28), lineWidth: 3)
                }
            }
            .accessibilityLabel(label)
            if let error {
                HStack(spacing: CU.Space.xs) {
                    Image(systemName: "exclamationmark.triangle").accessibilityHidden(true)
                    Text(error)
                }
                .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.danger)
            } else if let help {
                Text(help).font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
            }
        }
        .frame(width: width, alignment: .leading)
    }
}

// MARK: Switch row

/// A labelled system switch with accent tint, replacing every pair of On and Off capsules.
struct CUSwitchRow: View {
    let title: String
    @Binding var isOn: Bool
    var detail: String?

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            Toggle(isOn: $isOn) {
                Text(title).font(CU.Font.body.weighted(.semibold)).foregroundStyle(CU.text)
            }
            .toggleStyle(.switch).tint(CU.accent)
            if let detail { Text(detail).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary) }
        }
    }
}
