import DiscairLibrarian
import SwiftUI

/// Downloads (redesign 5.3, mockup `downloads--default`): the Librarian's job list, one row per record with the four-circle
/// tracker, the state in words and a filter (All, Active, Needs you, Arrived). A failed row carries the only primary, Try again.
/// The state is always icon plus words, never colour alone. Dismiss only hides the row.
struct CupertinoDownloads: View {
    let state: AppState
    @State private var filter: Filter = .all

    private var acq: AcquisitionModel { state.acquisition }

    enum Filter: String, CaseIterable, Identifiable {
        case all = "All", active = "Active", needsYou = "Needs you", arrived = "Arrived"
        var id: String { rawValue }

        func includes(_ j: Acquisition) -> Bool {
            switch self {
            case .all: true
            case .active: j.phase == .working || j.phase == .queued
            case .needsYou: j.phase == .failed
            case .arrived: j.phase == .imported
            }
        }
    }

    var body: some View {
        let jobs = acq.sortedJobs
        let shown = jobs.filter(filter.includes)
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                HStack(alignment: .firstTextBaseline, spacing: CU.Space.m) {
                    VStack(alignment: .leading, spacing: CU.Space.xs) {
                        Text("Downloads").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                        Text(summary(jobs)).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
                    }
                    Spacer(minLength: CU.Space.s)
                    CUSegmented(Filter.allCases.map { (value: $0, label: $0.rawValue) }, selection: $filter, accessibilityName: "Show")
                }
                .padding(.top, CU.Space.xs)
                if acq.importedCount > 0 {
                    HStack { Spacer(minLength: 0); Button("Clear \(acq.importedCount) imported") { acq.dismissImported() }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true)) }
                }
                if jobs.isEmpty {
                    Text(state.session == nil || state.library.isLive ? "Nothing is downloading. Albums you Get appear here." : "Downloads are available in the running app.")
                        .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
                } else if shown.isEmpty {
                    Text("Nothing in \(filter.rawValue.lowercased()) right now.").cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
                } else {
                    CUPanel {
                        ForEach(Array(shown.enumerated()), id: \.element.id) { i, job in
                            if i > 0 { Divider() }
                            row(job)
                        }
                    }
                    // Circles need less room than bars did: the list takes half the page, never less than a row needs.
                    .containerRelativeFrame(.horizontal, alignment: .leading) { width, _ in max(width / 2, 520) }
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }

    /// "2 on their way · 1 needs you · 3 arrived this week", with the zero parts left out so no count reads as a missing one.
    /// `updatedAt` is the Librarian's epoch seconds; "arrived this week" counts imports changed in the last seven days.
    private func summary(_ jobs: [Acquisition]) -> String {
        let way = jobs.filter { $0.phase == .working || $0.phase == .queued }.count
        let needs = jobs.filter { $0.phase == .failed }.count
        let weekAgo = Date().timeIntervalSince1970 - 7 * 86400
        let arrived = jobs.filter { $0.phase == .imported && ($0.updatedAt ?? 0) >= weekAgo }.count
        let parts = [way > 0 ? "\(way) on their way" : nil, needs > 0 ? "\(needs) needs you" : nil, arrived > 0 ? "\(arrived) arrived this week" : nil]
        let text = parts.compactMap { $0 }.joined(separator: " · ")
        return text.isEmpty ? "Nothing in progress." : text
    }

    private func stageStep(_ j: Acquisition) -> Int {
        j.phase == .imported ? CUChartMath.stageNames.count : HomeDashboard.stage(of: j).rawValue
    }

    private func row(_ j: Acquisition) -> some View {
        let failure = j.phase == .failed ? (j.details?.message ?? acq.statusLine(j)) : nil
        return HStack(alignment: .top, spacing: CU.Space.m) {
            CoverView(album: placeholderAlbum(j)).frame(width: 48, height: 48).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(j.title).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                Text(j.isSong ? "\(j.artist) · Song on \(j.details?.albumName ?? j.album)" : j.artist)
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                CUStageTracker(step: stageStep(j), progress: acq.fraction(j), failed: j.phase == .failed, failureReason: failure, showsNames: true)
                    .padding(.top, CU.Space.xs)
                stateLine(j, failure: failure)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            actions(j)
        }
        .padding(.vertical, CU.Space.s)
        .accessibilityElement(children: .contain)
    }

    /// The state in words under the tracker: the progress line while moving, the arrival line when in the library.
    @ViewBuilder private func stateLine(_ j: Acquisition, failure: String?) -> some View {
        if failure == nil {
            if j.phase == .imported {
                Label("In your library", systemImage: "checkmark.circle").font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.success)
            } else {
                let line = [acq.statusLine(j), acq.progressLine(j)].filter { !$0.isEmpty }.joined(separator: " · ")
                if !line.isEmpty { Text(line).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
            }
        }
        if let rgid = j.details?.releaseGroupMBID { EditionCoverStrip(rgid: rgid) }
    }

    /// One action row. A failed row's Try again is the only primary on the page.
    private func actions(_ j: Acquisition) -> some View {
        VStack(alignment: .trailing, spacing: CU.Space.s) {
            if acq.canRetry(j) { Button("Try again") { Task { await acq.retry(j) } }.buttonStyle(CapsuleButtonStyle(primary: true, small: true)) }
            if acq.canSkip(j) { Button("Use next source") { Task { await acq.skipSource(j) } }.buttonStyle(CapsuleButtonStyle(small: true)) }
            if j.phase != .working || acq.canSkip(j) {
                Button("Dismiss") { acq.dismiss(j) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
            }
        }
    }

    /// The row's cover: the release's artwork is looked up by the same title and artist the library uses.
    private func placeholderAlbum(_ j: Acquisition) -> AlbumItem {
        state.library.albums.first { $0.title == j.title && $0.artist == j.artist }
            ?? AlbumItem(id: -1, title: j.title, artist: j.artist, year: 0, genre: "", format: "", owned: false, hue: LibraryModel.hue(for: j.title))
    }
}
