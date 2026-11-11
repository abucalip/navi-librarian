import DiscairLibrarian
import SwiftUI

/// Connections, the credit graph, as `docs/redesign.md` section 5.2 draws it (mockups `connections--*`): a control bar with every
/// control labelled, the graph in sectors by kind with nodes that are always named, a List view for the keyboard, VoiceOver and
/// dense walks, a 300 pt inspector, and a sentence for each state (no start, not loaded, truncated, failed).
/// The data is the explorer model's; the Zine theme keeps its own look in `GraphExplorerView`.
struct CupertinoConnections: View {
    let state: AppState
    private var graph: GraphExplorerModel { state.graph }
    private var librarian: LibrarianClient? { state.session?.librarian }

    /// The inspector is 300 wide (section 5.2).
    static let inspectorWidth: CGFloat = 300

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                header
                controlBar
                if hasStart {
                    HStack(alignment: .top, spacing: CU.Space.m) {
                        VStack(alignment: .leading, spacing: CU.Space.m) {
                            notices
                            if graph.showsList || graph.tooManyToDraw { list } else { graphArea }
                        }
                        .frame(maxWidth: .infinity, alignment: .topLeading)
                        inspector.frame(width: Self.inspectorWidth)
                    }
                } else {
                    startPanel
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .onChange(of: graph.depth) { _, _ in Task { await graph.reload(librarian: librarian) } }
        .onChange(of: graph.creditsOnly) { _, _ in Task { await graph.reload(librarian: librarian) } }
    }

    /// A start is chosen once the walk has a centre or the owner picked an artist (even one the server has no data on).
    private var hasStart: Bool { graph.centre != nil || graph.startName != nil }

    // MARK: Header and control bar

