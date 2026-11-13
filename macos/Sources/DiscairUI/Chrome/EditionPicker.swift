import DiscairLibrarian
import SwiftUI

/// A small "N covers" button on the album cover (docs/artwork.md, idea 7), shown only when the album's release group has two or
/// more Front images. It opens a sheet to pick which cover the app uses; the server stores the pick and every screen follows it.
/// Nothing is drawn while the index is pending, empty or failed, and nothing is claimed about the album.
struct EditionPickerButton: View {
    let albumID: String
    let rgid: String?
    let editions: [ArtworkPicture]
    @Binding var showing: Bool

    var body: some View {
        Group {
            if hasEditionChoice(editions), let rgid, !rgid.isEmpty {
                Button { showing = true } label: {
                    Text("\(editions.count) covers")
                        .font(.caption.weight(.medium))
                        .padding(.horizontal, 9).padding(.vertical, 4)
                        .background(.regularMaterial, in: Capsule())
                }
                .buttonStyle(.plain)
                .padding(8)
                .help("Choose a cover")
                .accessibilityLabel("Choose cover, \(editions.count) editions")
            }
        }
    }
}

/// The covers to pick from, each labelled with its edition ("1999 JP CD"; plain text, it is third-party data).
struct EditionPickerSheet: View {
    let albumID: String
    let rgid: String
    let editions: [ArtworkPicture]
    @Environment(\.artwork) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var failed = false

    private var chosen: Int? { store?.choices[albumID] }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Choose a cover").font(.title2.weight(.semibold)).accessibilityAddTraits(.isHeader)
            Text("The cover you pick is used on every screen.").font(.callout).foregroundStyle(.secondary)
            ScrollView {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 120), spacing: 12)], spacing: 12) {
                    ForEach(editions) { picture in
                        let selected = picture.imageID == chosen
                        Button { Task { await pick(picture) } } label: {
                            VStack(spacing: 4) {
                                AlbumPictureView(picture: picture, size: .thumb)
                                    .frame(width: 120, height: 120)
                                    .background(Color.black.opacity(0.08))
                                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.accentColor, lineWidth: selected ? 3 : 0))
                                Text(picture.edition.isEmpty ? "Front" : picture.edition).font(.caption).lineLimit(1)
                            }
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(selected ? "\(picture.label), current cover" : picture.label)
                        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
                    }
                }
            }
            if failed { Text("Could not save the choice. Try again.").font(.callout).foregroundStyle(.red) }
            HStack {
                Button("Use the automatic cover") { Task { await automatic() } }.disabled(chosen == nil)
                Spacer()
                Button("Done") { dismiss() }.keyboardShortcut(.cancelAction)
            }
        }
        .padding(20)
        .frame(width: 520, height: 460)
    }

    private func pick(_ picture: ArtworkPicture) async {
        guard let store else { return }
        if await store.setChoice(albumID: albumID, rgid: rgid, imageID: picture.imageID) { failed = false; dismiss() } else { failed = true }
    }

    private func automatic() async {
        guard let store else { return }
        if await store.clearChoice(albumID: albumID) { failed = false; dismiss() } else { failed = true }
    }
}
