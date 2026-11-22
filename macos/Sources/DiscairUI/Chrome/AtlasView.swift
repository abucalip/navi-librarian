import AppKit
import DiscairLibrarian
import MapKit
import SwiftUI

/// The atlas (Phase 7 client gate): an Apple Maps view with one pin per place that has stated coordinates. A pin grows with
/// the recordings you own made there; a place with none you own is a white pin with a dashed border (the same rule as the
/// connection graph). Close pins cluster into numbered badges and lower-count labels hide first (D7.2). A List switch shows
/// the same places as rows. Nothing is geocoded: no coordinates, no pin.
struct AtlasView: View {
    let state: AppState
    let style: GraphStyle
    var showsInspector = true
    private var atlas: AtlasModel { state.atlas }

    /// Shared Cupertino page horizontal inset (`CU.Space.xl`, D4.4) so the title and map/list align with other pages.
    static let horizontalPadding: CGFloat = CU.Space.xl
    static let inspectorWidth: CGFloat = 290
    /// D7.4: footer legend item spacing and vertical line spacing.
    static let footerItemSpacing: CGFloat = 14
    static let footerLineSpacing: CGFloat = 4

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                header
                if let note = atlas.note { Text(note).foregroundStyle(style.muted).padding(.top, 4) }
                if atlas.showsList { list } else { map }
                footer
            }
            .padding(.horizontal, Self.horizontalPadding)
            if showsInspector {
                AtlasInspector(state: state, style: style)
            }
        }
        .task { await state.loadAtlas() }
    }

    // MARK: Header and footer

    private var header: some View {
        @Bindable var a = atlas
        return HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text("Atlas").font(style.title).lineLimit(1).accessibilityAddTraits(.isHeader)
            Text("places & scenes").font(.system(size: 12, weight: .semibold)).foregroundStyle(style.muted)
            Spacer()
            if atlas.loading { ProgressView().controlSize(.small) }
            CUSegmented([(value: false, label: "Map"), (value: true, label: "List")], selection: $a.showsList, accessibilityName: "View")
            Button("Refresh") { Task { await atlas.load(librarian: state.session?.librarian, force: true) } }
                .buttonStyle(CapsuleButtonStyle(primary: false, small: true)).disabled(atlas.loading)
        }
        .padding(.top, 4)
    }

    private var footer: some View {
        VStack(alignment: .leading, spacing: Self.footerLineSpacing) {
            FlowLayout(spacing: Self.footerItemSpacing, rowSpacing: Self.footerLineSpacing) {
                Label("Owned recordings made here: colour", systemImage: "circle.fill")
                Label("None owned: dashed", systemImage: "circle.dashed")
                Text("Pin size = recordings you own")
                Text("Only places with stated coordinates are pinned")
            }
            if atlas.truncated {
                Text("Showing the first places only.")
            }
        }
        .labelStyle(.titleAndIcon)
        .font(.system(size: 11))
        .foregroundStyle(style.muted)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: Map

    private var map: some View {
        AtlasMapView(
            places: atlas.places,
            region: atlas.region,
            selectedID: atlas.selectedID,
            accentColor: NSColor(style.accent),
            inkColor: NSColor(style.ink),
            labelBackground: NSColor(CU.content).withAlphaComponent(0.85),
            labelTextColor: NSColor(CU.text),
            onSelect: { id in Task { await atlas.select(id, librarian: state.session?.librarian) } }
        )
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .frame(maxWidth: .infinity, minHeight: 420, maxHeight: .infinity)
        .accessibilityLabel("Map of \(atlas.places.count) places")
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

    fileprivate static func coordinates(_ p: AtlasPlace) -> String {
        String(format: "%.2f°%@ %.2f°%@", abs(p.latitude), p.latitude >= 0 ? "N" : "S", abs(p.longitude), p.longitude >= 0 ? "E" : "W")
    }
}

/// Full-height trailing inspector for Atlas, matching the queue panel's glass chrome and toolbar centre line (D5.7).
struct AtlasInspector: View {
    let state: AppState
    let style: GraphStyle
    private var atlas: AtlasModel { state.atlas }

    /// Aligns the single-line 18 pt bold panel title's vertical centre (~11 pt half-height) with `CupertinoToolbar.centreY`.
    static let topPadding: CGFloat = CupertinoToolbar.centreY - 11

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                if let p = atlas.selected { selectedPanel(p) } else { idlePanel }
            }
            .padding(.top, Self.topPadding)
            .padding([.horizontal, .bottom], 18)
        }
        .frame(width: AtlasView.inspectorWidth)
        .frame(maxHeight: .infinity)
        .glassEffect(CU.glass, in: Rectangle())
        .overlay(alignment: .leading) { Rectangle().fill(CU.text.opacity(0.08)).frame(width: 1) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Atlas inspector")
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
        Text("\(AtlasView.coordinates(p)) · \(p.ownedRecordings) of \(p.recordings) recordings owned").font(.system(size: 11)).foregroundStyle(style.muted)
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
                            if let albumsLine = Self.albumLine(for: r.albums) {
                                Text(albumsLine).font(.system(size: 11)).foregroundStyle(style.muted).lineLimit(2)
                            }
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

    /// D7.3: collapses the album line when a recording has no linked albums (or only blank names).
    static func albumLine(for albums: [KnowledgeAlbumLink]) -> String? {
        let names = albums.map { $0.album.name.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
        return names.isEmpty ? nil : names.joined(separator: " · ")
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
}

// MARK: Clustered MapKit view (D7.2)

/// MapKit annotation wrapping one `AtlasPlace` for native clustering and priority-ordered label placement (D7.2).
final class AtlasPlaceAnnotation: NSObject, MKAnnotation {
    let place: AtlasPlace
    @objc dynamic var coordinate: CLLocationCoordinate2D
    var title: String? { place.entity.name }

    init(place: AtlasPlace) {
        self.place = place
        self.coordinate = CLLocationCoordinate2D(latitude: place.latitude, longitude: place.longitude)
    }
}

/// AppKit `MKMapView` wrapper enabling native MapKit clustering (`clusteringIdentifier`), priority-based pin/label
/// collision (`displayPriority` + `AtlasLabelLayout`), and strict in-bounds label clamping (D7.2).
struct AtlasMapView: NSViewRepresentable {
    static let clusterIdentifier = "atlas-place"

    let places: [AtlasPlace]
    let region: MKCoordinateRegion
    let selectedID: String?
    let accentColor: NSColor
    let inkColor: NSColor
    let labelBackground: NSColor
    let labelTextColor: NSColor
    let onSelect: (String) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    func makeNSView(context: Context) -> MKMapView {
        let mapView = MKMapView(frame: .zero)
        let config = MKStandardMapConfiguration(elevationStyle: .flat, emphasisStyle: .muted)
        config.pointOfInterestFilter = .excludingAll
        mapView.preferredConfiguration = config
        mapView.delegate = context.coordinator
        mapView.register(AtlasPinView.self, forAnnotationViewWithReuseIdentifier: AtlasPinView.reuseIdentifier)
        mapView.register(AtlasClusterView.self, forAnnotationViewWithReuseIdentifier: AtlasClusterView.reuseIdentifier)
        context.coordinator.installLabelOverlay(on: mapView)
        context.coordinator.sync(mapView: mapView, parent: self, forceRegion: true)
        return mapView
    }

    func updateNSView(_ mapView: MKMapView, context: Context) {
        context.coordinator.sync(mapView: mapView, parent: self, forceRegion: false)
    }

    @MainActor
    final class Coordinator: NSObject, MKMapViewDelegate {
        var parent: AtlasMapView
        private var lastPlaceIDs: [String] = []
        private var labelOverlay: AtlasLabelOverlayView?

        init(parent: AtlasMapView) { self.parent = parent }

        func installLabelOverlay(on mapView: MKMapView) {
            let overlay = AtlasLabelOverlayView(frame: mapView.bounds)
            overlay.autoresizingMask = [.width, .height]
            mapView.addSubview(overlay)
            labelOverlay = overlay
        }

        func sync(mapView: MKMapView, parent: AtlasMapView, forceRegion: Bool) {
            self.parent = parent
            let placeIDs = parent.places.map(\.id)
            if placeIDs != lastPlaceIDs {
                lastPlaceIDs = placeIDs
                let existing = mapView.annotations.filter { !($0 is MKUserLocation) }
                mapView.removeAnnotations(existing)
                let annotations = parent.places.map { AtlasPlaceAnnotation(place: $0) }
                mapView.addAnnotations(annotations)
                mapView.setRegion(parent.region, animated: false)
            } else if forceRegion {
                mapView.setRegion(parent.region, animated: false)
            }

            // Refresh styling & displayPriority on currently visible annotation views.
            for annotation in mapView.annotations {
                if let placeAnnotation = annotation as? AtlasPlaceAnnotation,
                   let view = mapView.view(for: placeAnnotation) as? AtlasPinView {
                    view.configure(
                        place: placeAnnotation.place,
                        selected: placeAnnotation.place.id == parent.selectedID,
                        accent: parent.accentColor,
                        ink: parent.inkColor
                    )
                } else if let cluster = annotation as? MKClusterAnnotation,
                          let view = mapView.view(for: cluster) as? AtlasClusterView {
                    view.configure(cluster: cluster, accent: parent.accentColor, ink: parent.inkColor)
                }
            }
            updateLabels(on: mapView)
        }

        func mapView(_ mapView: MKMapView, viewFor annotation: any MKAnnotation) -> MKAnnotationView? {
            if let cluster = annotation as? MKClusterAnnotation {
                let view = mapView.dequeueReusableAnnotationView(
                    withIdentifier: AtlasClusterView.reuseIdentifier,
                    for: cluster
                ) as? AtlasClusterView ?? AtlasClusterView(annotation: cluster, reuseIdentifier: AtlasClusterView.reuseIdentifier)
                view.configure(cluster: cluster, accent: parent.accentColor, ink: parent.inkColor)
                return view
            }
            if let placeAnnotation = annotation as? AtlasPlaceAnnotation {
                let view = mapView.dequeueReusableAnnotationView(
                    withIdentifier: AtlasPinView.reuseIdentifier,
                    for: placeAnnotation
                ) as? AtlasPinView ?? AtlasPinView(annotation: placeAnnotation, reuseIdentifier: AtlasPinView.reuseIdentifier)
                view.configure(
                    place: placeAnnotation.place,
                    selected: placeAnnotation.place.id == parent.selectedID,
                    accent: parent.accentColor,
                    ink: parent.inkColor
                )
                return view
            }
            return nil
        }

        func mapView(_ mapView: MKMapView, didSelect view: MKAnnotationView) {
            if let cluster = view.annotation as? MKClusterAnnotation {
                mapView.deselectAnnotation(cluster, animated: false)
                mapView.showAnnotations(cluster.memberAnnotations, animated: true)
                return
            }
            if let placeAnnotation = view.annotation as? AtlasPlaceAnnotation {
                mapView.deselectAnnotation(placeAnnotation, animated: false)
                parent.onSelect(placeAnnotation.place.id)
            }
        }

        func mapView(_ mapView: MKMapView, didAdd views: [MKAnnotationView]) {
            updateLabels(on: mapView)
        }

        func mapViewDidChangeVisibleRegion(_ mapView: MKMapView) {
            updateLabels(on: mapView)
        }

        func mapView(_ mapView: MKMapView, regionDidChangeAnimated animated: Bool) {
            updateLabels(on: mapView)
        }

        func updateLabels(on mapView: MKMapView) {
            guard let overlay = labelOverlay else { return }
            overlay.frame = mapView.bounds
            let bounds = mapView.bounds
            guard bounds.width > 0, bounds.height > 0 else {
                overlay.apply(labels: [], background: parent.labelBackground, textColor: parent.labelTextColor)
                return
            }

            let font = AtlasLabelOverlayView.labelFont
            var candidates: [AtlasLabelCandidate] = []
            var namesByID: [String: String] = [:]

            for annotation in mapView.annotations {
                guard let placeAnnotation = annotation as? AtlasPlaceAnnotation,
                      let view = mapView.view(for: placeAnnotation),
                      !view.isHidden, view.alphaValue > 0.01 else { continue }
                let place = placeAnnotation.place
                let center = mapView.convert(placeAnnotation.coordinate, toPointTo: mapView)
                guard bounds.contains(center) else { continue }
                let pinSize = CGFloat(AtlasGeometry.pinSize(owned: place.ownedRecordings))
                let text = place.entity.name
                let measured = (text as NSString).boundingRect(
                    with: NSSize(width: AtlasLabelOverlayView.maxLabelWidth, height: 18),
                    options: [.usesLineFragmentOrigin, .truncatesLastVisibleLine],
                    attributes: [.font: font]
                ).size
                let labelSize = CGSize(
                    width: min(AtlasLabelOverlayView.maxLabelWidth, ceil(measured.width)) + AtlasLabelOverlayView.horizontalPadding * 2,
                    height: ceil(measured.height) + AtlasLabelOverlayView.verticalPadding * 2
                )
                let priority = AtlasGeometry.displayPriority(
                    owned: place.ownedRecordings,
                    recordings: place.recordings,
                    selected: place.id == parent.selectedID
                ).rawValue
                candidates.append(AtlasLabelCandidate(
                    id: place.id,
                    pinCenter: center,
                    pinSize: pinSize,
                    labelSize: labelSize,
                    priority: priority
                ))
                namesByID[place.id] = text
            }

            let placements = AtlasLabelLayout.place(candidates, in: bounds)
            let visible: [(id: String, text: String, frame: CGRect)] = placements.values
                .filter(\.visible)
                .compactMap { placement in
                    guard let text = namesByID[placement.id] else { return nil }
                    return (placement.id, text, placement.frame)
                }
            overlay.apply(labels: visible, background: parent.labelBackground, textColor: parent.labelTextColor)
        }
    }
}

/// Custom circular pin for an `AtlasPlace`, participating in MapKit clustering and collision priority (D7.2).
final class AtlasPinView: MKAnnotationView {
    static let reuseIdentifier = "AtlasPinView"
    private var owned = false
    private var isSelectedPin = false
    private var pinDiameter: CGFloat = 14
    private var accentColor: NSColor = .controlAccentColor
    private var inkColor: NSColor = .labelColor

    override init(annotation: (any MKAnnotation)?, reuseIdentifier: String?) {
        super.init(annotation: annotation, reuseIdentifier: reuseIdentifier)
        clusteringIdentifier = AtlasMapView.clusterIdentifier
        collisionMode = .circle
        canShowCallout = false
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) not supported") }

    func configure(place: AtlasPlace, selected: Bool, accent: NSColor, ink: NSColor) {
        owned = place.ownedRecordings > 0
        isSelectedPin = selected
        pinDiameter = CGFloat(AtlasGeometry.pinSize(owned: place.ownedRecordings))
        accentColor = accent
        inkColor = ink
        clusteringIdentifier = AtlasMapView.clusterIdentifier
        collisionMode = .circle
        displayPriority = AtlasGeometry.displayPriority(owned: place.ownedRecordings, recordings: place.recordings, selected: selected)
        let canvas = pinDiameter + 12
        frame = NSRect(origin: frame.origin, size: NSSize(width: canvas, height: canvas))
        setAccessibilityRole(.button)
        setAccessibilityLabel("\(place.entity.name), \(place.ownedRecordings) of \(place.recordings) recordings owned")
        needsDisplay = true
    }

    override func draw(_ dirtyRect: NSRect) {
        let inset = (bounds.width - pinDiameter) / 2
        let circleRect = NSRect(x: inset, y: inset, width: pinDiameter, height: pinDiameter)
        let circle = NSBezierPath(ovalIn: circleRect)
        (owned ? accentColor : NSColor.white).setFill()
        circle.fill()

        let stroke = NSBezierPath(ovalIn: circleRect.insetBy(dx: 1, dy: 1))
        stroke.lineWidth = 2
        if !owned {
            stroke.setLineDash([3, 2], count: 2, phase: 0)
        }
        (owned ? NSColor.white : inkColor).setStroke()
        stroke.stroke()

        if isSelectedPin {
            let ring = NSBezierPath(ovalIn: circleRect.insetBy(dx: -3, dy: -3))
            ring.lineWidth = 3
            inkColor.setStroke()
            ring.stroke()
        }
    }
}

/// Numbered circular badge for an `MKClusterAnnotation` grouping close Atlas pins (D7.2).
final class AtlasClusterView: MKAnnotationView {
    static let reuseIdentifier = "AtlasClusterView"
    private var count = 0
    private var hasOwned = false
    private var badgeDiameter: CGFloat = 28
    private var accentColor: NSColor = .controlAccentColor
    private var inkColor: NSColor = .labelColor

    override init(annotation: (any MKAnnotation)?, reuseIdentifier: String?) {
        super.init(annotation: annotation, reuseIdentifier: reuseIdentifier)
        collisionMode = .circle
        displayPriority = .required
        canShowCallout = false
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) not supported") }

    func configure(cluster: MKClusterAnnotation, accent: NSColor, ink: NSColor) {
        let members = cluster.memberAnnotations.compactMap { $0 as? AtlasPlaceAnnotation }
        count = max(cluster.memberAnnotations.count, members.count)
        hasOwned = members.contains { $0.place.ownedRecordings > 0 }
        badgeDiameter = CGFloat(AtlasGeometry.clusterBadgeSize(count: count))
        accentColor = accent
        inkColor = ink
        collisionMode = .circle
        displayPriority = .required
        frame = NSRect(origin: frame.origin, size: NSSize(width: badgeDiameter + 4, height: badgeDiameter + 4))
        setAccessibilityRole(.button)
        setAccessibilityLabel("\(count) places clustered")
        needsDisplay = true
    }

    override func draw(_ dirtyRect: NSRect) {
        let inset = (bounds.width - badgeDiameter) / 2
        let rect = NSRect(x: inset, y: inset, width: badgeDiameter, height: badgeDiameter)
        let circle = NSBezierPath(ovalIn: rect)
        (hasOwned ? accentColor : NSColor.white).setFill()
        circle.fill()

        let border = NSBezierPath(ovalIn: rect.insetBy(dx: 1, dy: 1))
        border.lineWidth = 2
        if !hasOwned {
            border.setLineDash([3, 2], count: 2, phase: 0)
        }
        (hasOwned ? NSColor.white : inkColor).setStroke()
        border.stroke()

        let text = "\(count)" as NSString
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.monospacedDigitSystemFont(ofSize: 11, weight: .bold),
            .foregroundColor: hasOwned ? NSColor.white : inkColor,
        ]
        let size = text.size(withAttributes: attrs)
        text.draw(at: NSPoint(x: rect.midX - size.width / 2, y: rect.midY - size.height / 2), withAttributes: attrs)
    }
}

/// Non-interactive overlay hosting collision-free, map-bounds-clamped pin labels on `MKMapView` (D7.2).
final class AtlasLabelOverlayView: NSView {
    static let labelFont = NSFont.systemFont(ofSize: 10.5, weight: .semibold)
    static let maxLabelWidth: CGFloat = 156
    static let horizontalPadding: CGFloat = 5
    static let verticalPadding: CGFloat = 2

    private var pills: [String: AtlasLabelPillView] = [:]

    override var isFlipped: Bool { superview?.isFlipped ?? true }
    override func hitTest(_ point: NSPoint) -> NSView? { nil }

    func apply(labels: [(id: String, text: String, frame: CGRect)], background: NSColor, textColor: NSColor) {
        let activeIDs = Set(labels.map(\.id))
        for (id, pill) in pills where !activeIDs.contains(id) {
            pill.removeFromSuperview()
            pills.removeValue(forKey: id)
        }
        for item in labels {
            let pill: AtlasLabelPillView
            if let existing = pills[item.id] {
                pill = existing
            } else {
                pill = AtlasLabelPillView()
                addSubview(pill)
                pills[item.id] = pill
            }
            pill.frame = item.frame
            pill.configure(text: item.text, background: background, textColor: textColor)
        }
    }
}

private final class AtlasLabelPillView: NSView {
    private let field = NSTextField(labelWithString: "")

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer?.cornerRadius = 4
        field.font = AtlasLabelOverlayView.labelFont
        field.lineBreakMode = .byTruncatingTail
        field.maximumNumberOfLines = 1
        field.alignment = .center
        addSubview(field)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) not supported") }

    func configure(text: String, background: NSColor, textColor: NSColor) {
        layer?.backgroundColor = background.cgColor
        field.stringValue = text
        field.textColor = textColor
        field.frame = NSRect(
            x: AtlasLabelOverlayView.horizontalPadding,
            y: AtlasLabelOverlayView.verticalPadding,
            width: max(0, bounds.width - AtlasLabelOverlayView.horizontalPadding * 2),
            height: max(0, bounds.height - AtlasLabelOverlayView.verticalPadding * 2)
        )
    }
}
