import AppKit
import DiscairLibrarian
import Foundation
import UserNotifications

/// One Get that has just ended, as the owner should read it in a system notification.
public struct GetFinishedEvent: Equatable, Sendable {
    public enum Outcome: Equatable, Sendable { case imported, failed }
    public let id: String
    public let outcome: Outcome
    public let title: String
    public let body: String
}

/// One in-app note about a finished Get (see `AcquisitionModel.toasts`).
public struct GetToast: Identifiable, Equatable, Sendable {
    public let id: String
    public let outcome: GetFinishedEvent.Outcome
    public let title: String
    public let body: String
}

/// Decides which jobs to announce. A job is announced once, when a poll sees it end (imported or failed) after an earlier
/// poll saw it still moving. The first poll after connecting only learns the starting state, so old jobs never notify.
@MainActor
struct GetFinishedDetector {
    private var seen: [String: Acquisition.Phase] = [:]
    private var seeded = false

    /// Forget everything (a new connection); the next poll seeds again.
    mutating func reset() { seen = [:]; seeded = false }

    mutating func events(for jobs: [Acquisition]) -> [GetFinishedEvent] {
        var out: [GetFinishedEvent] = []
        for job in jobs {
            let before = seen[job.id]
            seen[job.id] = job.phase
            guard seeded, let before, Self.isMoving(before) else { continue }
            switch job.phase {
            case .imported: out.append(Self.event(job, .imported))
            case .failed: out.append(Self.event(job, .failed))
            default: break
            }
        }
        seen = seen.filter { entry in jobs.contains { $0.id == entry.key } }   // forget jobs the server dropped
        seeded = true
        return out
    }

    private static func isMoving(_ p: Acquisition.Phase) -> Bool { p == .working || p == .queued || p == .other }

    private static func event(_ job: Acquisition, _ outcome: GetFinishedEvent.Outcome) -> GetFinishedEvent {
        let what = job.title.isEmpty ? job.album : job.title
        switch outcome {
        case .imported:
            return GetFinishedEvent(id: job.id, outcome: .imported, title: "Added to your library",
                                    body: "\(what) by \(job.artist) is ready to play.")
        case .failed:
            let reason = job.details?.message ?? AcquisitionModel.statusText(job)
            return GetFinishedEvent(id: job.id, outcome: .failed, title: "Could not get \(what)",
                                    body: "\(job.artist): \(reason)")
        }
    }
}

/// Shows a finished Get. The model owns the rules; this only delivers.
@MainActor
public protocol GetNotifier: AnyObject {
    func deliver(_ event: GetFinishedEvent)
}

/// Delivers through Notification Center. Does nothing outside an app bundle (`swift run`, tests), where the system
/// would crash on `UNUserNotificationCenter.current()`. Asks permission the first time something is delivered.
@MainActor
public final class SystemGetNotifier: NSObject, GetNotifier, UNUserNotificationCenterDelegate {
    /// Called when the owner clicks a notification; the app opens the Downloads screen.
    public var onOpen: () -> Void = {}
    private var isBundled: Bool { Bundle.main.bundleURL.pathExtension == "app" }

    public override init() {
        super.init()
        if isBundled { UNUserNotificationCenter.current().delegate = self }
    }

    public func deliver(_ event: GetFinishedEvent) {
        guard isBundled else { return }
        let center = UNUserNotificationCenter.current()
        Task {
            guard (try? await center.requestAuthorization(options: [.alert, .sound])) == true else { return }
            let content = UNMutableNotificationContent()
            content.title = event.title
            content.body = event.body
            if event.outcome == .imported { content.sound = .default }
            content.threadIdentifier = "discair.get"
            try? await center.add(UNNotificationRequest(identifier: "get-\(event.id)-\(UUID().uuidString)", content: content, trigger: nil))
        }
    }

    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        await MainActor.run {
            NSApplication.shared.activate(ignoringOtherApps: true)
            onOpen()
        }
    }
}
