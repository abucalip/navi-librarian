import SwiftUI

/// The sleep timer's menu (docs/RADIO_PLAYBACK_PROPOSAL.md S2-4 item 2; mockup "Small pieces", "Sleep timer menu"): Off, then
/// 15 to 90 minutes, a check mark on the running length. The moon shows the minutes left while it runs.
struct SleepTimerMenu: View {
    enum Style { case icon, pill }
    let timer: SleepTimer
    var style: Style = .icon
    /// The bar's text colour, so the moon matches the other controls in Day, Night and over artwork.
    var ink: Color = .primary

    var body: some View {
        Menu {
            SleepTimerChoices(timer: timer)
        } label: {
            switch style {
            case .icon:
                HStack(spacing: 4) {
                    Image(systemName: timer.isRunning ? "moon.fill" : "moon").foregroundStyle(timer.isRunning ? CU.accent : ink)
                    if let text = SleepTimer.shortText(minutesLeft: timer.minutesLeft) { Text(text).font(CU.Font.caption.weighted(.semibold)).monospacedDigit().foregroundStyle(ink) }
                }
            case .pill:
                HStack(spacing: 6) {
                    Image(systemName: timer.isRunning ? "moon.fill" : "moon")
                    Text(SleepTimer.shortText(minutesLeft: timer.minutesLeft) ?? "Sleep").cuRole(CU.Font.callout).fontWeight(.semibold)
                }
                .foregroundStyle(CU.onMedia).padding(.horizontal, 12).padding(.vertical, 4)
                .background(CU.onMedia.opacity(0.18), in: Capsule())
            }
        }
        .menuStyle(.button).buttonStyle(.plain).menuIndicator(.hidden).fixedSize()
        .accessibilityLabel(SleepTimer.spoken(minutesLeft: timer.minutesLeft))
        .help("Sleep timer")
    }
}

/// The entries, shared by the moon, the Sleep button and the Controls menu.
public struct SleepTimerChoices: View {
    let timer: SleepTimer
    public init(timer: SleepTimer) { self.timer = timer }

    public var body: some View {
        Picker("Sleep Timer", selection: Binding(get: { timer.chosen }, set: { timer.start(minutes: $0 ?? 0) })) {
            Text(SleepTimer.entryTitle(nil)).tag(Int?.none)
            ForEach(SleepTimer.lengths, id: \.self) { Text(SleepTimer.entryTitle($0)).tag(Int?.some($0)) }
        }
        .pickerStyle(.inline)
    }
}

/// The words for a station that is not playing plainly. While a try waits, the seconds count down.
struct LivePhaseText: View {
    let live: LiveSession
    var role: CU.Font.Role?

    private func text(_ s: String) -> Text { role.map { Text(s).cuRole($0) } ?? Text(s) }

    var body: some View {
        if live.phase == .reconnecting, live.reconnect != nil {
            SwiftUI.TimelineView(.periodic(from: .now, by: 1)) { tl in text(live.phaseSentence(at: tl.date) ?? "") }
        } else {
            text(live.phaseSentence ?? "")
        }
    }
}

/// Retry on "Station unreachable" (a fresh round of tries).
struct RetryStationButton: View {
    let player: PlayerModel
    var body: some View {
        Button { player.retryStation() } label: {
            Text("Retry").cuRole(CU.Font.callout).fontWeight(.semibold).lineLimit(1).fixedSize()
                .foregroundStyle(CU.accentStrong).padding(.horizontal, 12).padding(.vertical, 4)
                .background(CU.onMedia, in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Retry")
    }
}
