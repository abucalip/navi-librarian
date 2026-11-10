import DiscairLibrarian
import SwiftUI

/// Downloads: "The Pipeline". No mockup exists; it uses Zine's parts (headline, 3 pt bordered boxes, mono labels,
/// hard-shadow buttons). Status is a word in a badge, never colour alone. Dismiss only hides the card.
struct ZineDownloads: View {
    let state: AppState

    private var acq: AcquisitionModel { state.acquisition }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Downloads").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("The Pipeline · \(acq.activeCount) moving").padding(.bottom, 8)
                Spacer()
                if acq.importedCount > 0 {
                    Button("Clear \(acq.importedCount) imported") { acq.dismissImported() }
                        .buttonStyle(ZineButtonStyle(small: true)).padding(.bottom, 8)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }

            if acq.visibleJobs.isEmpty {
                Mono(state.session == nil || state.library.isLive ? "Nothing is downloading. Albums you Get appear here." : "Downloads are available in the running app.")
            }
            ForEach(acq.sortedJobs) { job in row(job) }
        }
    }

    private func row(_ j: Acquisition) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text(j.title).font(Z.an(20)).textCase(.uppercase).lineLimit(1)
                Spacer()
                ZineBadge(acq.statusLine(j))
            }
            Mono(j.isSong ? "\(j.artist) · Song on \(j.details?.albumName ?? j.album)" : j.artist, size: 11)
            if let f = acq.fraction(j) {
                GeometryReader { g in
                    ZStack(alignment: .leading) {
                        Rectangle().fill(Z.white)
                        Rectangle().fill(Z.yellow).frame(width: g.size.width * f)
                    }
                }
                .frame(height: 14).zBorder(2)
                .accessibilityElement().accessibilityLabel("Download progress").accessibilityValue("\(Int(f * 100)) percent")
            }
            let line = acq.progressLine(j)
            if !line.isEmpty { Mono(line, size: 11) }
            if let rgid = j.details?.releaseGroupMBID { EditionCoverStrip(rgid: rgid) }
            if j.phase == .failed, let m = j.details?.message { Text(m).font(Z.serif(13)) }
            HStack(spacing: 8) {
                if acq.canRetry(j) { Button("Try again") { Task { await acq.retry(j) } }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true)) }
                if acq.canSkip(j) { Button("Use next source") { Task { await acq.skipSource(j) } }.buttonStyle(ZineButtonStyle(small: true)) }
                if j.phase != .working || acq.canSkip(j) {
                    Button("Dismiss") { acq.dismiss(j) }.buttonStyle(ZineButtonStyle(small: true))
                }
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
        .background(j.phase == .failed ? Z.yellow.opacity(0.35) : Z.white).zBorder(3)
        .accessibilityElement(children: .contain)
    }
}
