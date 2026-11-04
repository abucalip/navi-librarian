import DiscairAudio
import SwiftUI

/// Queue: a printed running order with dotted leaders; Radio from this is a classified ad. Mockup: `R.zine.queue`.
struct ZineQueue: View {
    let state: AppState
    @State private var saving = false
    @State private var saveName = ""
    private var live: Bool { state.library.isLive || state.player.current != nil }

    private var liveSummary: String {
        let up = state.player.queue.upNext
        return up.isEmpty ? "Nothing queued" : "\(up.count) up next · \(Int(up.reduce(0) { $0 + $1.duration } / 60)) min"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Running Order").font(Z.an(78)).textCase(.uppercase).tracking(0.8).lineLimit(1).accessibilityAddTraits(.isHeader)
                Mono(live ? liveSummary : "8 songs · 52 min").padding(.bottom, 8)
                Spacer()
                HStack(spacing: 10) {
                    if live { saveControls }
                    Button("Clear") { if live { state.player.clearUpNext() } }.buttonStyle(ZineButtonStyle())
                        .disabled(live && state.player.queue.upNext.isEmpty)
                }
                .padding(.bottom, 8)
            }
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            HStack(alignment: .top, spacing: 26) {
                VStack(spacing: 0) {
                    if live { liveOrder }
                    else { ForEach(Array(ZineFixtures.runningOrder.enumerated()), id: \.offset) { i, row in
                        let on = i == ZineFixtures.playingIndex
                        let a = Fixtures.albums[row.album]
                        ZineListRow(highlight: on) {
                            HStack(spacing: 10) {
                                Text("\(i + 1)").font(Z.an(22)).lineLimit(1).fixedSize().frame(width: 36, alignment: .leading)
                                ZineCover(album: a, width: 44, border: 2, shadow: 3)
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(row.title).font(Z.an(16)).textCase(.uppercase).lineLimit(1)
                                    Mono(a.artist)
                                }
                                Spacer(minLength: 4)
                                Mono((on ? "▶ playing · " : "") + row.time)
                                Mono("≡").accessibilityHidden(true)
                            }
                        }
                        .accessibilityElement(children: .combine)
                        .accessibilityLabel("\(i + 1). \(row.title), \(a.artist), \(row.time)\(on ? ", playing" : "")")
                    } }
                }
                .frame(maxWidth: .infinity)
                .layoutPriority(1.5)
                VStack(alignment: .leading, spacing: 14) {
                    if live { liveSide } else {
                    VStack(alignment: .leading, spacing: 8) {
                        ZineH2("Classified · Radio", size: 20)
                        Text("Wanted: more like this. Keeps playing similar artists picked by Librarian.").font(Z.serif(14))
                        Button("Start radio from this") { }.buttonStyle(ZineButtonStyle())
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Z.yellow).zBorder(3)
                    VStack(alignment: .leading, spacing: 0) {
                        ZineH2("Saved queues", size: 20)
                        DotRow { Mono("Late night") } right: { Mono("24") }
                        DotRow { Mono("Sunday morning") } right: { Mono("17") }.padding(.top, 2)
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Z.white).zBorder(3)
                    VStack(alignment: .leading, spacing: 0) {
                        ZineH2("Earlier today", size: 20)
                        Mono("Glory Box · Roygbiv · Cloudbusting")
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
                    .zBorder(3, dashed: true)
                    }
                }
                .frame(maxWidth: live ? 280 : .infinity)
            }
        }
    }

    @ViewBuilder private var liveOrder: some View {
        let p = state.player
        if let c = p.current { runningRow(c, number: 1, playing: true, index: nil) }
        else { Mono("Nothing playing. Play a song and the running order shows here.") }
        let up = p.queue.upNext
        ForEach(Array(up.enumerated()), id: \.element.id) { i, item in runningRow(item, number: i + 2, playing: false, index: i) }
    }

    private func runningRow(_ q: QueueItem, number: Int, playing: Bool, index: Int?) -> some View {
        let a = AlbumItem(id: -1, title: q.album, artist: q.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: q.coverArt)
        let p = state.player
        let count = p.queue.upNext.count
        return ZineListRow(highlight: playing) {
            HStack(spacing: 10) {
                HStack(spacing: 10) {
                Text("\(number)").font(Z.an(22)).lineLimit(1).fixedSize().frame(width: 36, alignment: .leading)
                ZineCover(album: a, width: 44, border: 2, shadow: 3)
                VStack(alignment: .leading, spacing: 1) {
                    Text(q.title).font(Z.an(16)).textCase(.uppercase).lineLimit(1)
                    Mono(q.artist)
                }
                Spacer(minLength: 4)
                }
                .modifier(RowDragSource(id: index == nil ? nil : q.id.uuidString))
                Mono((playing ? "▶ playing · " : "") + PlayerModel.clock(q.duration))
                if let i = index {
                    Button("Play") { p.jump(toUpNext: i) }.buttonStyle(ZineButtonStyle(small: true))
                    Button("Up") { p.moveUpNext(from: i, to: i - 1) }.buttonStyle(ZineButtonStyle(small: true)).disabled(i == 0)
                        .accessibilityLabel("Move \(q.title) up")
                    Button("Down") { p.moveUpNext(from: i, to: i + 1) }.buttonStyle(ZineButtonStyle(small: true)).disabled(i == count - 1)
                        .accessibilityLabel("Move \(q.title) down")
                    Button("Remove") { p.removeUpNext(at: i) }.buttonStyle(ZineButtonStyle(small: true))
                        .accessibilityLabel("Remove \(q.title)")
                }
            }
        }
        .accessibilityElement(children: .contain)
        .modifier(QueueReorder(enabled: index != nil) { ids in
            guard let i = index, let from = p.queue.upNext.firstIndex(where: { $0.id.uuidString == ids.first }) else { return false }
            p.moveUpNext(from: from, to: i)
            return true
        })
    }

    @ViewBuilder private var saveControls: some View {
        if saving {
            TextField("Name", text: $saveName).textFieldStyle(.plain).font(Z.mono(12)).padding(6).frame(width: 150).zBorder(2)
                .onSubmit(commitSave).accessibilityLabel("Name for the saved queue")
            Button("Save", action: commitSave).buttonStyle(ZineButtonStyle())
            Button("Cancel") { saving = false }.buttonStyle(ZineButtonStyle())
        } else {
            Button("Save queue") { saveName = ""; saving = true }.buttonStyle(ZineButtonStyle()).disabled(state.player.queue.isEmpty)
        }
    }

    private func commitSave() { state.saveQueue(named: saveName); saving = false }

    @ViewBuilder private var liveSide: some View {
        let p = state.player
        VStack(alignment: .leading, spacing: 14) {
        VStack(alignment: .leading, spacing: 8) {
            ZineH2("Classified · Radio", size: 20)
            Text(state.radio.status ?? "Wanted: more like this. Adds songs by similar artists you own.").font(Z.serif(14))
            HStack(spacing: 10) {
                Button("Start radio from this") { state.startRadio() }.buttonStyle(ZineButtonStyle())
                    .disabled(state.radio.busy || p.current == nil)
                Toggle("Autoplay", isOn: Bindable(state.radio).autoplay).toggleStyle(.checkbox).font(Z.mono(12))
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
        .background(Z.yellow).zBorder(3)
        VStack(alignment: .leading, spacing: 4) {
            ZineH2("Saved queues", size: 20)
            if state.savedQueues.queues.isEmpty { Mono("None yet. Save the running order to keep it") }
            ForEach(state.savedQueues.queues) { q in
                VStack(alignment: .leading, spacing: 4) {
                    DotRow { Mono(q.name) } right: { Mono("\(q.items.count)") }
                    HStack(spacing: 8) {
                        Button("Play") { state.playSavedQueue(q.id) }.buttonStyle(ZineButtonStyle(small: true))
                        Button("Add") { state.addSavedQueue(q.id) }.buttonStyle(ZineButtonStyle(small: true))
                            .accessibilityLabel("Add \(q.name) to queue")
                        Button("Delete") { state.savedQueues.remove(q.id) }.buttonStyle(ZineButtonStyle(small: true))
                            .accessibilityLabel("Delete \(q.name)")
                    }
                }
                .accessibilityElement(children: .contain)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
        .background(Z.white).zBorder(3)
        VStack(alignment: .leading, spacing: 0) {
            ZineH2("Earlier today", size: 20)
            if p.history.isEmpty { Mono("Nothing played yet this session") }
            ForEach(p.history.prefix(8)) { h in DotRow { Mono(h.title) } right: { Mono(PlayerModel.clock(h.duration)) } }
        }
        .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
        .zBorder(3, dashed: true)
        }
    }
}

/// Drag a Running Order row onto another to move it; rows that are not in Up Next (the one playing) do not take part.
private struct QueueReorder: ViewModifier {
    let enabled: Bool
    let drop: ([String]) -> Bool
    func body(content: Content) -> some View {
        if enabled { content.dropDestination(for: String.self) { ids, _ in drop(ids) } } else { content }
    }
}
