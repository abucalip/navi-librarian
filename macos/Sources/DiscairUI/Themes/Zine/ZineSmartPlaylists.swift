import SwiftUI

/// Smart Playlists in Zine's language: "Rule Sheets". Rules sit on a bordered sheet, the picked songs read like a
/// track list below it. No mockup exists for this screen; it reuses the Gap Radar parts.
struct ZineSmartPlaylists: View {
    let state: AppState
    private var smart: SmartPlaylistModel { state.smart }
    private let previewLimit = 100

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Smart Playlists").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("Rules pick the songs, Navidrome keeps them").padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(smart.lists) { l in
                        Button(l.name) { smart.selectedID = l.id }.buttonStyle(ZineButtonStyle(kind: l.id == smart.selectedID ? .yellow : .plain, small: true))
                    }
                    Button("New playlist") { smart.add() }.buttonStyle(ZineButtonStyle(small: true))
                }
                .padding(.trailing, 6).padding(.bottom, 6)
            }
            if let list = smart.selected {
                sheet(list)
                results(list)
            } else {
                Mono("No smart playlists yet. Add one to start.")
            }
            if !smart.remote.isEmpty {
                Anton("On Navidrome", 24)
                ForEach(smart.remote) { p in HStack { Text(p.name).font(Z.mono(12)).lineLimit(1); Spacer(); Mono("\(p.songCount) songs", size: 10) } }
            }
        }
        .task { await state.loadSmartPlaylists() }
    }

    private func binding(_ list: SmartPlaylist) -> Binding<SmartPlaylist> {
        Binding(get: { smart.lists.first { $0.id == list.id } ?? list }, set: { smart.update($0) })
    }

    private func sheet(_ list: SmartPlaylist) -> some View {
        let b = binding(list)
        return VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                TextField("Name", text: b.name).textFieldStyle(.plain).font(Z.an(28)).textCase(.uppercase)
                Spacer(minLength: 8)
                Button("Delete") { smart.remove(list.id) }.buttonStyle(ZineButtonStyle(kind: .red, small: true))
            }
            HStack(spacing: 8) {
                Mono("Match")
                Picker("Match", selection: b.matchAll) { Text("all").tag(true); Text("any").tag(false) }.labelsHidden().fixedSize()
                Mono("of these rules")
            }
            ForEach(b.rules) { $rule in
                HStack(spacing: 8) {
                    Picker("Field", selection: $rule.field) { ForEach(SmartField.allCases) { Text($0.label).tag($0) } }
                        .labelsHidden().fixedSize()
                        .onChange(of: rule.field) { _, f in if !f.operators.contains(rule.op) { rule.op = f.operators[0] } }
                    Picker("Condition", selection: $rule.op) { ForEach(rule.field.operators) { Text($0.label).tag($0) } }
                        .labelsHidden().fixedSize()
                    TextField(rule.field.isText ? "text" : "number", text: $rule.value).textFieldStyle(.plain).font(Z.mono(12))
                        .padding(.horizontal, 6).padding(.vertical, 3).frame(maxWidth: 180).background(Z.white).zBorder(2)
                    Button { b.wrappedValue.rules.removeAll { $0.id == rule.id } } label: { Text("×").font(Z.mono(14, bold: true)) }
                        .buttonStyle(.plain).accessibilityLabel("Remove rule")
                }
            }
            HStack(spacing: 12) {
                Button("Add rule") { b.wrappedValue.rules.append(SmartRule(field: .artist, op: .contains, value: "")) }
                    .buttonStyle(ZineButtonStyle(small: true))
                Spacer(minLength: 8)
                Mono("Order")
                Picker("Order", selection: b.order) { ForEach(SmartOrder.allCases) { Text($0.label).tag($0) } }.labelsHidden().fixedSize()
                Mono("Limit")
                Picker("Limit", selection: b.limit) {
                    Text("None").tag(0); ForEach([25, 50, 100, 250], id: \.self) { Text("\($0)").tag($0) }
                }.labelsHidden().fixedSize()
            }
        }
        .padding(14).background(Z.paper).zBorder(3)
        .accessibilityElement(children: .contain)
    }

    private func results(_ list: SmartPlaylist) -> some View {
        let songs = state.smartSongs(list)
        return VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                Anton("\(songs.count) songs", 26)
                if state.library.songsHaveMore { Mono("first \(state.library.songs.count) read") }
                Spacer(minLength: 8)
                Button("Play") { state.play(rows: songs, startAt: 0) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true)).disabled(songs.isEmpty)
                Button(smart.saving ? "Saving…" : "Save to Navidrome") { state.saveSmart(list, songs: songs) }
                    .buttonStyle(ZineButtonStyle(small: true)).disabled(songs.isEmpty || smart.saving)
            }
            if let s = smart.status { Mono(s, size: 10) }
            if songs.isEmpty { Mono(state.library.songsLoading ? "Reading your songs…" : "No songs match these rules.") }
            ForEach(Array(songs.prefix(previewLimit).enumerated()), id: \.offset) { i, s in
                Button { state.play(rows: songs, startAt: i) } label: {
                    HStack(spacing: 10) {
                        Text(s.title).font(Z.mono(12, bold: true)).lineLimit(1)
                        Text(s.artist).font(Z.mono(12)).lineLimit(1)
                        Spacer(minLength: 8)
                        Mono("\(s.plays) plays", size: 10)
                    }
                    .padding(.vertical, 3).contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
            if songs.count > previewLimit { Mono("and \(songs.count - previewLimit) more") }
        }
    }
}
