import Foundation

/// One song in the queue: just what playback and the screens need.
public struct QueueItem: Identifiable, Equatable, Sendable, Codable {
    public let id: UUID
    public let songID: String
    public let title: String
    public let artist: String
    public let album: String
    public let albumID: String?
    public let coverArt: String?
    public let duration: Double
    /// File suffix as Navidrome reports it (`flac`, `ogg`...), used to decide whether to ask for a transcode.
    public let suffix: String?
    /// Track and disc number on the album, used to tell a continuous album (gapless) from songs that merely follow each other.
    public let track: Int?
    public let disc: Int?
    /// The path Navidrome reports for the file (the SMB waveform maps it to the Mac's mount). Nil when not known.
    public let path: String?
    /// The song's MusicBrainz recording id when Navidrome reports one. Optional, so queues saved before it existed still load.
    public let mbid: String?

    public init(id: UUID = UUID(), songID: String, title: String, artist: String, album: String = "", albumID: String? = nil,
                coverArt: String? = nil, duration: Double = 0, suffix: String? = nil, track: Int? = nil, disc: Int? = nil, path: String? = nil,
                mbid: String? = nil) {
        self.track = track; self.disc = disc; self.path = path; self.mbid = mbid
        self.id = id; self.songID = songID; self.title = title; self.artist = artist; self.album = album
        self.albumID = albumID; self.coverArt = coverArt; self.duration = duration; self.suffix = suffix
    }
}

public enum RepeatMode: String, Sendable, CaseIterable, Codable { case off, all, one }

/// The play order, with shuffle, repeat, Play next, Add to queue and reorder. Pure logic: it never touches audio.
/// `items` is the list as the owner arranged it; with shuffle on, `order` walks it in a random order that starts at the
/// current song, and turning shuffle off keeps the current song where it is.
public struct PlayQueue: Equatable, Sendable {
    public private(set) var items: [QueueItem] = []
    /// Indexes into `items` in play order.
    private var order: [Int] = []
    /// Position inside `order`; nil when nothing is selected.
    private var cursor: Int?
    public private(set) var shuffle = false
    public var repeatMode: RepeatMode = .off

    public init() {}

    /// What is saved between launches: the list as arranged, which song is current, shuffle and repeat. A shuffled
    /// order is not kept; shuffle starts a new one from the current song.
    public struct Snapshot: Codable, Equatable, Sendable {
        public var items: [QueueItem]
        public var index: Int?
        public var shuffle: Bool
        public var repeatMode: RepeatMode
        public init(items: [QueueItem], index: Int?, shuffle: Bool, repeatMode: RepeatMode) {
            self.items = items; self.index = index; self.shuffle = shuffle; self.repeatMode = repeatMode
        }
    }

    public var snapshot: Snapshot { Snapshot(items: items, index: currentIndex, shuffle: shuffle, repeatMode: repeatMode) }

    public init(snapshot: Snapshot) {
        var g = SystemRandomNumberGenerator()
        self.init()
        guard !snapshot.items.isEmpty else { return }
        set(snapshot.items, startAt: snapshot.index ?? 0, using: &g)
        repeatMode = snapshot.repeatMode
        if snapshot.shuffle { setShuffle(true, using: &g) }
    }

    public var current: QueueItem? { cursor.map { items[order[$0]] } }
    public var currentIndex: Int? { cursor.map { order[$0] } }
    public var isEmpty: Bool { items.isEmpty }

    /// Songs after the current one, in play order (what the Up Next list shows).
    public var upNext: [QueueItem] {
        guard let c = cursor else { return [] }
        return order[(c + 1)...].map { items[$0] }
    }

    /// Songs before the current one, in play order. They stay in the queue after they have played.
    public var played: [QueueItem] {
        guard let c = cursor else { return [] }
        return order[..<c].map { items[$0] }
    }

    /// Goes back to a song that has played, by its position in `played`.
    public mutating func jump(played offset: Int) {
        guard let c = cursor, offset >= 0, offset < c else { return }
        cursor = offset
    }

    /// Replaces the queue and selects `startAt` (an index into `songs`).
    public mutating func set(_ songs: [QueueItem], startAt: Int = 0, using rng: inout some RandomNumberGenerator) {
        items = songs
        guard !songs.isEmpty else { order = []; cursor = nil; return }
        let start = min(max(startAt, 0), songs.count - 1)
        rebuildOrder(current: start, using: &rng)
    }

    public mutating func set(_ songs: [QueueItem], startAt: Int = 0) {
        var g = SystemRandomNumberGenerator()
        set(songs, startAt: startAt, using: &g)
    }

