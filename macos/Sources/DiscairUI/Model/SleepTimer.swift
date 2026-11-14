import Foundation
import Observation

/// The sleep timer (docs/RADIO_PLAYBACK_PROPOSAL.md S2-4 item 2; the same lengths as Android's `SleepTimer`). Generic: it does not
/// know about stations. When time is up it calls `onExpire` once (the player stops a station or pauses a song). It runs on the wall
/// clock, so a Mac that slept through the end stops on wake.
@MainActor @Observable
public final class SleepTimer {
    /// The lengths offered, in minutes.
    public static let lengths = [15, 30, 45, 60, 90]

    /// When the timer ends, nil while it is off.
    public private(set) var endsAt: Date?
    /// The length that was chosen last (for the check mark in the menu); nil while off.
    public private(set) var chosen: Int?
    /// Whole minutes left, rounded up, so "1 min" is the last thing shown. Nil while off. Updated by the tick.
    public private(set) var minutesLeft: Int?

    @ObservationIgnored public var onExpire: (() -> Void)?
    /// False when nothing is playing any more: the timer is then cancelled instead of firing at nothing.
    @ObservationIgnored public var isPlaying: () -> Bool = { true }
    @ObservationIgnored let now: () -> Date
    @ObservationIgnored let pause: @Sendable (TimeInterval) async -> Void
    @ObservationIgnored private var task: Task<Void, Never>?

    public static let tickInterval: TimeInterval = 1

    public init(now: @escaping () -> Date = Date.init,
                pause: @escaping @Sendable (TimeInterval) async -> Void = { try? await Task.sleep(for: .seconds($0)) }) {
        self.now = now
        self.pause = pause
    }

    public var isRunning: Bool { endsAt != nil }

    /// Starts, or restarts, a timer of `minutes`. Zero or less switches it off.
    public func start(minutes: Int) {
        guard minutes > 0 else { cancel(); return }
        task?.cancel()
        chosen = minutes
        endsAt = now().addingTimeInterval(TimeInterval(minutes) * 60)
        minutesLeft = minutes
        task = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                await self.pause(Self.tickInterval)
                if Task.isCancelled { return }
                self.check()
            }
        }
    }

    public func cancel() {
        task?.cancel(); task = nil
        endsAt = nil; chosen = nil; minutesLeft = nil
    }

    /// One tick (public so a test can drive it without waiting). Fires when due, cancels when nothing plays, else updates the minutes.
    public func check() {
        guard let endsAt else { return }
        if now() >= endsAt {
            cancel()
            onExpire?()
        } else if !isPlaying() {
            cancel()
        } else {
            let left = Self.minutes(left: endsAt.timeIntervalSince(now()))
            if left != minutesLeft { minutesLeft = left }
        }
    }

    /// Minutes left, rounded up.
    static func minutes(left seconds: TimeInterval) -> Int { max(1, Int((seconds / 60).rounded(.up))) }

    // MARK: Words

    /// The label of a menu entry: "15 minutes", or "Off".
    public static func entryTitle(_ minutes: Int?) -> String { minutes.map { "\($0) minutes" } ?? "Off" }

    /// Short text beside the moon while the timer runs: "45 min"; nil while off.
    public static func shortText(minutesLeft: Int?) -> String? { minutesLeft.map { "\($0) min" } }

    /// What VoiceOver reads for the moon.
    public static func spoken(minutesLeft: Int?) -> String {
        guard let minutesLeft else { return "Sleep timer, off" }
        return "Sleep timer, \(minutesLeft) \(minutesLeft == 1 ? "minute" : "minutes") left"
    }
}
