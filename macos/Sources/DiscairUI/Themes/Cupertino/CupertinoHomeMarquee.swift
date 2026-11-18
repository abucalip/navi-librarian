import DiscairNavidrome
import SwiftUI

// The shelves and the summary line of the "Marquee" Home (`docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md` sections 2 to 3.4).
// Mockups: `docs/design/macos-home-marquee/mockups.html`. The rules and words come from `HomeScreen`; these views draw them.

/// Covers for tiles whose album may not be in the library (a Get, a radio song) or is known only by its Navidrome id.
@MainActor
enum HomeCovers {
    static func placeholder(title: String, artist: String) -> AlbumItem {
        AlbumItem(id: -1, title: title, artist: artist, year: 0, genre: "", format: "", owned: false, hue: LibraryModel.hue(for: title))
    }

    static func item(_ album: NavidromeAlbum) -> AlbumItem { LibraryModel.item(album, index: 0) }
}

/// A shelf's title (17 bold), its subtitle (12, secondary) on the same baseline, and a text button at the trailing edge.
struct HomeShelfHeader: View {
    let title: String
    let subtitle: String
    var buttonTitle: String?
    var action: () -> Void = {}

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
            Text(title).font(.system(size: 17, weight: .bold)).tracking(-0.1).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
            Text(subtitle).cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
            Spacer(minLength: CU.Space.s)
            if let buttonTitle {
                Button(buttonTitle, action: action).buttonStyle(.plain)
                    .font(.system(size: 12, weight: .semibold)).foregroundStyle(CU.accentStrong)
            }
        }
    }
}

/// Six equal columns (three when stacked), 16 apart.
private func shelfColumns(stacked: Bool) -> [GridItem] {
    Array(repeating: GridItem(.flexible(), spacing: CU.Space.m, alignment: .top), count: stacked ? 3 : 6)
}

/// A square cover filling its column, with its title, artist and status line under it. The cover (with the title and the lines) is
/// one button; `accessory` sits over the cover's corner as a separate control (the Play button).
struct HomeShelfTile<Overlay: View, Accessory: View>: View {
    let cover: AlbumItem
    let title: String
    let artist: String
    let status: String
    let statusColor: Color
    var statusIcon: String?
    var label: String
    /// Spoken after the label when the label cannot carry the status (the radio tile: "Get *title* by *artist*").
    var value = ""
    let action: () -> Void
    @ViewBuilder var overlay: Overlay
    @ViewBuilder var accessory: Accessory