    public mutating func setShuffle(_ on: Bool, using rng: inout some RandomNumberGenerator) {
        guard on != shuffle else { return }
        shuffle = on
        rebuildOrder(current: currentIndex, using: &rng)
    }

    public mutating func setShuffle(_ on: Bool) {
        var g = SystemRandomNumberGenerator()
        setShuffle(on, using: &g)
    }

    private mutating func rebuildOrder(current: Int?, using rng: inout some RandomNumberGenerator) {
        guard let current else { order = Array(items.indices); cursor = nil; return }
        if shuffle {
            let rest = items.indices.filter { $0 != current }.shuffled(using: &rng)
            order = [current] + rest
            cursor = 0
        } else {
            order = Array(items.indices)
            cursor = current
        }
    }

    /// Inserts right after the current song (Play next). With nothing selected it becomes the first song.
    public mutating func playNext(_ song: QueueItem) {
        guard let c = cursor else { items.append(song); order = Array(items.indices); cursor = items.count - 1; return }
        items.append(song)
        order.insert(items.count - 1, at: c + 1)
        if !shuffle { normaliseSequentialOrder() }
    }

    /// Adds at the end of the queue (Add to queue).
    public mutating func append(_ song: QueueItem) {
        items.append(song)
        order.append(items.count - 1)
        if cursor == nil { cursor = order.count - 1 }
    }

    /// Without shuffle the order is the list itself, so an insert must also move the song in `items`.
    private mutating func normaliseSequentialOrder() {
        guard let c = cursor else { return }
        let cur = order[c]
        let inserted = items.removeLast()
        items.insert(inserted, at: cur + 1)
        order = Array(items.indices)
        cursor = cur
    }

    /// Removes a song from Up Next by its position in `upNext`.
    public mutating func removeUpNext(at offset: Int) {
        guard let c = cursor, upNext.indices.contains(offset) else { return }
        let removed = order[c + 1 + offset]
        items.remove(at: removed)
        order = order.enumerated().filter { $0.offset != c + 1 + offset }.map { $0.element > removed ? $0.element - 1 : $0.element }
    }

    /// Moves a song inside Up Next (a button path for reordering, so it never needs a drag).
    public mutating func moveUpNext(from: Int, to: Int) {
        guard let c = cursor, upNext.indices.contains(from), upNext.indices.contains(to), from != to else { return }
        if shuffle {
            let v = order.remove(at: c + 1 + from)
            order.insert(v, at: c + 1 + to)
        } else {
            let cur = order[c]
            let v = items.remove(at: cur + 1 + from)
            items.insert(v, at: cur + 1 + to)
            order = Array(items.indices)
        }
    }

    /// Moves to the next song. `natural` is true when the song ended by itself (Repeat one replays it then).
    /// Returns the new current song, or nil when the queue is finished (the cursor stays on the last song).
    @discardableResult
    public mutating func advance(natural: Bool) -> QueueItem? {
        guard let c = cursor else { return nil }
        if natural && repeatMode == .one { return current }
        if c + 1 < order.count { cursor = c + 1; return current }
        if repeatMode == .all, !order.isEmpty { cursor = 0; return current }
        return nil
    }

    /// Previous song; at the start it stays on the first (the caller restarts the song when it is past a few seconds).
    @discardableResult
    public mutating func back() -> QueueItem? {
        guard let c = cursor else { return nil }
        if c > 0 { cursor = c - 1 } else if repeatMode == .all, order.count > 1 { cursor = order.count - 1 }
        return current
    }

    /// The song that follows the current one when it ends by itself (nil when the queue ends or Repeat one replays).
    public var peekNext: QueueItem? {
        guard let c = cursor, repeatMode != .one else { return nil }
        if c + 1 < order.count { return items[order[c + 1]] }
        if repeatMode == .all, order.count > 1 { return items[order[0]] }
        return nil
    }

    /// Jumps to a song in Up Next by its position there.
    public mutating func jump(upNext offset: Int) {
        guard let c = cursor, upNext.indices.contains(offset) else { return }
        cursor = c + 1 + offset
    }

    /// Empties Up Next; the current song and the songs already played stay.
    public mutating func clearUpNext() {
        guard let c = cursor else { return }
        let keep = order[...c].map { items[$0] }
        items = keep; order = Array(keep.indices); cursor = keep.count - 1
    }

    /// Selects a song by its position in `items`.
    public mutating func select(index: Int) {
        guard items.indices.contains(index), let c = order.firstIndex(of: index) else { return }
        cursor = c
    }
}
