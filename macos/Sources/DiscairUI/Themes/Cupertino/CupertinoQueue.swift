import DiscairAudio
import SwiftUI

/// Queue: Up Next as a trailing inspector (glass, a control layer) over the Albums grid, with an Autoplay (radio)
/// switch, saved queue and history. Mockup: `R.cupertino.queue`.
struct CupertinoAlbumsGrid: View {
    let state: AppState
    /// The Recently Added tab: the newest albums instead of the alphabetical grid.
    var recent = false
    /// Text from the Library search field; only matching albums show.
    var query = ""
    /// False inside the Library page, which has its own heading.
    var showHeader = true
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if showHeader { Text(recent ? "Recently Added" : "Albums").font(CU.title(34)).padding(.top, 4).padding(.bottom, 16) }
                if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.textSecondary).padding(.bottom, 8) }
                if case .failed(let m) = state.library.phase { CUErrorLine(message: m).padding(.bottom, 8) }
                if state.neverPlayedOnly, !recent {
                    Button { state.neverPlayedOnly = false } label: { Label("Never played: \(state.library.neverPlayedAlbums.count.formatted()) albums", systemImage: "xmark.circle.fill") }
                        .buttonStyle(CapsuleButtonStyle(small: true)).padding(.bottom, 16)
                        .accessibilityHint("Shows every album again")
                }
                let source = recent ? state.library.recent : (state.neverPlayedOnly ? state.library.neverPlayedAlbums : state.library.searchableAlbums)
                let shown = LibrarySearch.albums(state.visible(source), query: query)
                if shown.isEmpty, !query.isEmpty { Text("No albums match.").foregroundStyle(CU.textSecondary) }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 16, alignment: .top)], alignment: .leading, spacing: 16) {
                    ForEach(shown) { a in AlbumTile(state: state, album: a) }
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }
}

