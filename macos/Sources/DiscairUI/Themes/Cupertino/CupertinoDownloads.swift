import DiscairLibrarian
import SwiftUI

/// Downloads: the Librarian's job list. No mockup exists; it follows Cupertino's rules (bold sans title, opaque
/// white content, grouped cards, red-pink accent). State is icon plus words, never colour alone. Dismiss only hides the card.
struct CupertinoDownloads: View {
    let state: AppState

    private var acq: AcquisitionModel { state.acquisition }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .firstTextBaseline) {
                    Text("Downloads").font(CU.title(34)).accessibilityAddTraits(.isHeader)
                    Spacer()
                    if acq.importedCount > 0 {
                        Button("Clear \(acq.importedCount) imported") { acq.dismissImported() }
                            .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                    }
                }
                .padding(.top, 4)
                if acq.visibleJobs.isEmpty {
                    Text(state.session == nil || state.library.isLive ? "Nothing is downloading. Albums you Get appear here." : "Downloads are available in the running app.")
                        .foregroundStyle(CU.muted).padding(.top, 8)
                }
                ForEach(acq.sortedJobs) { job in row(job) }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }

    private func icon(_ j: Acquisition) -> String {
        switch j.phase {
        case .working: "arrow.down.circle.fill"
        case .queued: "clock"
        case .imported: "checkmark.circle.fill"
        case .failed: "exclamationmark.triangle.fill"
        case .other: "questionmark.circle"
        }
    }

    private func row(_ j: Acquisition) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                Image(systemName: icon(j)).font(.system(size: 22))
                    .foregroundStyle(j.phase == .failed || j.phase == .working ? CU.accent : CU.muted)
                    .frame(width: 28).accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 2) {
                    Text(j.title).font(.system(size: 15, weight: .semibold)).lineLimit(1)
                    Text(j.isSong ? "\(j.artist) · Song on \(j.details?.albumName ?? j.album)" : j.artist)
                        .font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
                }
                Spacer()
                Text(acq.statusLine(j)).font(.system(size: 12, weight: .semibold))
                    .padding(.horizontal, 10).padding(.vertical, 3)
                    .background(CU.fill, in: Capsule())
            }
            if let f = acq.fraction(j) {
                ProgressView(value: f).tint(CU.accent).accessibilityLabel("Download progress").accessibilityValue("\(Int(f * 100)) percent")
            }
            let line = acq.progressLine(j)
            if !line.isEmpty { Text(line).font(.system(size: 12)).foregroundStyle(CU.muted) }
            if j.phase == .failed, let m = j.details?.message { Text(m).font(.system(size: 12)).foregroundStyle(CU.muted) }
            HStack(spacing: 8) {
                if acq.canRetry(j) { Button("Try again") { Task { await acq.retry(j) } }.buttonStyle(CapsuleButtonStyle(primary: true, small: true)) }
                if acq.canSkip(j) { Button("Use next source") { Task { await acq.skipSource(j) } }.buttonStyle(CapsuleButtonStyle(small: true)) }
                if j.phase != .working || acq.canSkip(j) {
                    Button("Dismiss") { acq.dismiss(j) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                }
            }
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .accessibilityElement(children: .contain)
    }
}