    private var header: some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
                Text("Connections").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                if graph.loading { ProgressView().controlSize(.small).accessibilityLabel("Loading connections") }
            }
            Text("Who played, produced and recorded with whom, from stated MusicBrainz credits.")
                .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
        }
        .padding(.top, CU.Space.xs)
    }

    private func labelled<C: View>(_ label: String, @ViewBuilder _ control: () -> C) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            Text(label).font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.textSecondary)
            control().frame(height: 32)
        }
    }

    private var controlBar: some View {
        @Bindable var g = graph
        return HStack(alignment: .bottom, spacing: CU.Space.l) {
            if graph.canGoBack, let back = graph.backTitle {
                Button { Task { await graph.back(librarian: librarian) } } label: {
                    HStack(spacing: CU.Space.xs) { Image(systemName: "chevron.left").font(CU.Icon.small(.bold)); Text(back).lineLimit(1) }
                }
                .buttonStyle(CapsuleButtonStyle())
                .accessibilityLabel("Back to \(back)")
                .frame(height: 32)
            }
            labelled("Start from") { CupertinoStartField(state: state, current: graph.centre?.name ?? graph.startName) }
            labelled("Reach") {
                CUSegmented([(value: 1, label: "1 step"), (value: 2, label: "2 steps"), (value: 3, label: "3 steps")],
                            selection: $g.depth, accessibilityName: "Reach", inControlBar: true)
            }
            labelled("Credits only") {
                Toggle("Credits only", isOn: $g.creditsOnly).labelsHidden().toggleStyle(.switch).tint(CU.accent)
                    .frame(maxHeight: .infinity, alignment: .center)
            }
            Spacer(minLength: 0)
            labelled("View") {
                CUSegmented([(value: false, label: "Graph"), (value: true, label: "List")], selection: $g.showsList,
                            accessibilityName: "View", inControlBar: true)
            }
        }
    }

    // MARK: Notices

    @ViewBuilder private var notices: some View {
        if notLoaded {
            if graph.updateRequested {
                CUNotice(kind: .success, lead: "Requested.",
                         message: graph.updateNote ?? "The server fetches it on its next run. Come back later; this page does not need to stay open.")
            } else {
                CUNotice(kind: .info, lead: "Not loaded.",
                         message: "The server has no MusicBrainz data for \(graph.startName ?? "this artist") yet. This says nothing about the artist.",
                         actionTitle: graph.canRequestUpdate ? "Request update" : nil,
                         action: graph.canRequestUpdate ? { Task { await graph.requestUpdate(name: graph.startName ?? "", librarian: librarian) } } : nil)
                if graph.updateFailed, let n = graph.updateNote { CUNotice(kind: .danger, lead: "Could not request the update.", message: n) }
            }
        } else if let note = graph.note, graph.loadFailure == nil {
            CUNotice(kind: .info, lead: note)
        }
        if let t = graph.truncatedNotice {
            CUNotice(kind: .warning, lead: t.lead, message: t.message,
                     actionTitle: graph.showsList ? nil : "Switch to List", action: graph.showsList ? nil : { graph.showsList = true })
        }
        if graph.tooManyToDraw, !graph.showsList {
            CUNotice(kind: .info, lead: "Too many to draw.", message: "Nodes would be smaller than 40 pt, so the connections are listed instead.")
        }
        if let failure = graph.loadFailure {
            CUNotice(kind: .danger, lead: failure.wasLoadMore ? "Couldn’t load more." : "Couldn’t load connections.",
                     message: failure.summary + (graph.nodes.isEmpty ? "" : " The connections already shown are kept."),
                     actionTitle: "Try again", action: { Task { await graph.retry(librarian: librarian) } })
        }
    }

    /// The start artist has no data on the server: a 404, or a walk that came back pending.
    private var notLoaded: Bool {
        graph.nodes.isEmpty && (graph.canRequestUpdate || graph.updateRequested || graph.coverage == "pending" || graph.updateFailed)
    }

    // MARK: No start chosen

    private var startPanel: some View {
        let artists = Array(state.library.artists.sorted { $0.albumCount > $1.albumCount }.prefix(6))
        return CUPanel {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                Text("Start from an artist you own").cuRole(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                Text("Type a name above, or pick one of the artists you have the most albums by. The graph shows people, albums, places and labels within the reach you choose.")
                    .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).frame(maxWidth: 560, alignment: .leading)
                if let note = graph.note { CUNotice(kind: .info, lead: note) }
                HStack(alignment: .top, spacing: CU.Space.l) {
                    ForEach(artists) { a in
                        Button { Task { await state.loadConnections(for: a) } } label: {
                            VStack(spacing: CU.Space.xs) {
                                GraphNodeFace(entity: .preview(name: a.name, type: "artist", owned: true), size: 72, library: state.library, hintArtist: a.name, forceOwned: true, ink: CU.text)
                                Text(a.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                                Text(a.albumCount == 1 ? "1 album" : "\(a.albumCount) albums").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                            }
                            .frame(width: 112).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(a.name), \(a.albumCount) albums. Start from this artist")
                    }
                }
                Divider().overlay(CU.separator)
                legend
            }
            .padding(CU.Space.m)
        }
    }

    // MARK: Graph

    private var graphArea: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            GeometryReader { geo in canvas(geo.size) }
                .frame(maxWidth: .infinity, minHeight: graph.nodes.isEmpty ? 300 : 560)
                .accessibilityElement(children: .contain)
                .accessibilityLabel("Connection graph. \(graph.summaryLine)")
            legend
            HStack(spacing: CU.Space.s) {
                Spacer(minLength: 0)
                Text(graph.footerCount).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                if graph.nextCursor != nil { Button("Load more") { Task { await graph.loadMore(librarian: librarian) } }.buttonStyle(CapsuleButtonStyle()).disabled(graph.loading) }
            }
        }
    }

    /// Node sizes from section 5.2: the start artist 72, step 1 48, step 2 32. A ring that would need smaller nodes switches to List.
    enum Sizes { static let centre: CGFloat = 72, step1: CGFloat = 48, step2: CGFloat = 32 }

    private func canvas(_ size: CGSize) -> some View {
        let layout = graph.sectorLayout
        let deepest = max(graph.nodes.map(\.depth).max() ?? 1, 1)
        // Rings are measured in points (188, 292). The canvas only scales down when the window is too small to hold the outermost node.
        let outer = GraphLayout.points(of: deepest) + Sizes.step2 + 28
        let scale = min(1, (min(size.width, size.height) / 2) / outer)
        let origin = CGPoint(x: size.width / 2, y: size.height / 2)
        func point(_ id: String) -> CGPoint {
            let p = layout[id] ?? .zero
            return CGPoint(x: origin.x + p.x * GraphLayout.firstRingPoints * scale, y: origin.y + p.y * GraphLayout.firstRingPoints * scale)
        }
        let centres = GraphLayout.sectorCentres(graph.nodes.map { .init(id: $0.id, depth: $0.depth, via: $0.via, kind: $0.entity.type) })
        return ZStack {
            Canvas { ctx, _ in
                for depth in 1...max(graph.depth, deepest) where !graph.nodes.isEmpty {
                    let r = GraphLayout.points(of: depth) * scale
                    let ring = Path(ellipseIn: CGRect(x: origin.x - r, y: origin.y - r, width: 2 * r, height: 2 * r))
                    ctx.stroke(ring, with: .color(CU.separatorStrong.opacity(0.7)), style: StrokeStyle(lineWidth: 1, dash: [1, 5]))
                }
                for n in graph.nodes where n.id != graph.selectedID {
                    var path = Path(); path.move(to: point(n.via)); path.addLine(to: point(n.id))
                    ctx.stroke(path, with: .color(CU.chart2), style: StrokeStyle(lineWidth: 1.5, dash: n.credit ? [] : [4, 4]))
                }
                if let n = graph.selected {
                    var path = Path(); path.move(to: point(n.via)); path.addLine(to: point(n.id))
                    ctx.stroke(path, with: .color(CU.accent), style: StrokeStyle(lineWidth: 3, dash: n.credit ? [] : [4, 4]))
                }
            }
            .accessibilityHidden(true)
            ForEach(GraphSector.allCases, id: \.self) { sector in
                if let angle = centres[sector] {
                    Text(sector.title).cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                        .padding(.horizontal, CU.Space.xs).background(CU.content.opacity(0.85), in: Capsule())
                        .position(x: origin.x + cos(angle) * 112 * scale, y: origin.y + sin(angle) * 112 * scale)
                        .accessibilityHidden(true)
                }
            }
            ForEach(graph.nodes) { n in
                let p = point(n.id), a = atan2(p.y - origin.y, p.x - origin.x)
                nodeFace(n).position(p)
                nodeLabel(n, angle: a).position(Self.labelCentre(for: p, angle: a, size: n.depth <= 1 ? Sizes.step1 : Sizes.step2))
            }
            if let c = graph.centre {
                VStack(spacing: CU.Space.xs) {
                    GraphNodeFace(entity: c, size: Sizes.centre, library: state.library, hintArtist: c.name, forceOwned: true, ink: CU.text)
                    Text(c.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1).frame(width: 140)
                }
                .position(x: origin.x, y: origin.y + 10)
                .accessibilityElement(children: .ignore).accessibilityLabel("Centre: \(c.name)")
            } else if let name = graph.startName {
                notLoadedCentre(name).position(origin)
            }
        }
        .clipped()
    }

    private func nodeFace(_ n: GraphNode) -> some View {
        let size = n.depth <= 1 ? Sizes.step1 : Sizes.step2
        let picked = n.id == graph.selectedID
        return Button { graph.selectedID = picked ? nil : n.id } label: {
            GraphNodeFace(entity: n.entity, size: size, library: state.library, hintArtist: graph.centre?.name ?? "", forceOwned: false, ink: CU.text, discs: false)
                .overlay {
                    if picked {
                        if GraphSector.of(kind: n.entity.type) == .albums {
                            RoundedRectangle(cornerRadius: size * 0.12 + 4, style: .continuous).strokeBorder(CU.accent, lineWidth: 3).padding(-4)
                        } else { Circle().strokeBorder(CU.accent, lineWidth: 3).padding(-4) }
                    }
                }
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(CupertinoConnections.accessibilityName(n))
        .accessibilityAddTraits(picked ? .isSelected : [])
    }

    /// The name sits on the outer side of its node, so neighbours on the ring do not cover each other's labels: beside the node on
    /// the left and right of the ring, above or below it at the top and bottom.
    static let labelWidth: CGFloat = 84
    static func labelCentre(for p: CGPoint, angle: CGFloat, size: CGFloat) -> CGPoint {
        let side = abs(cos(angle)) > 0.5
        if side {
            let sign: CGFloat = cos(angle) > 0 ? 1 : -1
            return CGPoint(x: p.x + sign * (size / 2 + 6 + labelWidth / 2), y: p.y)
        }
        let sign: CGFloat = sin(angle) > 0 ? 1 : -1
        return CGPoint(x: p.x, y: p.y + sign * (size / 2 + 16))
    }

    private func nodeLabel(_ n: GraphNode, angle: CGFloat) -> some View {
        let picked = n.id == graph.selectedID
        let side = abs(cos(angle)) > 0.5
        return Text(n.entity.name).font(CU.Font.caption.weighted(.semibold)).foregroundStyle(picked ? CU.accentStrong : CU.text)
            .multilineTextAlignment(side ? (cos(angle) > 0 ? .leading : .trailing) : .center).lineLimit(2)
            .frame(width: Self.labelWidth, alignment: side ? (cos(angle) > 0 ? .leading : .trailing) : .center)
            .allowsHitTesting(false).accessibilityHidden(true)
    }

    private func notLoadedCentre(_ name: String) -> some View {
        VStack(spacing: CU.Space.s) {
            GraphNodeFace(entity: .preview(name: name, type: "artist", owned: true), size: Sizes.centre, library: state.library, hintArtist: name, forceOwned: true, ink: CU.text)
            Text(name).cuRole(CU.Font.headline).foregroundStyle(CU.text)
            Text(graph.loading ? "Reading connections…" : "No connections to draw yet.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
        }
    }

    static func accessibilityName(_ n: GraphNode) -> String {
        "\(n.entity.name), \(GraphWording.kindWord(n.entity.type)), \(n.depth == 1 ? "1 step" : "\(n.depth) steps"), \(n.entity.owned ? "in your library" : "not in your library"), \(n.credit ? "credit" : "link, not a credit")"
    }

    // MARK: Legend

    private var legend: some View {
        HStack(spacing: CU.Space.m) {
            legendItem("In your library") { Circle().fill(CU.accentTint).overlay(Circle().strokeBorder(CU.text, lineWidth: 2)).frame(width: 14, height: 14) }
            legendItem("Not in your library") { Circle().fill(CU.bgFill).overlay(Circle().strokeBorder(CU.text, style: StrokeStyle(lineWidth: 1.5, dash: [3, 2]))).frame(width: 14, height: 14) }
            legendItem("Stated credit") { Rectangle().fill(CU.chart2).frame(width: 24, height: 1.5) }
            legendItem("Link, not a credit") {
                Path { p in p.move(to: .zero); p.addLine(to: CGPoint(x: 24, y: 0)) }
                    .stroke(CU.chart2, style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])).frame(width: 24, height: 2)
            }
        }
        .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Key: in your library is in colour with a solid border; not in your library is grey with a dashed border; a solid line is a stated credit; a dashed line is a link that is not a credit.")
    }

    private func legendItem<S: View>(_ text: String, @ViewBuilder _ swatch: () -> S) -> some View {
        HStack(spacing: CU.Space.xs) { swatch(); Text(text) }
    }

    // MARK: List view

    private enum Column { static let name: CGFloat = 220, library: CGFloat = 112, steps: CGFloat = 48 }

    private var list: some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            HStack(spacing: CU.Space.s) {
                Text("Name").frame(width: Column.name, alignment: .leading).padding(.leading, 40)
                Text("Connection to \(graph.centre?.name ?? "the start")").frame(maxWidth: .infinity, alignment: .leading)
                Text("Library").frame(width: Column.library, alignment: .leading)
                Text("Steps").frame(width: Column.steps, alignment: .trailing)
            }
            .font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.textSecondary)
            .padding(.horizontal, CU.Space.s).padding(.bottom, CU.Space.xs)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.separator).frame(height: 1) }
            .accessibilityHidden(true)
            if graph.nodes.isEmpty {
                Text(graph.loading ? "Reading connections…" : "No connections to list yet.").cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(CU.Space.m)
            }
            ForEach(graph.listGroups) { group in
                Text("\(group.title) · \(group.rows.count)").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                    .padding(.horizontal, CU.Space.s).padding(.top, CU.Space.m).padding(.bottom, CU.Space.xs)
                    .accessibilityAddTraits(.isHeader)
                ForEach(group.rows) { row in listRow(row) }
            }
            HStack(spacing: CU.Space.s) {
                Text("Showing \(graph.nodes.count) \(graph.nodes.count == 1 ? "connection" : "connections") · sorted by kind, then steps")
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                Spacer(minLength: 0)
                if graph.nextCursor != nil { Button("Load more") { Task { await graph.loadMore(librarian: librarian) } }.buttonStyle(CapsuleButtonStyle()).disabled(graph.loading) }
            }
            .padding(.top, CU.Space.m)
        }
    }

    private func listRow(_ row: GraphListRow) -> some View {
        let n = row.node
        let picked = n.id == graph.selectedID
        return Button { graph.selectedID = picked ? nil : n.id } label: {
            HStack(spacing: CU.Space.s) {
                HStack(spacing: CU.Space.s) {
                    GraphNodeFace(entity: n.entity, size: 32, library: state.library, hintArtist: graph.centre?.name ?? "", forceOwned: false, ink: CU.text)
                    Text(n.entity.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                }
                .frame(width: Column.name + 40 - CU.Space.s, alignment: .leading)
                Text(row.connection + (n.credit ? "" : " · link, not a credit")).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
                    .lineLimit(1).truncationMode(.tail).frame(maxWidth: .infinity, alignment: .leading)
                Group {
                    if n.entity.owned {
                        HStack(spacing: CU.Space.xs) { Image(systemName: "checkmark.circle").font(CU.Icon.small()); Text("In library") }
                            .font(CU.Font.callout.weighted(.semibold)).foregroundStyle(CU.success)
                    } else { Text("Not in library").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
                }
                .frame(width: Column.library, alignment: .leading)
                Text("\(n.depth)").cuRole(CU.Font.body).monospacedDigit().foregroundStyle(CU.text).frame(width: Column.steps, alignment: .trailing)
            }
            .padding(.horizontal, CU.Space.s).frame(height: 48)
            .background(picked ? CU.accentTint : .clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(n.entity.name). \(row.connection). \(n.entity.owned ? "In library" : "Not in library"). \(n.depth == 1 ? "1 step" : "\(n.depth) steps").")
        .accessibilityAddTraits(picked ? .isSelected : [])
    }

    // MARK: Inspector

    private var inspector: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            if let n = graph.selected { selected(n) } else { idle }
        }
        .padding(CU.Space.m)
        .frame(maxWidth: .infinity, minHeight: 360, alignment: .topLeading)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .environment(\.cuInPanel, true)
        .accessibilityElement(children: .contain)
    }

    private var idle: some View {
        let name = graph.centre?.name ?? graph.startName ?? "Connections"
        let owned = state.library.artist(named: name)
        return VStack(alignment: .leading, spacing: CU.Space.s) {
            Text(name).cuRole(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
            if graph.nodes.isEmpty {
                Text(owned.map { "In your library · \($0.albumCount) \($0.albumCount == 1 ? "album" : "albums")" } ?? "Not in your library")
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            } else {
                Text(graph.summaryLine).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            }
            Text("Choose a person, album, place or label to see how it connects and where each link comes from.")
                .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.vertical, CU.Space.s)
            if !graph.nodes.isEmpty {
                Text("Kinds").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
                ForEach(GraphSector.allCases.filter { (graph.sectorCounts[$0] ?? 0) > 0 }, id: \.self) { sector in
                    HStack {
                        Text(sector.kindsTitle)
                        Spacer()
                        Text("\(graph.sectorCounts[sector] ?? 0)").monospacedDigit()
                    }
                    .font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.text)
                }
            }
            if let cov = graph.coverage {
                Text(cov == "loaded" ? "MusicBrainz data: loaded on the server." : "MusicBrainz data: not on the server yet.")
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
            }
        }
    }

    @ViewBuilder private func selected(_ n: GraphNode) -> some View {
        let isPerson = GraphSector.of(kind: n.entity.type) == .people
        let isAlbum = GraphSector.of(kind: n.entity.type) == .albums
        let artist = isPerson ? state.library.artist(named: n.entity.name) : nil
        let album = isAlbum ? GraphNodeFace.ownedAlbum(n.entity.name, library: state.library) : nil
        HStack(spacing: CU.Space.m) {
            GraphNodeFace(entity: n.entity, size: 44, library: state.library, hintArtist: graph.centre?.name ?? "", forceOwned: false, ink: CU.text)
            VStack(alignment: .leading, spacing: 0) {
                Text(n.entity.name).cuRole(CU.Font.title3).foregroundStyle(CU.text).lineLimit(2).accessibilityAddTraits(.isHeader)
                Text("\(GraphWording.kindWord(n.entity.type)) · \(n.depth == 1 ? "1 step" : "\(n.depth) steps") from \(graph.parentName(of: n) ?? graph.centre?.name ?? "the start")")
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            }
        }
        HStack(spacing: CU.Space.s) {
            if isPerson {
                Button("Re-centre here") { Task { await graph.recentre(on: n, librarian: librarian) } }.buttonStyle(CapsuleButtonStyle(primary: true))
                Button("Open artist") { if let artist { state.open(artist: artist) } }.buttonStyle(CapsuleButtonStyle()).disabled(artist == nil)
            }
            if isAlbum, let album { Button("Open album") { state.open(album: album) }.buttonStyle(CapsuleButtonStyle()) }
        }
        .padding(.top, CU.Space.xs)
        if isPerson, artist == nil {
            Text("No albums under this name in your library, so there is no artist page to open.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
        }
        Text("How they connect · \(n.evidence.count)").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
            .padding(.top, CU.Space.s)
        if n.evidence.isEmpty {
            Text(n.credit ? "The server sent no evidence for this credit." : "A link in the data that is not a credit. The server sent no evidence for it.")
                .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
        }
        ForEach(Array(n.evidence.enumerated()), id: \.offset) { _, e in evidenceCard(e, node: n) }
        let also = graph.alsoOnInLibrary(n)
        if !also.isEmpty {
            Text("Also on, in your library").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
            // F10: the covers come from the walk already read, not from a server total (docs/redesign.md section 5.2).
            Text("Owned albums next to this one in the walk you have read.").cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary)
            HStack(spacing: CU.Space.s) {
                ForEach(also.prefix(5)) { a in
                    let item = GraphNodeFace.ownedAlbum(a.entity.name, library: state.library)
                    Button { if let item { state.open(album: item) } } label: {
                        GraphNodeFace(entity: a.entity, size: 44, library: state.library, hintArtist: graph.centre?.name ?? "", forceOwned: true, ink: CU.text)
                    }
                    .buttonStyle(.plain).accessibilityLabel("\(a.entity.name), in your library")
                }
            }
        }
    }

    private func evidenceCard(_ e: KnowledgeCredit, node n: GraphNode) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            HStack(alignment: .firstTextBaseline) {
                Text(GraphListRow.words(e)).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                Spacer(minLength: CU.Space.s)
                if n.credit {
                    Label("Credit", systemImage: "checkmark").font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.success)
                        .padding(.horizontal, CU.Space.s).frame(height: 24).background(CU.successTint, in: Capsule())
                } else {
                    Label("Link", systemImage: "link").font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.textSecondary)
                        .padding(.horizontal, CU.Space.s).frame(height: 24).background(CU.bgFill, in: Capsule())
                }
            }
            Text(Self.whatItIsOn(e, node: n, parent: graph.parentName(of: n) ?? graph.centre?.name)).cuRole(CU.Font.body).foregroundStyle(CU.text)
            Text(GraphWording.sourceLine(source: e.source, matchQuality: e.matchQuality)).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            if let url = e.sourceURL { Text(url).cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary).lineLimit(1).truncationMode(.middle) }
        }
        .padding(CU.Space.m).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .accessibilityElement(children: .combine)
    }

    /// What the credit is on, in words: the track or scope the server names, then its dates, else who the walk came through.
    static func whatItIsOn(_ e: KnowledgeCredit, node: GraphNode, parent: String?) -> String {
        if let t = e.track, !t.isEmpty { return t }
        if let s = e.scope, !s.isEmpty { return GraphWording.capitalised(s) }
        if let from = e.validFrom, !from.isEmpty { return e.validTo.map { "\(from) to \($0)" } ?? "From \(from)" }
        return "With \(parent ?? "the start")"
    }
}

