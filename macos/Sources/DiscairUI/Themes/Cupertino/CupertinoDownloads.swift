import DiscairLibrarian
import SwiftUI

/// Downloads: the Librarian's job list. No mockup exists; it follows Cupertino's rules (bold sans title, opaque
/// white content, grouped cards, red-pink accent). State is icon plus words, never colour alone. Dismiss is the only
/// destructive action and always asks first because the server deletes the job's files.
struct CupertinoDownloads: View {
    let state: AppState
    @State private var confirming: Acquisition?
    @State private var confirmingAll = false

    private var acq: AcquisitionModel { state.acquisition }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .firstTextBaseline) {
                    Text("Downloads").font(CU.title(34)).accessibilityAddTraits(.isHeader)
                    Spacer()
                    if acq.importedCount > 0 {
                        Button("Clear \(acq.importedCount) imported") { confirmingAll = true }
                            .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                    }
                }
                .padding(.top, 4)
                if acq.jobs.isEmpty {
                    Text(state.session == nil || state.library.isLive ? "Nothing is downloading. Albums you Get appear here." : "Downloads are available in the running app.")
                        .foregroundStyle(CU.muted).padding(.top, 8)
                }
                ForEach(acq.sortedJobs) { job in row(job) }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .confirmationDialog(confirming.map { "Dismiss \($0.title)?" } ?? "", isPresented: Binding(get: { confirming != nil }, set: { if !$0 { confirming = nil } }), titleVisibility: .visible) {
            Button("Dismiss and delete files", role: .destructive) { if let j = confirming { Task { await acq.dismiss(j) } } }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("The Librarian deletes the files it downloaded for this job. It refuses if that is not safe.")
        }
        .confirmationDialog("Clear imported downloads?", isPresented: $confirmingAll, titleVisibility: .visible) {
            Button("Clear \(acq.importedCount) imported", role: .destructive) { Task { await acq.dismissImported() } }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("The Librarian removes these jobs and deletes their download files. The music already in your library stays.")
        }
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
                    Button("Dismiss") { confirming = j }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                }
            }
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        .accessibilityElement(children: .contain)
    }
}
