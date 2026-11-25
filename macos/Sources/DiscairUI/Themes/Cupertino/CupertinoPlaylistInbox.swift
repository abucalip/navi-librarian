import DiscairLibrarian
import SwiftUI

struct CupertinoInboxShelf: View {
    let state: AppState
    private var model: PlaylistInboxModel { state.playlistInbox }
    private var connected: Bool {
        model.isConnected && (state.session == nil || state.session?.librarian != nil)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Playlist Inbox").font(CU.title(22)).accessibilityAddTraits(.isHeader)
            if connected {
                shelf
            } else if state.session?.status == .connecting {
                InboxLoading(label: "Connecting to Librarian…")
            } else {
                Text("Connect to Librarian to view saved playlists.").foregroundStyle(CU.textSecondary)
            }
        }
        .task(id: model.connectionRevision) { await model.loadShelf() }
    }

    @ViewBuilder private var shelf: some View {
        switch model.shelf {
        case .idle, .loading:
            InboxLoading(label: "Loading playlists…")
        case .failed(let message):
            InboxFailure(message: message) { await model.loadShelf() }
        case .loaded(let inbox):
            if inbox.items.isEmpty {
                Text(inbox.state == "unconfigured" ? "Connect ListenBrainz to receive playlists." : "No playlists in your inbox yet.")
                    .foregroundStyle(CU.textSecondary)
            } else {
                ScrollView(.horizontal) {
                    LazyHStack(alignment: .top, spacing: 12) {
                        ForEach(inbox.items) { edition in
                            Button {
                                model.open(edition.id)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(edition.displayTitle).font(CU.Font.title3.weighted(.semibold)).lineLimit(2)
                                    InboxEditionMetadata(edition: edition)
                                }
                                .frame(width: 224, alignment: .leading)
                                .padding(12)
                                .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 12))
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .scrollIndicators(.hidden)
            }
        }
    }
}

struct CupertinoInboxEdition: View {
    let state: AppState
    let id: Int64
    private var model: PlaylistInboxModel { state.playlistInbox }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 12) {
                Button {
                    model.close()
                } label: {
                    Label("Playlist Inbox", systemImage: "chevron.left")
                }
                .buttonStyle(CapsuleButtonStyle(small: true))
                .accessibilityLabel("Back to Playlist Inbox")

                switch model.detail {
                case .idle, .loading:
                    InboxLoading(label: "Loading playlist…")
                case .failed(let message):
                    InboxFailure(message: message) { await model.loadDetail(id: id) }
                case .loaded(let detail):
                    detailHeader(detail)
                    if detail.tracks.isEmpty {
                        Text("This playlist has no tracks.").foregroundStyle(CU.textSecondary)
                    }
                    ForEach(detail.tracks) { track in
                        InboxTrackRow(track: track)
                    }
                }
            }
            .padding(.horizontal, CU.Space.xl)
            .padding(.vertical, 4)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task(id: id) { await model.loadDetail(id: id) }
    }

    private func detailHeader(_ detail: PlaylistInboxDetail) -> some View {
        let songs = PlaylistInboxModel.playbackItems(for: detail)
        return VStack(alignment: .leading, spacing: 8) {
            Text(detail.edition.displayTitle).font(CU.title(34)).accessibilityAddTraits(.isHeader)
            InboxEditionMetadata(edition: detail.edition)
            Button("Play owned tracks") { state.player.playInOrder(songs) }
                .buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                .disabled(songs.isEmpty)
        }
    }
}

private struct InboxEditionMetadata: View {
    let edition: PlaylistInboxEdition

    private var source: String {
        switch edition.sourceKind {
        case "hosted": "ListenBrainz · Created for Me"
        case "cf": "ListenBrainz · Recommendations"
        case "local": "Discair"
        default: "Playlist"
        }
    }

    private var generationDate: Date? {
        guard let value = edition.generatedAt else { return nil }
        return (try? Date.ISO8601FormatStyle().parse(value))
            ?? (try? Date.ISO8601FormatStyle(includingFractionalSeconds: true).parse(value))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(source)
            if let generationDate {
                Text(generationDate, format: .dateTime.year().month(.abbreviated).day())
            } else {
                Text("Generation date unavailable")
            }
            if let owned = edition.ownedCount {
                Text("\(owned) of \(edition.totalCount) owned")
            } else {
                Text("Ownership unavailable · \(edition.totalCount) tracks")
            }
        }
        .font(CU.Font.callout.weighted(.regular))
        .foregroundStyle(CU.textSecondary)
    }
}

private extension PlaylistInboxEdition {
    var displayTitle: String {
        guard let title, !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return "Untitled playlist" }
        return title
    }
}

private struct InboxTrackRow: View {
    let track: PlaylistInboxTrack

    private var ownership: String {
        switch track.matchState {
        case "owned": "Owned"
        case "missing": "Missing"
        case "ambiguous": "Ambiguous match"
        default: "Ownership unavailable"
        }
    }

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text("\(track.position + 1)").monospacedDigit().foregroundStyle(CU.textSecondary)
            VStack(alignment: .leading, spacing: 2) {
                Text(track.displayTitle).fontWeight(.medium)
                let metadata = [track.artist, track.album].compactMap { $0 }.filter { !$0.isEmpty }
                if !metadata.isEmpty {
                    Text(metadata.joined(separator: " · ")).foregroundStyle(CU.textSecondary)
                }
            }
            Spacer(minLength: 8)
            Text(ownership).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary)
        }
        .padding(10)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
    }
}

private struct InboxLoading: View {
    let label: String

    var body: some View {
        HStack(spacing: 8) {
            ProgressView().controlSize(.small)
            Text(label)
        }
        .foregroundStyle(CU.textSecondary)
    }
}

private struct InboxFailure: View {
    let message: String
    let retry: () async -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(message).foregroundStyle(CU.textSecondary)
            Button("Try again") { Task { await retry() } }
                .buttonStyle(CapsuleButtonStyle(small: true))
        }
    }
}
