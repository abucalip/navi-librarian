import Foundation

/// Liner note of the day (docs/artwork.md, idea 12): one picture of an album on Home, cropped by a fixed rule, with the album
/// revealed on tap. Chosen by day and by type only; taste and play data play no part in the picture.

/// A stable number for a day or a key. Swift's `hashValue` changes between launches, so this uses FNV-1a instead, so the same day
/// always gives the same picture.
public func linerNoteSeed(_ key: String) -> Int {
    var hash: UInt64 = 0xcbf29ce484222325
    for byte in key.utf8 {
        hash ^= UInt64(byte)
        hash = hash &* 0x100000001b3
    }
    return Int(hash % UInt64(Int32.max))
}

/// The local calendar day as `yyyy-MM-dd`, the key the note is chosen for.
public func linerNoteDay(_ date: Date, calendar: Calendar = .current) -> String {
    let c = calendar.dateComponents([.year, .month, .day], from: date)
    return String(format: "%04d-%02d-%02d", c.year ?? 0, c.month ?? 0, c.day ?? 0)
}

/// The release groups to try for a day, in order: the valid, unique ids sorted, rotated by the day's number. The order does not
/// depend on the order the list arrived in (the dashboard shuffles its picks).
public func linerNoteOrder(_ groups: [String], day: String) -> [String] {
    var seen = Set<String>()
    let ids = groups.compactMap { artworkGroupID($0)?.lowercased() }.filter { seen.insert($0).inserted }.sorted()
    guard !ids.isEmpty else { return [] }
    let start = linerNoteSeed(day) % ids.count
    return Array(ids[start...] + ids[..<start])
}

extension ArtworkIndex {
    /// The picture for the day's note: a booklet page, a session or band photo (the same rule as the artist collage) or a label
    /// (Medium). Never a PDF (its preview is not the page), never a Front, Back or other cover. Empty when none exist.
    public func linerNotePicture(day: String) -> ArtworkPicture? {
        var seen = Set<Int>()
        let pool = (bookletImages + images.filter { $0.qualifiesForCollage } + [slotImage("Medium")].compactMap { $0 })
            .filter { !$0.isPDF && seen.insert($0.imageID).inserted }
        guard !pool.isEmpty else { return nil }
        return pool[linerNoteSeed(day) % pool.count]
    }
}
