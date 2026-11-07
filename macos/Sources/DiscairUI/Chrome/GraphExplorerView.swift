import DiscairLibrarian
import SwiftUI

/// Colours and type a theme gives the explorer. The screen itself is the same in every theme.
struct GraphStyle {
    let accent: Color, ink: Color, muted: Color, card: Color, title: Font
    static let cupertino = GraphStyle(accent: CU.accent, ink: CU.ink, muted: CU.muted, card: CU.card, title: CU.title(34))
    static let zine = GraphStyle(accent: Z.red, ink: Z.ink, muted: Z.ink.opacity(0.6), card: Z.paper, title: Z.an(60))
}

/// The connection graph (Phase 7 client gate). An artist in the middle; artists show their photo and albums their artwork.
/// Owned nodes are in colour with a solid edge; anything the library does not hold is black and white with a dashed edge.
/// A solid line is a stated credit, a dashed line is a link that is not a credit. Every node shows its evidence.
struct GraphExplorerView: View {
    let state: AppState
    let style: GraphStyle
    private var graph: GraphExplorerModel { state.graph }

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                header
                if let note = graph.note { Text(note).foregroundStyle(style.muted).padding(.top, 4) }
                canvas
                footer
            }
            .padding(.horizontal, 28).padding(.bottom, 20)
            inspector.frame(width: 290)
        }
        .task { await state.loadConnections() }
        .onChange(of: graph.depth) { _, _ in Task { await graph.reload(librarian: state.session?.librarian) } }
        .onChange(of: graph.creditsOnly) { _, _ in Task { await graph.reload(librarian: state.session?.librarian) } }
    }

    // MARK: Header and footer

    private var header: some View {
        @Bindable var g = graph
        return VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                if graph.canGoBack {
                    Button("Back") { Task { await graph.back(librarian: state.session?.librarian) } }.buttonStyle(CapsuleButtonStyle(primary: false, small: true))
                }
                Text(graph.centre?.name ?? "Connections").font(style.title).lineLimit(1).accessibilityAddTraits(.isHeader)
                Spacer()
                if graph.loading { ProgressView().controlSize(.small) }
            }
            HStack(spacing: 14) {
                Picker("Depth", selection: $g.depth) { ForEach(1...3, id: \.self) { Text("Depth \($0)").tag($0) } }
                    .pickerStyle(.segmented).frame(width: 240).labelsHidden()
                Toggle("Credits only", isOn: $g.creditsOnly).toggleStyle(.switch).tint(style.accent)
            }
        }
        .padding(.top, 4)
    }

    private var footer: some View {
        HStack(spacing: 14) {
            legend
            Spacer()
            if let t = graph.truncatedText { Text(t).font(.system(size: 11)).foregroundStyle(style.muted) }
            if graph.nextCursor != nil {
                Button("Load more") { Task { await graph.loadMore(librarian: state.session?.librarian) } }
                    .buttonStyle(CapsuleButtonStyle(primary: false, small: true)).disabled(graph.loading)
            }
        }
        .font(.system(size: 11)).foregroundStyle(style.muted)
    }

    private var legend: some View {
        HStack(spacing: 10) {
            Label("In library: colour", systemImage: "circle.fill")
            Label("Not in library: black and white", systemImage: "circle.dashed")
            Label("Stated credit", systemImage: "line.diagonal")
        }
        .labelStyle(.titleAndIcon)
    }

    // MARK: Canvas

    private var canvas: some View {
        GeometryReader { geo in canvasContent(geo.size) }
        .frame(maxWidth: .infinity, minHeight: 520, maxHeight: .infinity)
        .accessibilityElement(children: .contain)
    }

    private func canvasContent(_ size: CGSize) -> some View {
            let layout = graph.layout
            let maxDepth = max(graph.nodes.map(\.depth).max() ?? 1, 1)
            let reach = GraphLayout.radius(of: maxDepth)
            let half = min(size.width, size.height) / 2
            let ring1 = graph.nodes.filter { $0.depth == 1 }.count
            let nodeSize = nodeSize(half: half, reach: reach, count: ring1)
            let scale = (half - nodeSize / 2 - 10) / reach
            let origin = CGPoint(x: size.width / 2, y: size.height / 2)
            func point(_ id: String) -> CGPoint {
                let p = layout[id] ?? .zero
                return CGPoint(x: origin.x + p.x * scale, y: origin.y + p.y * scale)
            }
            return ZStack {
                Canvas { ctx, _ in
                    for n in graph.nodes {
                        var path = Path(); path.move(to: point(n.via)); path.addLine(to: point(n.id))
                        let picked = n.id == graph.selectedID
                        ctx.stroke(path, with: .color(picked ? style.accent : style.ink.opacity(0.35)),
                                   style: StrokeStyle(lineWidth: picked ? 3 : 1.5, dash: n.credit ? [] : [4, 4]))
                    }
                }
                ForEach(graph.nodes) { n in
                    nodeButton(n, size: nodeSize).position(point(n.id))
                }
                if let c = graph.centre {
                    GraphNodeFace(entity: c, size: nodeSize * 1.5, library: state.library, hintArtist: c.name, forceOwned: true, ink: style.ink)
                        .position(origin)
                        .accessibilityLabel("Centre: \(c.name)")
                }
            }
    }

    private func nodeSize(half: CGFloat, reach: Double, count: Int) -> CGFloat {
        guard count > 0 else { return 64 }
        let ring = 2 * Double.pi * (half / reach)          // length of the first ring in points
        return CGFloat(min(64, max(30, ring / Double(count) * 0.85)))
    }

    private func nodeButton(_ n: GraphNode, size: CGFloat) -> some View {
        Button { graph.selectedID = n.id } label: {
            VStack(spacing: 2) {
                GraphNodeFace(entity: n.entity, size: size, library: state.library, hintArtist: graph.centre?.name ?? "", forceOwned: false, ink: style.ink)
                    .overlay { if n.id == graph.selectedID { Circle().strokeBorder(style.accent, lineWidth: 3).padding(-4) } }
                if size >= 44 { Text(n.entity.name).font(.system(size: 10, weight: .semibold)).lineLimit(1).frame(width: 90) }
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(n.entity.name), \(n.entity.type), \(n.entity.owned ? "in your library" : "not in your library")")
    }

    // MARK: Inspector

    private var inspector: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                if let n = graph.selected { selectedPanel(n) } else { idlePanel }
            }
            .padding(18)
        }
        .background(style.card)
    }

    private var idlePanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(graph.centre?.name ?? "Connections").font(.system(size: 18, weight: .bold))
            Text("Choose a node to see how it connects, and where each link comes from.").foregroundStyle(style.muted)
            if let cov = graph.coverage {
                Text(cov == "loaded" ? "MusicBrainz data: loaded." : "MusicBrainz data: not on the server yet.").font(.system(size: 11)).foregroundStyle(style.muted)
            }
        }
    }

    @ViewBuilder private func selectedPanel(_ n: GraphNode) -> some View {
        Text(n.entity.name).font(.system(size: 18, weight: .bold))
        Text("\(n.entity.type) · \(n.entity.owned ? "in your library" : "not in your library") · depth \(n.depth)").font(.system(size: 12)).foregroundStyle(style.muted)
        HStack {
            if let artist = state.library.artist(named: n.entity.name), ["artist", "person", "group"].contains(n.entity.type) {
                Button("Open artist") { state.open(artist: artist) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
            }
            if ["release", "release_group"].contains(n.entity.type), let album = GraphNodeFace.ownedAlbum(n.entity.name, library: state.library) {
                Button("Open album") { state.open(album: album) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
            }
            if ["artist", "person", "group"].contains(n.entity.type) {
                Button("Re-centre here") { Task { await graph.recentre(on: n, librarian: state.session?.librarian) } }
                    .buttonStyle(CapsuleButtonStyle(primary: false, small: true))
            }
        }
        Text(n.credit ? "Stated credit" : "Connection, not a credit").font(.system(size: 12, weight: .semibold))
        ForEach(Array(n.evidence.enumerated()), id: \.offset) { _, e in
            VStack(alignment: .leading, spacing: 3) {
                Text(e.label.capitalized).font(.system(size: 12, weight: .semibold))
                Text("\(e.source) · \(e.evidenceClass) · \(e.matchQuality)").font(.system(size: 11)).foregroundStyle(style.muted)
                if let url = e.sourceURL { Text(url).font(.system(size: 10)).foregroundStyle(style.muted).lineLimit(1).truncationMode(.middle) }
            }
            .padding(10).frame(maxWidth: .infinity, alignment: .leading)
            .background(.background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
    }
}

/// One node's picture. Artists show their photo, albums their artwork, everything else a symbol. An entity the library
/// does not hold is drawn black and white inside a dashed black border; one it holds keeps its colour and a solid border.
struct GraphNodeFace: View {
    let entity: KnowledgeEntity
    let size: CGFloat
    let library: LibraryModel
    let hintArtist: String
    let forceOwned: Bool
    let ink: Color

    private var owned: Bool { forceOwned || entity.owned }
    private var isPerson: Bool { ["artist", "person", "group"].contains(entity.type) }
    private var isAlbum: Bool { ["release", "release_group"].contains(entity.type) }

    /// The library album with this title, so owned covers come from Navidrome.
    static func ownedAlbum(_ title: String, library: LibraryModel) -> AlbumItem? {
        (library.albums + library.recent).first { $0.title.caseInsensitiveCompare(title) == .orderedSame }
    }

    private var symbol: String {
        switch entity.type {
        case "work": "music.note.list"
        case "recording": "waveform"
        case "label": "tag"
        case "area", "place": "mappin.and.ellipse"
        case "event": "calendar"
        case "instrument": "guitars"
        default: "circle.hexagongrid"
        }
    }

    var body: some View {
        Group {
            if isPerson {
                ArtistPhoto(name: entity.name, size: size)
            } else if isAlbum {
                CoverView(album: album).frame(width: size, height: size).clipShape(RoundedRectangle(cornerRadius: size * 0.12, style: .continuous))
            } else {
                Image(systemName: symbol).font(.system(size: size * 0.42)).foregroundStyle(owned ? ink : ink.opacity(0.7))
                    .frame(width: size, height: size).background(.white, in: Circle())
            }
        }
        .grayscale(owned ? 0 : 1)
        .overlay {
            if isAlbum {
                RoundedRectangle(cornerRadius: size * 0.12, style: .continuous).strokeBorder(owned ? ink : .black, style: border)
            } else { Circle().strokeBorder(owned ? ink : .black, style: border) }
        }
        .frame(width: size, height: size)
    }

    private var border: StrokeStyle { StrokeStyle(lineWidth: owned ? 2 : 2, dash: owned ? [] : [5, 3]) }

    private var album: AlbumItem {
        if let known = Self.ownedAlbum(entity.name, library: library) { return known }
        // Not matched in the library: the Librarian looks the cover up by artist and title.
        return AlbumItem(id: abs(entity.mbid.hashValue % 900_000), title: entity.name, artist: hintArtist, year: 0, genre: "", format: "",
                         owned: false, hue: LibraryModel.hue(for: entity.name))
    }
}