struct CupertinoQueueInspector: View {
    let state: AppState
    static let width: CGFloat = 380
    private enum Tab { case queue, saved }
    @State private var tab = Tab.queue
    @State private var saving = false
    @State private var saveName = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                segmented
                Spacer()
                Text(tab == .saved ? "\(state.savedQueues.queues.count) saved" : live ? liveSummary : "8 songs · 52 min").foregroundStyle(CU.textSecondary).font(CU.Font.body.weighted(.regular)).lineLimit(1).minimumScaleFactor(0.8)
            }
            .padding(.bottom, 16)

            HStack(spacing: 8) {
                Image(systemName: "dot.radiowaves.left.and.right").font(CU.Icon.row())
                VStack(alignment: .leading, spacing: 0) {
                    Text("Autoplay").fontWeight(.semibold)
                    Text(state.radio.status ?? "Radio from this, similar artists in your library").font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary).lineLimit(2)
                }
                Spacer(minLength: 4)
                Button("Radio") { state.startRadio() }.buttonStyle(CapsuleButtonStyle())
                    .disabled(state.radio.busy || state.player.current == nil)
                    .accessibilityLabel("Start radio from this song")
                if state.radio.sonicAvailable {
                    Button("Sounds like") { state.startSonicRadio() }.buttonStyle(CapsuleButtonStyle())
                        .disabled(state.radio.busy || state.player.current == nil)
                        .accessibilityLabel("Add songs that sound like this song")
                }
                Toggle("Autoplay", isOn: Bindable(state.radio).autoplay).labelsHidden().toggleStyle(.switch).tint(CU.accent)
            }
            .padding(.horizontal, 8).padding(.top, 8).padding(.bottom, 16)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.text.opacity(0.08)).frame(height: 1) }
            .padding(.bottom, 8)

            // The playing album's Track images (idea 6): shown only when the album has some.
            TrackSheetCards(state: state).padding(.bottom, 8)
            ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 0) {
                    if tab == .saved { savedRows }
                    else if live { liveRows }
                    else {
                        ForEach(Array(Fixtures.queue.enumerated()), id: \.offset) { i, q in row(i, q) }
                    }
                }
            }
            .onChange(of: state.player.current?.id) { _, id in if id != nil { withAnimation { proxy.scrollTo("current-song", anchor: .center) } } }
            .onAppear { proxy.scrollTo("current-song", anchor: .center) }
            }
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                if saving {
                    TextField("Name", text: $saveName).textFieldStyle(.roundedBorder).onSubmit(commitSave).frame(maxWidth: 150)
                    Button("Save", action: commitSave).buttonStyle(CapsuleButtonStyle())
                    Button("Cancel") { saving = false }.buttonStyle(CapsuleButtonStyle())
                } else {
                    Button("Save queue") { saveName = ""; saving = true }.buttonStyle(CapsuleButtonStyle())
                        .disabled(state.player.queue.isEmpty)
                }
                Button("Clear") { if live { state.player.clearUpNext() } }.buttonStyle(CapsuleButtonStyle())
                    .disabled(live && state.player.queue.upNext.isEmpty)
            }
            .padding(.top, 8)
        }
        .font(CU.Font.body.weighted(.regular))
        .padding(.top, 66).padding([.horizontal, .bottom], 16)
        .frame(width: Self.width).frame(maxHeight: .infinity)
        .glassEffect(CU.glass, in: Rectangle())
        .overlay(alignment: .leading) { Rectangle().fill(CU.text.opacity(0.08)).frame(width: 1) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Queue")
    }

    private func commitSave() { state.saveQueue(named: saveName); saving = false; tab = .saved }

    @ViewBuilder private var savedRows: some View {
        let list = state.savedQueues.queues
        if list.isEmpty { Text("No saved queues yet. Save the queue to bring it back later.").foregroundStyle(CU.textSecondary).padding(8) }
        ForEach(list) { q in
            HStack(spacing: 8) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(q.name).fontWeight(.semibold).lineLimit(1)
                    Text("\(q.items.count) songs · \(q.minutes) min").font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary)
                }
                Spacer(minLength: 4)
                Button("Play") { state.playSavedQueue(q.id) }.buttonStyle(CapsuleButtonStyle())
                Menu {
                    Button("Add to queue") { state.addSavedQueue(q.id) }
                    Divider()
                    Button("Delete", role: .destructive) { state.savedQueues.remove(q.id) }
                } label: { Image(systemName: "ellipsis.circle") }
                .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
                .accessibilityLabel("Actions for \(q.name)")
            }
            .padding(.horizontal, 8).padding(.vertical, 8)
            .accessibilityElement(children: .contain)
        }
    }

    private var live: Bool { state.library.isLive || state.player.current != nil }

    private var liveSummary: String {
        let p = state.player
        let up = p.queue.upNext
        let minutes = Int(up.reduce(0) { $0 + $1.duration } / 60)
        return up.isEmpty ? "Nothing queued" : "\(up.count) to come · \(minutes) min"
    }

    @ViewBuilder private var liveRows: some View {
        let p = state.player
        // Played songs stay in the list above the current one, dimmed; choosing one plays it again.
        let played = p.queue.played
        ForEach(Array(played.enumerated()), id: \.element.id) { i, item in
            Button { p.jump(toPlayed: i) } label: {
                songRow(item, time: PlayerModel.clock(item.duration), playing: false).opacity(0.5)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Played: \(item.title), \(item.artist). Play again")
        }
        if let c = p.current { songRow(c, time: PlayerModel.clock(c.duration), playing: true).id("current-song") }
        else { Text("Nothing playing. Play a song and what follows shows here.").foregroundStyle(CU.textSecondary).padding(8) }
        let up = p.queue.upNext
        ForEach(Array(up.enumerated()), id: \.element.id) { i, item in
            ReorderRow(index: i, count: up.count, move: { p.moveUpNext(from: $0, to: $1) }) { grab in
            songRow(item, time: PlayerModel.clock(item.duration), playing: false, grab: grab, onDouble: { p.jump(toUpNext: i) }) {
                Menu {
                    Button("Play now") { p.jump(toUpNext: i) }
                    Button("Move up") { p.moveUpNext(from: i, to: i - 1) }.disabled(i == 0)
                    Button("Move down") { p.moveUpNext(from: i, to: i + 1) }.disabled(i == up.count - 1)
                    if state.radio.sonicAvailable { Button("Sonic path from playing song") { state.showSonicPath(to: item) } }
                    Divider()
                    Button("Remove from queue", role: .destructive) { p.removeUpNext(at: i) }
                } label: { Image(systemName: "ellipsis.circle") }
                .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
                .accessibilityLabel("Actions for \(item.title)")
            }
            }
        }
    }

    private func songRow<T: View>(_ q: QueueItem, time: String, playing: Bool, grab: ReorderGrab? = nil, onDouble: (() -> Void)? = nil, @ViewBuilder trailing: () -> T = { EmptyView() }) -> some View {
        HStack(spacing: 8) {
            HStack(spacing: 8) {
            CoverView(album: AlbumItem(id: -1, title: q.album, artist: q.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: q.coverArt))
                .frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous)).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 0) {
                Text(q.title).fontWeight(.semibold).lineLimit(1)
                Text(q.artist).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary).lineLimit(1)
            }
            Spacer(minLength: 4)
            }
            .modifier(grab ?? ReorderGrab())
            HStack(spacing: 4) {
                if playing { PlayingBars(active: state.player.isPlaying) }
                Text(time).monospacedDigit()
            }
            .font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary)
            trailing()
        }
        .padding(.horizontal, 8).padding(.vertical, 8)
        .background(playing ? CU.accent.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .contentShape(Rectangle())
        .onTapGesture(count: 2) { onDouble?() }
        .accessibilityElement(children: .combine)
    }

    private var segmented: some View {
        HStack(spacing: 0) {
            seg("Queue", on: tab == .queue) { tab = .queue }
            seg("Saved", on: tab == .saved) { tab = .saved }
        }
        .padding(4).background(CU.textSecondary.opacity(0.14), in: Capsule())
    }

    private func seg(_ t: String, on: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).font(CU.Font.body.weighted(on ? .semibold : .medium)).lineLimit(1).fixedSize().padding(.horizontal, 16).padding(.vertical, 4)
                .background(on ? CU.onAccent : .clear, in: Capsule())
                .shadow(color: CU.shadowInk.opacity(on ? 0.15 : 0), radius: 1.5, y: 1)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    private func row(_ i: Int, _ q: (title: String, album: Int, time: String)) -> some View {
        let a = Fixtures.albums[q.album]
        return HStack(spacing: 8) {
            CoverView(album: a).frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
            VStack(alignment: .leading, spacing: 0) {
                Text(q.title).fontWeight(.semibold).lineLimit(1)
                Text(a.artist).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary).lineLimit(1)
            }
            Spacer(minLength: 4)
            HStack(spacing: 4) {
                if i == 0 { Image(systemName: "waveform").accessibilityLabel("Playing") }
                Text(q.time).monospacedDigit()
            }
            .font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary)
        }
        .padding(.horizontal, 8).padding(.vertical, 8)
        .background(i == 0 ? CU.accent.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .accessibilityElement(children: .combine)
    }
}