// MARK: Start field

/// "Start from": a 32 pt field with the chosen artist's photo; typing lists up to six library matches under it (section 5.2).
struct CupertinoStartField: View {
    let state: AppState
    let current: String?
    @State private var text = ""
    @FocusState private var focused: Bool

    private var matches: [ArtistItem] {
        guard !LibrarySearch.fold(text).isEmpty else { return [] }
        return Array(LibrarySearch.artists(state.library.artists, query: text).prefix(6))
    }

    var body: some View {
        HStack(spacing: CU.Space.s) {
            if let current, text.isEmpty { ArtistPhoto(name: current, size: 20) } else { Image(systemName: "magnifyingglass").foregroundStyle(CU.textSecondary).accessibilityHidden(true) }
            TextField(current ?? "Artist name", text: $text).textFieldStyle(.plain).focused($focused)
                .font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.text)
                .onSubmit { if let first = matches.first { pick(first) } }
                .accessibilityLabel("Start from")
            Image(systemName: "chevron.down").font(CU.Icon.small(.semibold)).foregroundStyle(CU.textSecondary).accessibilityHidden(true)
        }
        .padding(.horizontal, CU.Space.s).frame(width: 240, height: 32)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay { RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(focused ? CU.accent : CU.separatorStrong, lineWidth: 1) }
        .overlay {
            if focused { RoundedRectangle(cornerRadius: 8, style: .continuous).inset(by: -2.5).stroke(CU.accent.opacity(0.28), lineWidth: 3) }
        }
        .overlay(alignment: .topLeading) {
            if !matches.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(matches) { a in
                        Button { pick(a) } label: {
                            HStack(spacing: CU.Space.s) {
                                ArtistPhoto(name: a.name, size: 24)
                                Text(a.name).lineLimit(1)
                                Spacer()
                                Text(a.albumCount == 1 ? "1 album" : "\(a.albumCount) albums").font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
                            }
                            .padding(.horizontal, CU.Space.s).frame(height: 32).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.vertical, CU.Space.xs).frame(width: 240)
                .background(CU.content, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).strokeBorder(CU.separatorStrong, lineWidth: 1))
                .shadow(color: CU.shadowInk.opacity(0.16), radius: 12, y: 4)
                .offset(y: 36)
            }
        }
        .zIndex(5)
    }

    private func pick(_ a: ArtistItem) { text = ""; focused = false; Task { await state.loadConnections(for: a) } }
}

extension KnowledgeEntity {
    /// An entity made from a name, for a face drawn before the server has answered (the start artist of a not-loaded walk).
    static func preview(name: String, type: String, owned: Bool) -> KnowledgeEntity {
        let escaped = name.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
        let json = #"{"mbid":"start-\#(abs(name.hashValue))","canonical_name":"\#(escaped)","type":"\#(type)","owned":\#(owned)}"#
        return try! JSONDecoder().decode(KnowledgeEntity.self, from: Data(json.utf8))
    }
}
