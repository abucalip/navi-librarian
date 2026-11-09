import SwiftUI

/// A search field for choosing an artist from the library, with the matches listed under it. Connections and Timeline start
/// from it instead of from whichever artist was opened last.
struct ArtistPickerField: View {
    let state: AppState
    let style: GraphStyle
    var prompt = "Search an artist"
    let onPick: (ArtistItem) -> Void
    @State private var text = ""
    @FocusState private var focused: Bool

    private var matches: [ArtistItem] {
        guard !LibrarySearch.fold(text).isEmpty else { return [] }
        return Array(LibrarySearch.artists(state.library.artists, query: text).prefix(6))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(style.muted).accessibilityHidden(true)
                TextField(prompt, text: $text).textFieldStyle(.plain).focused($focused)
                    .onSubmit { if let first = matches.first { pick(first) } }
                    .accessibilityLabel(prompt)
                if !text.isEmpty {
                    Button { text = "" } label: { Image(systemName: "xmark.circle.fill").foregroundStyle(style.muted) }
                        .buttonStyle(.plain).accessibilityLabel("Clear")
                }
            }
            .padding(.horizontal, 12).frame(width: 300, height: 34)
            .background(style.card, in: Capsule())
            .overlay(Capsule().stroke(style.ink.opacity(0.12), lineWidth: 1))
            if !matches.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(matches) { a in
                        Button { pick(a) } label: {
                            HStack(spacing: 10) {
                                ArtistPhoto(name: a.name, size: 28)
                                Text(a.name).lineLimit(1)
                                Spacer()
                                Text(a.albumCount == 1 ? "1 album" : "\(a.albumCount) albums").font(.system(size: 11)).foregroundStyle(style.muted)
                            }
                            .padding(.horizontal, 10).padding(.vertical, 5).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .frame(width: 300).padding(.vertical, 4)
                .background(style.card, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(style.ink.opacity(0.12), lineWidth: 1))
            }
        }
    }

    private func pick(_ a: ArtistItem) { text = ""; focused = false; onPick(a) }
}
