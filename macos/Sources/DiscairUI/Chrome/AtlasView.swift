import DiscairLibrarian
import MapKit
import SwiftUI

/// The atlas (Phase 7 client gate): an Apple Maps view with one pin per place that has stated coordinates. A pin grows with
/// the recordings you own made there; a place with none you own is a white pin with a dashed border (the same rule as the
/// connection graph). A List switch shows the same places as rows. Nothing is geocoded: no coordinates, no pin.
struct AtlasView: View {
    let state: AppState
    let style: GraphStyle
    private var atlas: AtlasModel { state.atlas }
    @State private var camera: MapCameraPosition = .automatic

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                header
                if let note = atlas.note { Text(note).foregroundStyle(style.muted).padding(.top, 4) }
                if atlas.showsList { list } else { map }
                footer
            }
            .padding(.horizontal, 28).padding(.bottom, 20)
            inspector.frame(width: 290)
        }
        .task { await state.loadAtlas(); camera = .region(atlas.region) }
        .onChange(of: atlas.places.count) { _, _ in camera = .region(atlas.region) }
    }

    // MARK: Header and footer

    private var header: some View {
        @Bindable var a = atlas
        return HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text("Atlas").font(style.title).lineLimit(1).accessibilityAddTraits(.isHeader)
            Text("places & scenes").font(.system(size: 12, weight: .semibold)).foregroundStyle(style.muted)
            Spacer()
            if atlas.loading { ProgressView().controlSize(.small) }
            Picker("View", selection: $a.showsList) { Text("Map").tag(false); Text("List").tag(true) }
                .pickerStyle(.segmented).frame(width: 140).labelsHidden()
            Button("Refresh") { Task { await atlas.load(librarian: state.session?.librarian, force: true) } }
                .buttonStyle(CapsuleButtonStyle(primary: false, small: true)).disabled(atlas.loading)
        }
        .padding(.top, 4)
    }

    private var footer: some View {
        HStack(spacing: 14) {
            Label("Owned recordings made here: colour", systemImage: "circle.fill")
            Label("None owned: dashed", systemImage: "circle.dashed")
            Text("Pin size = recordings you own · only places with stated coordinates are pinned")
            Spacer()
            if atlas.truncated { Text("Showing the first places only.") }
        }
        .labelStyle(.titleAndIcon).font(.system(size: 11)).foregroundStyle(style.muted)
    }

    // MARK: Map

    private var map: some View {
        Map(position: $camera) {
            ForEach(atlas.places) { p in
                Annotation(p.entity.name, coordinate: CLLocationCoordinate2D(latitude: p.latitude, longitude: p.longitude), anchor: .center) {
                    pin(p)
                }
            }
        }
        .mapStyle(.standard(elevation: .flat, emphasis: .muted, pointsOfInterest: .excludingAll))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .frame(maxWidth: .infinity, minHeight: 420, maxHeight: .infinity)
        .accessibilityLabel("Map of \(atlas.places.count) places")
    }

    private func pin(_ p: AtlasPlace) -> some View {
        let size = AtlasGeometry.pinSize(owned: p.ownedRecordings)
        let owned = p.ownedRecordings > 0
        return Button { Task { await atlas.select(p.id, librarian: state.session?.librarian) } } label: {
            Circle()
                .fill(owned ? style.accent : Color.white)
                .overlay { Circle().strokeBorder(owned ? Color.white : style.ink, style: StrokeStyle(lineWidth: 2, dash: owned ? [] : [3, 2])) }
                .overlay { if p.id == atlas.selectedID { Circle().strokeBorder(style.ink, lineWidth: 3).padding(-4) } }
                .frame(width: size, height: size)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(p.entity.name), \(p.ownedRecordings) of \(p.recordings) recordings owned")
    }

    // MARK: List

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: 6) {
                ForEach(atlas.places) { p in
                    Button { Task { await atlas.select(p.id, librarian: state.session?.librarian) } } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(p.entity.name).font(.system(size: 14, weight: .semibold))
                                Text([p.kind, Self.coordinates(p)].compactMap { $0 }.joined(separator: " · ")).font(.system(size: 11)).foregroundStyle(style.muted)
                            }
                            Spacer()
                            Text("\(p.ownedRecordings) of \(p.recordings) owned").font(.system(size: 12)).foregroundStyle(style.muted)
                        }
                        .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                        .background(p.id == atlas.selectedID ? style.accent.opacity(0.15) : style.card, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .frame(maxWidth: .infinity, minHeight: 420, maxHeight: .infinity)
    }

    // MARK: Inspector

    private var inspector: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                if let p = atlas.selected { selectedPanel(p) } else { idlePanel }
            }
            .padding(18)
        }
        .background(style.card)
    }

    private var idlePanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Atlas").font(.system(size: 18, weight: .bold))
            Text("Choose a pin to see what was recorded there, and where each fact comes from.").foregroundStyle(style.muted)
            if let cov = atlas.coverage {
                Text(cov == "loaded" ? "MusicBrainz data: loaded." : "MusicBrainz data: not on the server yet.").font(.system(size: 11)).foregroundStyle(style.muted)
            }
        }
    }

    @ViewBuilder private func selectedPanel(_ p: AtlasPlace) -> some View {
        Text(p.entity.name).font(.system(size: 18, weight: .bold))
        Text([p.kind, "coordinates stated"].compactMap { $0 }.joined(separator: " · ")).font(.system(size: 12)).foregroundStyle(style.muted)
        Text("\(Self.coordinates(p)) · \(p.ownedRecordings) of \(p.recordings) recordings owned").font(.system(size: 11)).foregroundStyle(style.muted)
        if atlas.detailLoading { ProgressView().controlSize(.small) }
        if let note = atlas.detailNote { Text(note).font(.system(size: 12)).foregroundStyle(style.muted) }
        if let d = atlas.detail, d.place.mbid == p.id { detailPanel(d) }
    }

    @ViewBuilder private func detailPanel(_ d: KnowledgePlace) -> some View {
        if let area = d.area.first {
            block("Contained in", ([area.area] + area.containedIn).map(\.entity.name).joined(separator: " → "),
                  note: "stated chain, nearest first; nothing inferred")
        }
        if let begin = d.facts?.begin { block("Opened", [begin, d.facts?.end].compactMap { $0 }.joined(separator: " – "), note: nil) }
        if !d.recordings.isEmpty {
            @Bindable var a = atlas
            HStack {
                Text("Recordings (\(d.recordings.count), \(d.recordings.filter(\.owned).count) owned)").font(.system(size: 12, weight: .semibold))
                Spacer()
                Toggle("Discs", isOn: $a.showsDiscs).toggleStyle(.switch).controlSize(.mini)
                    .accessibilityHint("Shows each album's disc image next to its recordings")
            }
            ForEach(d.recordings.prefix(12), id: \.recording.mbid) { r in
                VStack(alignment: .leading, spacing: 3) {
                    HStack(alignment: .center, spacing: 8) {
                        if atlas.showsDiscs, let rgid = AtlasGeometry.discGroup(r.albums) { AlbumDisc(rgid: rgid, diameter: 34) }
                        VStack(alignment: .leading, spacing: 3) {
                            Text(r.recording.name).font(.system(size: 12, weight: .semibold))
                            Text(r.albums.map(\.album.name).joined(separator: " · ")).font(.system(size: 11)).foregroundStyle(style.muted).lineLimit(2)
                        }
                    }
                    if let c = r.credits.first { Text("\(c.source) · \(c.evidenceClass) · \(c.matchQuality)").font(.system(size: 10)).foregroundStyle(style.muted) }
                    if let album = r.albums.first(where: \.owned), let item = GraphNodeFace.ownedAlbum(album.album.name, library: state.library) {
                        Button("Open album") { state.open(album: item) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                    }
                }
                .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                .background(.background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            if d.recordings.count > 12 || d.truncated { Text("More recordings are linked than shown.").font(.system(size: 11)).foregroundStyle(style.muted) }
        }
        if !d.events.isEmpty { block("Events", d.events.map(\.entity.name).joined(separator: " · "), note: nil) }
        if !d.notLoaded.isEmpty { Text("Not loaded: \(d.notLoaded.joined(separator: ", "))").font(.system(size: 11)).foregroundStyle(style.muted) }
    }

    private func block(_ title: String, _ text: String, note: String?) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(.system(size: 12, weight: .semibold))
            Text(text).font(.system(size: 12))
            if let note { Text(note).font(.system(size: 10)).foregroundStyle(style.muted) }
        }
        .padding(10).frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private static func coordinates(_ p: AtlasPlace) -> String {
        String(format: "%.2f°%@ %.2f°%@", abs(p.latitude), p.latitude >= 0 ? "N" : "S", abs(p.longitude), p.longitude >= 0 ? "E" : "W")
    }
}
