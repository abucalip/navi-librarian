import DiscairLibrarian
import Foundation

/// What the Pipeline dock shows: the Gets that are moving or waiting, in a small tray over every screen while the owner
/// listens. Pure, so the rules are tested without a window.
@MainActor
struct PipelineDockContent: Equatable {
    struct Row: Equatable, Identifiable {
        let id: String
        let title: String
        let artist: String
        let status: String
        /// 0...1 when the server reports a percentage; `nil` shows an unfilled "working" bar.
        let fraction: Double?
        let waiting: Bool
    }

    static let maxRows = 3

    let rows: [Row]
    /// Active jobs beyond the rows shown.
    let more: Int
    /// Failed jobs still on the Downloads screen, so a failure is never hidden by the dock closing itself.
    let failed: Int
    let activeCount: Int

    var isEmpty: Bool { activeCount == 0 && failed == 0 }

    /// Header text. Words, never colour alone.
    var headline: String {
        var parts: [String] = []
        if activeCount > 0 { parts.append(activeCount == 1 ? "1 download" : "\(activeCount) downloads") }
        if failed > 0 { parts.append(failed == 1 ? "1 failed" : "\(failed) failed") }
        return parts.joined(separator: " · ")
    }

    init(jobs: [Acquisition]) {
        let active = jobs.filter { $0.phase == .working || $0.phase == .queued }
            .sorted { a, b in
                if (a.phase == .working) != (b.phase == .working) { return a.phase == .working }
                return (a.updatedAt ?? 0) > (b.updatedAt ?? 0)
            }
        activeCount = active.count
        failed = jobs.filter { $0.phase == .failed }.count
        rows = active.prefix(Self.maxRows).map { j in
            let pct = j.details?.liveProgress?.percent
            return Row(id: j.id, title: j.title, artist: j.artist, status: AcquisitionModel.statusText(j),
                       fraction: pct.map { min(max($0 / 100, 0), 1) }, waiting: j.phase == .queued)
        }
        more = max(0, active.count - Self.maxRows)
    }
}

extension AcquisitionModel {
    var dock: PipelineDockContent { PipelineDockContent(jobs: visibleJobs) }
}
