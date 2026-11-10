import DiscairLibrarian
import SwiftUI

/// What the owner saw for today's liner note, kept on this Mac so the same note stays up all day: the Home picks reshuffle on
/// each load, so without it the day's album would change. A per-viewer convenience only; nothing reads it back from the server.
struct LinerNoteChoice: Codable, Equatable {
    let day: String
    let rgid: String
    let title: String
    let artist: String

    private static let key = "discair.linerNote.choice"

    static func saved() -> LinerNoteChoice? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(LinerNoteChoice.self, from: data)
    }

    func save() {
        guard let data = try? JSONEncoder().encode(self) else { return }
        UserDefaults.standard.set(data, forKey: Self.key)
    }
}

/// Home's liner note of the day (docs/artwork.md, idea 12): one picture from an album on Home, cropped to a square by a fixed
/// centre rule, with "Which album?" revealing the album on tap. Read-only. Nothing is drawn while loading, when no album on Home
/// has a picture for the day, or when the lookup fails. Theme-neutral for now (one plain style, as the track cards are).
struct LinerNoteCard: View {
    /// The Home albums the note may come from, already filtered by "Not for me".
    let albums: [AlbumItem]
    @Environment(\.artwork) private var store
    @State private var note: Note?
    @State private var revealed = false

    struct Note: Equatable {
        let picture: ArtworkPicture
        let title: String
        let artist: String
    }

    var body: some View {
        // The task sits on the Group so it runs even when there is no note yet; an empty Group takes no space in a stack.
        Group {
            if let note {
                HStack(alignment: .center, spacing: 18) {
                    LinerNotePicture(picture: note.picture)
                    VStack(alignment: .leading, spacing: 6) {
                        Text("LINER NOTE OF THE DAY")
                            .font(.system(size: 11, weight: .bold)).tracking(0.7).foregroundStyle(.secondary)
                        if revealed {
                            Text(note.title).font(.system(size: 20, weight: .semibold)).lineLimit(2)
                            Text(note.artist).foregroundStyle(.secondary).lineLimit(1)
                        }
                        Button(revealed ? "Hide album" : "Which album?") { revealed.toggle() }
                            .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                            .accessibilityHint("Shows the album this picture comes from")
                    }
                    Spacer(minLength: 0)
                }
                .padding(14)
                .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                .padding(.bottom, 14)
                .accessibilityElement(children: .contain)
            }
        }
        .task(id: taskKey) { await load() }
    }

    /// Reloads when the day changes or the Home albums change.
    private var taskKey: String {
        let groups = albums.compactMap { artworkGroupID($0.releaseGroupMBID)?.lowercased() }.sorted().joined(separator: ",")
        return "\(linerNoteDay(Date()))|\(groups)"
    }

    private func load() async {
        guard let store else { return }
        let day = linerNoteDay(Date())
        // Today's note is kept: the saved album is tried first, and the Home albums only when it has no picture.
        if let saved = LinerNoteChoice.saved(), saved.day == day {
            switch await store.artworkIndex(rgid: saved.rgid, release: nil) {
            case .ready(let index):
                if let picture = index.linerNotePicture(day: day), !Task.isCancelled {
                    note = Note(picture: picture, title: saved.title, artist: saved.artist); return
                }
            default:
                // Still building or failed: show nothing now and ask again on the next load (never a stored "no picture").
                note = nil; return
            }
        }
        var byGroup: [String: AlbumItem] = [:]
        for album in albums {
            if let rgid = artworkGroupID(album.releaseGroupMBID)?.lowercased(), byGroup[rgid] == nil { byGroup[rgid] = album }
        }
        // At most three lookups a day; each unbuilt index starts its own background build (docs/artwork.md, idea 12).
        for rgid in linerNoteOrder(Array(byGroup.keys), day: day).prefix(3) {
            guard let album = byGroup[rgid] else { continue }
            guard case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else { continue }
            if let picture = index.linerNotePicture(day: day) {
                LinerNoteChoice(day: day, rgid: rgid, title: album.title, artist: album.artist).save()
                note = Note(picture: picture, title: album.title, artist: album.artist)
                return
            }
        }
        note = nil
    }
}

/// The picture cut to a square by a fixed centre crop (no face detection): it fills the square and the edges are clipped.
private struct LinerNotePicture: View {
    let picture: ArtworkPicture
    @Environment(\.artwork) private var store
    @State private var image: NSImage?

    var body: some View {
        ZStack {
            if let image { Image(nsImage: image).resizable().scaledToFill() }
        }
        .frame(width: 120, height: 120)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .accessibilityLabel(picture.label)
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: .display)
        }
    }
}
