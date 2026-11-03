import SwiftUI

/// Library: A-Z index with a letter margin and dotted leaders, three columns. Mockup: `R.zine.library`.
struct ZineLibrary: View {
    let state: AppState
    private let letters = Array("ABCDEFGHIJKLMNOPQRSTUVWXYZ").map(String.init)

    var body: some View {
        HStack(alignment: .top, spacing: 18) {
            VStack(spacing: 0) {
                ForEach(letters, id: \.self) { l in
                    let on = l == "T"
                    Button { } label: {
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
                    Text("T").font(Z.an(72)).accessibilityAddTraits(.isHeader)
                    Mono("Artist index · 38 artists · Showing 24").padding(.bottom, 8)
                    Spacer()
                    HStack(spacing: 4) { Mono("View:"); Mono("Index", bold: true); Mono("· Table · Grid") }.padding(.bottom, 8)
                }
                .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
                columns
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
    }

    /// Three balanced columns, filled top to bottom like CSS columns.
    private var columns: some View {
        let all = ZineFixtures.artistIndex
        let per = Int((Double(all.count) / 3).rounded(.up))
        let cols = stride(from: 0, to: all.count, by: per).map { Array(all[$0..<min($0 + per, all.count)]) }
        return HStack(alignment: .top, spacing: 12) {
            ForEach(Array(cols.enumerated()), id: \.offset) { ci, col in
                VStack(spacing: 0) {
                    ForEach(col, id: \.0) { name, count in
                        Button { if name == "Talk Talk" { state.screen = .artist } } label: {
                            DotRow {
                                Text(name).font(Z.an(15)).textCase(.uppercase).lineLimit(1)
                            } right: { Mono("\(count)") }
                            .padding(.vertical, 3).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(name), \(count) albums")
                    }
                }
                .frame(maxWidth: .infinity, alignment: .top)
                if ci < cols.count - 1 { Rectangle().fill(Z.ink).frame(width: 2) }
            }
        }
        .fixedSize(horizontal: false, vertical: true)
    }
}
