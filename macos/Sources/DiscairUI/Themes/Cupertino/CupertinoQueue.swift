import SwiftUI

/// Queue: Up Next as a trailing inspector (glass, a control layer) over the Albums grid, with an Autoplay (radio)
/// switch, saved queue and history. Mockup: `R.cupertino.queue`.
struct CupertinoAlbumsGrid: View {
    let state: AppState
    /// True when the Up Next inspector is open and the grid must stay clear of it.
    var inspector = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Albums").font(CU.title(34)).padding(.top, 4).padding(.bottom, 14)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 18, alignment: .top)], alignment: .leading, spacing: 18) {
                    ForEach(Fixtures.albums([0, 1, 2, 3, 4, 5, 6, 13, 12, 11])) { a in
                        Button { state.selectedAlbum = a; state.screen = .album } label: {
                        VStack(alignment: .leading, spacing: 0) {
                            CoverView(album: a).frame(width: 128).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                .shadow(color: .black.opacity(0.2), radius: 7, y: 4).padding(.bottom, 9)
                            Text(a.title).fontWeight(.semibold).lineLimit(1)
                            Text(a.artist).foregroundStyle(CU.muted).lineLimit(1)
                        }
                        .font(.system(size: 13)).frame(width: 128, alignment: .leading)
                        .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(a.title), \(a.artist)")
                    }
                }
            }
            .padding(.leading, 28).padding(.trailing, 28 + (inspector ? CupertinoQueueInspector.width : 0)).padding(.bottom, 28)   // keeps content out from under the inspector
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }
}

struct CupertinoQueueInspector: View {
    let state: AppState
    static let width: CGFloat = 380
    @State private var showHistory = false
    @State private var autoplay = true

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                segmented
                Spacer()
                Text("8 songs · 52 min").foregroundStyle(CU.muted).font(.system(size: 13))
            }
            .padding(.bottom, 12)

            HStack(spacing: 10) {
                Image(systemName: "dot.radiowaves.left.and.right").font(.system(size: 16))
                VStack(alignment: .leading, spacing: 1) {
                    Text("Autoplay").fontWeight(.semibold)
                    Text("Radio from this, similar artists by Librarian").font(.system(size: 12)).foregroundStyle(CU.muted)
                }
                Spacer(minLength: 4)
                Toggle("Autoplay", isOn: $autoplay).labelsHidden().toggleStyle(.switch).tint(.green)
            }
            .padding(.horizontal, 8).padding(.top, 8).padding(.bottom, 12)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.ink.opacity(0.08)).frame(height: 1) }
            .padding(.bottom, 8)

            ScrollView {
                VStack(spacing: 0) {
                    if showHistory {
                        Text("Earlier today: Glory Box · Roygbiv · Cloudbusting").foregroundStyle(CU.muted).padding(8)
                    } else {
                        ForEach(Array(Fixtures.queue.enumerated()), id: \.offset) { i, q in row(i, q) }
                    }
                }
            }
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                Button("Save queue") { }.buttonStyle(CapsuleButtonStyle())
                Button("Clear") { }.buttonStyle(CapsuleButtonStyle())
            }
            .padding(.top, 10)
        }
        .font(.system(size: 13))
        .padding(.top, 66).padding([.horizontal, .bottom], 18)
        .frame(width: Self.width).frame(maxHeight: .infinity)
        .glassEffect(CU.glass, in: Rectangle())
        .overlay(alignment: .leading) { Rectangle().fill(CU.ink.opacity(0.08)).frame(width: 1) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Up Next")
    }

    private var segmented: some View {
        HStack(spacing: 0) {
            seg("Up Next", on: !showHistory) { showHistory = false }
            seg("History", on: showHistory) { showHistory = true }
        }
        .padding(3).background(Color(red: 0.47, green: 0.47, blue: 0.5).opacity(0.14), in: Capsule())
    }

    private func seg(_ t: String, on: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).font(.system(size: 13, weight: on ? .semibold : .medium)).padding(.horizontal, 14).padding(.vertical, 3)
                .background(on ? Color.white : .clear, in: Capsule())
                .shadow(color: .black.opacity(on ? 0.15 : 0), radius: 1.5, y: 1)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    private func row(_ i: Int, _ q: (title: String, album: Int, time: String)) -> some View {
        let a = Fixtures.albums[q.album]
        return HStack(spacing: 11) {
            CoverView(album: a).frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            VStack(alignment: .leading, spacing: 0) {
                Text(q.title).fontWeight(.semibold).lineLimit(1)
                Text(a.artist).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
            }
            Spacer(minLength: 4)
            HStack(spacing: 4) {
                if i == 0 { Image(systemName: "waveform").accessibilityLabel("Playing") }
                Text(q.time).monospacedDigit()
            }
            .font(.system(size: 12)).foregroundStyle(CU.muted)
        }
        .padding(.horizontal, 8).padding(.vertical, 6)
        .background(i == 0 ? CU.accent.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
        .accessibilityElement(children: .combine)
    }
}