    var body: some View {
        ZStack(alignment: .topLeading) {
            Button(action: action) {
                VStack(alignment: .leading, spacing: 2) {
                    CoverView(album: cover)
                        .overlay { overlay }
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                        .shadow(color: CU.shadowInk.opacity(0.16), radius: 12, y: 4)
                        .padding(.bottom, CU.Space.xs)
                    Text(title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                    Text(artist).cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                    HStack(spacing: CU.Space.xs) {
                        if let statusIcon { Image(systemName: statusIcon).font(CU.Font.callout.weighted(.semibold)).accessibilityHidden(true) }
                        Text(status).lineLimit(1)
                    }
                    .cu(CU.Font.callout).fontWeight(.semibold).foregroundStyle(statusColor)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(label).accessibilityValue(value)
            accessory
        }
        .accessibilityElement(children: .contain)
    }
}

extension HomeShelfTile where Accessory == EmptyView {
    init(cover: AlbumItem, title: String, artist: String, status: String, statusColor: Color, statusIcon: String? = nil, label: String,
         value: String = "", action: @escaping () -> Void, @ViewBuilder overlay: () -> Overlay) {
        self.init(cover: cover, title: title, artist: artist, status: status, statusColor: statusColor, statusIcon: statusIcon, label: label,
                  value: value, action: action, overlay: overlay, accessory: { EmptyView() })
    }
}

/// The stage of a Get as a ring over the cover: a quarter, half or three quarters. Decorative; the stage is in the status line.
private struct StageRing: View {
    let fraction: Double
    var body: some View {
        ZStack {
            Circle().stroke(Color.white.opacity(0.28), lineWidth: 6)
            Circle().trim(from: 0, to: fraction).stroke(Color.white, style: StrokeStyle(lineWidth: 6, lineCap: .butt)).rotationEffect(.degrees(-90))
        }
        .padding(3).frame(width: 38, height: 38).accessibilityHidden(true)
    }
}

// MARK: New on the shelf

/// Up to six tiles: Gets in progress, arrived albums not played yet, songs heard on the radio, then recently added albums.
struct HomeShelfSection: View {
    let state: AppState
    let stacked: Bool

    var body: some View {
        let d = state.homeDashboard
        let byID = Dictionary(state.library.allNavidromeAlbums.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        // With Librarian unreachable the Gets and radio songs are unknown, so only recently added albums are shown.
        let arrivals = d.notice == .librarianUnreachable ? [] : d.arrivals
        var dates: [String: Date] = [:]
        for case let .arrived(id, _, _) in arrivals { if let created = byID[id]?.created, let date = HomeScreen.parseDate(created) { dates[id] = date } }
        let tiles = HomeScreen.shelfTiles(arrivals: arrivals, recentlyAdded: d.recentlyAdded.compactMap { byID[$0] }, arrivedDates: dates)
        return VStack(alignment: .leading, spacing: CU.Space.m) {
            HomeShelfHeader(title: "New on the shelf", subtitle: HomeScreen.shelfSubtitle(tiles: tiles), buttonTitle: "All downloads") { state.screen = .downloads }
            if tiles.isEmpty {
                Text("Nothing here yet. Albums you Get appear here while they download, and new albums stay for a while after they arrive.")
                    .font(.system(size: 14)).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            } else {
                LazyVGrid(columns: shelfColumns(stacked: stacked), alignment: .leading, spacing: CU.Space.m) {
                    ForEach(Array(tiles.enumerated()), id: \.offset) { _, tile in view(for: tile, byID: byID) }
                }
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func color(_ role: HomeScreen.StatusRole) -> Color {
        switch role {
        case .warning: CU.warning
        case .danger: CU.danger
        case .accent: CU.accentStrong
        case .secondary: CU.textSecondary
        }
    }

    @ViewBuilder private func view(for tile: HomeScreen.ShelfTile, byID: [String: NavidromeAlbum]) -> some View {
        let status = HomeScreen.shelfStatus(tile, now: Date())
        switch tile {
        case let .job(_, title, artist, stage, failure):
            HomeShelfTile(cover: HomeCovers.placeholder(title: title, artist: artist), title: title, artist: artist, status: status.text,
                          statusColor: color(status.role), statusIcon: failure == nil ? nil : "exclamationmark.triangle.fill",
                          label: HomeScreen.tileLabel(title: title, artist: artist, status: status.text), action: { state.screen = .downloads }) {
                ZStack {
                    Color.black.opacity(failure == nil ? 0.5 : 0.6)
                    if failure != nil {
                        Image(systemName: "exclamationmark.triangle.fill").font(.system(size: 22, weight: .semibold)).foregroundStyle(.white).accessibilityHidden(true)
                    } else if let fraction = HomeScreen.stageFraction(stage) {
                        StageRing(fraction: fraction)
                    }
                }
            }
        case let .arrived(albumID, title, artist, _):
            let item = byID[albumID].map(HomeCovers.item) ?? HomeCovers.placeholder(title: title, artist: artist)
            HomeShelfTile(cover: item, title: title, artist: artist, status: status.text, statusColor: color(status.role),
                          label: HomeScreen.tileLabel(title: title, artist: artist, status: status.text), action: { state.open(album: item) },
                          overlay: { EmptyView() }, accessory: { playButton(item, title: title) })
        case let .radio(playID, title, artist, _):
            radioTile(playID: playID, title: title, artist: artist, base: status)
        case let .added(albumID, title, artist, _):
            let item = byID[albumID].map(HomeCovers.item) ?? HomeCovers.placeholder(title: title, artist: artist)
            HomeShelfTile(cover: item, title: title, artist: artist, status: status.text, statusColor: color(status.role),
                          label: HomeScreen.tileLabel(title: title, artist: artist, status: status.text), action: { state.open(album: item) }, overlay: { EmptyView() })
        }
    }

    /// A song heard on the radio: a click Gets it, and the status line then follows the radio Download states.
    private func radioTile(playID: Int, title: String, artist: String, base: HomeScreen.ShelfStatus) -> some View {
        let download = state.downloadState(playID: playID)
        var text = base.text, role = base.role, icon: String?
        switch download {
        case .working: text = "Downloading…"; role = .warning
        case .done: text = "Get sent"; role = .accent
        case .owned: text = "In your library"; role = .secondary
        case .failed: text = "Failed · " + (state.radioDownloads.sentence(for: playID) ?? "try again"); role = .danger; icon = "exclamationmark.triangle.fill"
        default: break
        }
        return HomeShelfTile(cover: HomeCovers.placeholder(title: title, artist: artist), title: title, artist: artist, status: text,
                             statusColor: color(role), statusIcon: icon, label: "Get \(title) by \(artist)", value: text,
                             action: { Task { await state.radioDownloads.get(playID: playID) } }) {
            VStack {
                HStack {
                    Text("RADIO").font(.system(size: 10, weight: .bold)).tracking(0.7).foregroundStyle(.white)
                        .padding(.horizontal, 7).padding(.vertical, 2).background(Color.black.opacity(0.62), in: RoundedRectangle(cornerRadius: 5, style: .continuous))
                    Spacer(minLength: 0)
                }
                Spacer(minLength: 0)
            }
            .padding(7).accessibilityHidden(true)
        }
    }

    private func playButton(_ item: AlbumItem, title: String) -> some View {
        GeometryReader { g in
            Button { state.playAlbum(item) } label: {
                Image(systemName: "play.fill").font(.system(size: 12, weight: .semibold)).foregroundStyle(Color(red: 0.114, green: 0.114, blue: 0.122))
                    .frame(width: 30, height: 30).background(Color.white.opacity(0.92), in: Circle())
                    .shadow(color: .black.opacity(0.3), radius: 4, y: 2)
            }
            .buttonStyle(.plain).accessibilityLabel("Play \(title)")
            .position(x: g.size.width - 8 - 15, y: g.size.width - 8 - 15)   // 8 in from the cover's bottom right; the cover is square
        }
        .aspectRatio(1, contentMode: .fit)
    }
}

// MARK: Waiting longest

/// Six albums that have waited longest for a play (plan 3.3).
struct HomeWaitingSection: View {
    let state: AppState
    let stacked: Bool

    var body: some View {
        let d = state.homeDashboard
        let byID = Dictionary(state.library.allNavidromeAlbums.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        let albums = (d.shelfLife?.longestUnplayed ?? []).compactMap { byID[$0] }
        let never = { (a: NavidromeAlbum) in (a.playCount ?? 0) == 0 && a.played == nil }
        let allNever = !albums.isEmpty && albums.allSatisfy(never)
        return VStack(alignment: .leading, spacing: CU.Space.m) {
            HomeShelfHeader(title: "Waiting longest", subtitle: HomeScreen.waitingSubtitle(allNeverPlayed: allNever),
                            buttonTitle: (d.neverPlayed ?? 0) > 0 ? "Play something unplayed" : nil) { state.playSomethingUnplayed() }
            if albums.isEmpty {
                Text(d.load == .ready ? "Nothing is waiting. Every album you own has been played." : "Albums you own and have not played yet appear here.")
                    .font(.system(size: 14)).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            } else {
                LazyVGrid(columns: shelfColumns(stacked: stacked), alignment: .leading, spacing: CU.Space.m) {
                    ForEach(albums, id: \.id) { a in
                        let item = HomeCovers.item(a)
                        let caption = HomeScreen.waitingCaption(created: HomeScreen.parseDate(a.created), played: HomeScreen.parseDate(a.played), neverPlayed: never(a)) ?? ""
                        let artist = a.artist ?? "Unknown artist"
                        HomeShelfTile(cover: item, title: a.name, artist: artist, status: caption, statusColor: CU.textSecondary,
                                      label: HomeScreen.tileLabel(title: a.name, artist: artist, status: caption),
                                      action: { state.open(album: item) }, overlay: { EmptyView() })
                    }
                }
            }
        }
        .accessibilityElement(children: .contain)
    }
}

// MARK: Summary line

/// The taste headline and up to four figures, as one line of text (plan 3.4).
struct HomeSummaryLine: View {
    let state: AppState
    let stacked: Bool

    var body: some View {
        let figures = HomeScreen.summaryFigures(state.homeDashboard, now: Date())
        let taste = self.taste
        return VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(CU.separator).frame(height: 1)
            Group {
                if stacked {
                    VStack(alignment: .leading, spacing: CU.Space.s) { if let taste { taste }; figureRow(figures) }
                } else {
                    HStack(alignment: .firstTextBaseline, spacing: CU.Space.m) {
                        if let taste { taste } else { Spacer(minLength: 0) }
                        HStack(spacing: CU.Space.m) { figureButtons(figures) }.fixedSize()
                    }
                }
            }
            .padding(.top, CU.Space.m)
        }
        .accessibilityElement(children: .contain)
    }

    /// The server's headline in quotation marks, only when taste is ready; nothing otherwise (Insights explains the other states).
    private var taste: AnyView? {
        guard case let .ready(headline, _, _, _, _) = HomeScreen.taste(profiles: state.taste.profiles, loaded: state.taste.loaded) else { return nil }
        return AnyView(
            Button { state.screen = .insights } label: {
                Text("“\(headline)”").font(.system(size: 14)).foregroundStyle(CU.text).multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true).frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.plain).accessibilityLabel("Open Insights").accessibilityHint(headline)
        )
    }

    /// Stacked (narrow): the figures wrap below the sentence.
    private func figureRow(_ figures: [HomeScreen.SummaryFigure]) -> some View {
        FlowLayout(spacing: CU.Space.m) { figureButtons(figures) }
    }

    @ViewBuilder private func figureButtons(_ figures: [HomeScreen.SummaryFigure]) -> some View {
        ForEach(Array(figures.enumerated()), id: \.offset) { _, figure in
            Button { open(figure.target) } label: { words(figure.text) }
                .buttonStyle(.plain).accessibilityHint(hint(figure.target))
        }
    }

    /// "1,248 albums": the number in semibold primary, the rest in secondary, with tabular figures.
    private func words(_ text: String) -> some View {
        let number = text.prefix { $0 != " " }
        return HStack(spacing: 0) {
            Text(number).fontWeight(.semibold).foregroundStyle(CU.text)
            Text(text.dropFirst(number.count)).foregroundStyle(CU.textSecondary)
        }
        .font(.system(size: 14)).monospacedDigit().lineLimit(1)
    }

    private func open(_ target: HomeScreen.SummaryTarget) {
        switch target {
        case .library: state.screen = .library
        case .history: state.screen = .history
        case .neverPlayed: state.openNeverPlayedAlbums()
        }
    }

    private func hint(_ target: HomeScreen.SummaryTarget) -> String {
        switch target {
        case .library: "Opens your Library"
        case .history: "Opens History"
        case .neverPlayed: "Opens the albums with no plays"
        }
    }
}
