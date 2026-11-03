import SwiftUI

/// Library: A-Z index with a letter margin and dotted leaders, three columns. Mockup: `R.zine.library`.
struct ZineLibrary: View {
    let state: AppState
    private var letters: [String] {
        Array("ABCDEFGHIJKLMNOPQRSTUVWXYZ").map(String.init) + (state.library.artists.contains { $0.letter == "#" } ? ["#"] : [])
    }

    var body: some View {
        HStack(alignment: .top, spacing: 18) {
            VStack(spacing: 0) {
                ForEach(letters, id: \.self) { l in
                    let on = l == state.selectedLetter
                    Button { state.selectedLetter = l } label: {
                        Text(l).font(Z.an(18)).frame(maxWidth: .infinity).padding(.vertical, 1.5)
                            .foregroundStyle(on ? Z.yellow : Z.ink).background(on ? Z.ink : .clear)
                    }
                    .buttonStyle(.plain).accessibilityLabel("Letter \(l)").accessibilityAddTraits(on ? .isSelected : [])
                }
            }
            .frame(width: 44).padding(.trailing, 8)
            .overlay(alignment: .trailing) { Rectangle().fill(Z.ink).frame(width: 3) }

            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .bottom, spacing: 16) {
                    Text(state.selectedLetter).font(Z.an(72)).accessibilityAddTraits(.isHeader)
                    Mono(state.library.isLive ? "Artist index · \(shown.count) artists · \(state.library.totalAlbumsText.dropFirst(8))" : "Artist index · 38 artists · Showing 24").padding(.bottom, 8)
                    Spacer()
                    HStack(spacing: 4) { Mono("View:"); Mono("Index", bold: true); Mono("· Table · Grid") }.padding(.bottom, 8)
                }
                .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
                columns
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
    }

    /// Artists under the chosen letter (the whole index in sample mode shows the T page).
    private var shown: [ArtistItem] {
        state.library.artists.filter { $0.letter == state.selectedLetter }
    }

    /// Three balanced columns, filled top to bottom like CSS columns.
    private var columns: some View {
        let all = shown
        let per = max(1, Int((Double(all.count) / 3).rounded(.up)))
        let cols = stride(from: 0, to: all.count, by: per).map { Array(all[$0..<min($0 + per, all.count)]) }
        return HStack(alignment: .top, spacing: 12) {
            ForEach(Array(cols.enumerated()), id: \.offset) { ci, col in
                VStack(spacing: 0) {
                    ForEach(col) { artist in
                        Button { state.open(artist: artist) } label: {
                            DotRow {
                                Text(artist.name).font(Z.an(15)).textCase(.uppercase).lineLimit(1)
                            } right: { Mono("\(artist.albumCount)") }
                            .padding(.vertical, 3).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(artist.name), \(artist.albumCount) albums")
                    }
                }
                .frame(maxWidth: .infinity, alignment: .top)
                if ci < cols.count - 1 { Rectangle().fill(Z.ink).frame(width: 2) }
            }
        }
        .fixedSize(horizontal: false, vertical: true)
    }
}
