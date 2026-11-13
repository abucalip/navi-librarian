import SwiftUI

/// The Radio page. Placeholder until S2-1 item 7 (mockup A2): it only proves the navigation and the model are wired,
/// by showing the title and how many stations the server listed. No station row, On Air panel or Edit Tags yet.
struct CupertinoStations: View {
    let state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            Text("Radio").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).padding(.top, CU.Space.xs).accessibilityAddTraits(.isHeader)
            Text(summary).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, CU.Space.xl)
    }

    private var summary: String {
        switch state.stations.phase {
        case .idle, .loading: "Reading the stations…"
        case .failed(let message, _): message
        case .loaded: state.stations.isEmpty ? "No stations yet. Add one in Navidrome and it appears here." : "\(state.stations.stations.count) stations."
        }
    }
}
