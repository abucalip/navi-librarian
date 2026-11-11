import SwiftUI

/// Smart Playlists (contract 6.7): a rule builder on the left, the songs the rules pick on the right, Play and Save
/// to Navidrome on top. No mockup exists for this screen; it reuses Cupertino's cards, capsules and bold titles.
struct CupertinoSmartPlaylists: View {
    let state: AppState
    private var smart: SmartPlaylistModel { state.smart }
    private let previewLimit = 100

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Smart Playlists").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                Text("Rules pick songs from your library. Save a result to Navidrome to play it anywhere.").foregroundStyle(CU.textSecondary)
                picker
                if let list = smart.selected {
                    editor(list)
                    results(list)
                } else {
                    Text("No smart playlists yet. Add one to start.").foregroundStyle(CU.textSecondary)
                }
                if !smart.remote.isEmpty { remote }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task { await state.loadSmartPlaylists() }
    }

    private var picker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(smart.lists) { l in
                    Button(l.name) { smart.selectedID = l.id }
                        .buttonStyle(CapsuleButtonStyle(primary: l.id == smart.selectedID, small: true))
                }
                Button("New playlist") { smart.add() }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
            }
        }
    }

    private func binding(_ list: SmartPlaylist) -> Binding<SmartPlaylist> {
        Binding(get: { smart.lists.first { $0.id == list.id } ?? list }, set: { smart.update($0) })
    }

    private func editor(_ list: SmartPlaylist) -> some View {
        let b = binding(list)
        return VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                TextField("Name", text: b.name).textFieldStyle(.plain).font(CU.title(22))
                Spacer(minLength: 8)
                Button("Delete") { smart.remove(list.id) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
            }
            HStack(spacing: 8) {
                Text("Match").foregroundStyle(CU.textSecondary)
                Picker("Match", selection: b.matchAll) { Text("all").tag(true); Text("any").tag(false) }
                    .labelsHidden().fixedSize()
                Text("of these rules").foregroundStyle(CU.textSecondary)
            }
            ForEach(b.rules) { $rule in
                HStack(spacing: 8) {
                    Picker("Field", selection: $rule.field) { ForEach(SmartField.allCases) { Text($0.label).tag($0) } }
                        .labelsHidden().fixedSize()
                        .onChange(of: rule.field) { _, f in
                            if !f.operators.contains(rule.op) { rule.op = f.operators[0] }
                            if f.isInsight, f.choices?.contains(where: { $0.value == rule.value }) != true { rule.value = "" }
                        }
                    Picker("Condition", selection: $rule.op) { ForEach(rule.field.operators) { Text($0.label).tag($0) } }
                        .labelsHidden().fixedSize()
                    if rule.field.isInsight {
                        Picker("Value", selection: $rule.value) {
                            Text("Choose…").tag("")
                            ForEach(rule.field.choices(including: rule.value)) { Text($0.label).tag($0.value) }
                        }.labelsHidden().fixedSize()
                    } else {
                        TextField(rule.field.valueHint, text: $rule.value).textFieldStyle(.roundedBorder).frame(maxWidth: 180)
                    }
                    Button { b.wrappedValue.rules.removeAll { $0.id == rule.id } } label: { Image(systemName: "minus.circle") }
                        .buttonStyle(.plain).foregroundStyle(CU.textSecondary).accessibilityLabel("Remove rule")
                }
            }
            if b.wrappedValue.rules.contains(where: { $0.field.isInsight }) {
                Text("Insight rules are worked out by the server. This app lists every song for them.").font(.caption).foregroundStyle(CU.textSecondary)
            }
            HStack(spacing: 8) {
                Button("Add rule") { b.wrappedValue.rules.append(SmartRule(field: .artist, op: .contains, value: "")) }
                    .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                Spacer(minLength: 8)
                Text("Order").foregroundStyle(CU.textSecondary)
                Picker("Order", selection: b.order) { ForEach(SmartOrder.allCases) { Text($0.label).tag($0) } }.labelsHidden().fixedSize()
                Text("Limit").foregroundStyle(CU.textSecondary)
                Picker("Limit", selection: b.limit) {
                    Text("None").tag(0); ForEach([25, 50, 100, 250], id: \.self) { Text("\($0)").tag($0) }
                }.labelsHidden().fixedSize()
            }
        }
        .padding(16)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .contain)
    }

    private func results(_ list: SmartPlaylist) -> some View {
        let songs = state.smartSongs(list)
        return VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text("\(songs.count) songs").font(CU.title(20))
                if state.library.songsHaveMore { Text("(first \(state.library.songs.count) songs read)").foregroundStyle(CU.textSecondary) }
                Spacer(minLength: 8)
                Button("Play") { state.play(rows: songs, startAt: 0) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(songs.isEmpty)
                Button(smart.saving ? "Saving…" : "Save to Navidrome") { state.saveSmart(list, songs: songs) }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled(songs.isEmpty || smart.saving)
            }
            if let s = smart.status { Text(s).foregroundStyle(CU.textSecondary).font(CU.Font.callout.weighted(.regular)) }
            if songs.isEmpty {
                Text(state.library.songsLoading ? "Reading your songs…" : "No songs match these rules.").foregroundStyle(CU.textSecondary)
            }
            ForEach(Array(songs.prefix(previewLimit).enumerated()), id: \.offset) { i, s in
                Button { state.play(rows: songs, startAt: i) } label: {
                    HStack(spacing: 8) {
                        Text(s.title).fontWeight(.medium).lineLimit(1)
                        Text(s.artist).foregroundStyle(CU.textSecondary).lineLimit(1)
                        Spacer(minLength: 8)
                        Text("\(s.plays) plays").font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
                    }
                    .padding(.vertical, 4).contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
            if songs.count > previewLimit { Text("and \(songs.count - previewLimit) more").foregroundStyle(CU.textSecondary) }
        }
    }

    private var remote: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("On Navidrome").font(CU.title(20))
            ForEach(smart.remote) { p in
                HStack { Text(p.name).lineLimit(1); Spacer(); Text("\(p.songCount) songs").foregroundStyle(CU.textSecondary) }
            }
        }
    }
}
