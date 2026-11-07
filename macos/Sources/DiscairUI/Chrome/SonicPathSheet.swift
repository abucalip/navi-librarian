import DiscairAudio
import SwiftUI

/// The sonic path from the playing song to a chosen song: the server's ordered steps, with Add to Queue and Play Now.
/// Plain system styling so it reads the same under every theme.
struct SonicPathSheet: View {
    let state: AppState
    let model: SonicPathModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Sonic Path").font(.title2.bold()).accessibilityAddTraits(.isHeader)
            Text("\(model.start.title) to \(model.target.title)").foregroundStyle(.secondary).lineLimit(1)
            switch model.phase {
            case .loading:
                ProgressView("Finding the path…").frame(maxWidth: .infinity, minHeight: 200)
            case .empty:
                Text("No sonic path between these songs yet.").frame(maxWidth: .infinity, minHeight: 200)
            case .failed(let message):
                Text(message).foregroundStyle(.red).frame(maxWidth: .infinity, minHeight: 200)
            case .ready(let steps):
                List(Array(steps.enumerated()), id: \.offset) { i, s in
                    HStack(spacing: 10) {
                        Text("\(i + 1)").monospacedDigit().foregroundStyle(.secondary).frame(width: 24, alignment: .trailing)
                        VStack(alignment: .leading) {
                            Text(s.title).lineLimit(1)
                            Text(s.artist).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                        }
                    }
                    .accessibilityElement(children: .combine)
                }
                .frame(minHeight: 260)
            }
            HStack {
                Button("Close") { state.sonicPath = nil }.keyboardShortcut(.cancelAction)
                Spacer()
                if case .ready(let steps) = model.phase {
                    Button("Add to Queue") { state.useSonicPath(steps, playNow: false) }
                    Button("Play Now") { state.useSonicPath(steps, playNow: true) }.keyboardShortcut(.defaultAction)
                }
            }
        }
        .padding(20).frame(width: 440)
    }
}
