import Foundation

/// One line of lyrics. `startMs` is nil for plain lyrics. Lyrics text is copyrighted: it is shown on screen and kept in
/// the local cache, and is never logged or sent anywhere else (ANDROID_LYRICS_CONTRACT.md section 3).
public struct LyricLine: Equatable, Sendable, Codable {
    public let startMs: Int?
    public let text: String
    public init(startMs: Int?, text: String) { self.startMs = startMs; self.text = text }
}

public struct Lyrics: Equatable, Sendable, Codable {
    /// True when every line has a start time and the lines follow the music.
    public let timed: Bool
    public let lines: [LyricLine]
    public init(timed: Bool, lines: [LyricLine]) { self.timed = timed; self.lines = lines }
}

/// One entry of `getLyricsBySongId` (OpenSubsonic `songLyrics`). Unknown fields are ignored.
public struct LyricsEntry: Decodable, Equatable, Sendable {
    public struct Line: Decodable, Equatable, Sendable {
        public let start: Int?
        public let value: String?
        public init(start: Int?, value: String?) { self.start = start; self.value = value }
    }
    public let lang: String?
    public let synced: Bool?
    /// Milliseconds added to every start (may be negative); absent means none.
    public let offset: Int?
    public let line: [Line]?
    public init(lang: String? = nil, synced: Bool? = nil, offset: Int? = nil, line: [Line]? = nil) {
        self.lang = lang; self.synced = synced; self.offset = offset; self.line = line
    }
}

struct LyricsPayload: Decodable {
    struct List: Decodable { let structuredLyrics: [LyricsEntry]? }
    let lyricsList: List?
}

struct ExtensionsPayload: Decodable {
    struct Ext: Decodable { let name: String? }
    let openSubsonicExtensions: [Ext]?
}

/// Choosing and cleaning (ANDROID_LYRICS_CONTRACT.md section 5).
public enum LyricsChooser {
    static let maxLines = 2000
    static let maxLineLength = 500

    /// Prefers a timed entry, then a plain one; within each, the entry in `language` (for example "en"), else the first.
    public static func choose(_ entries: [LyricsEntry], language: String? = nil) -> Lyrics? {
        func pick(_ list: [LyricsEntry]) -> LyricsEntry? {
            if let language, let match = list.first(where: { $0.lang?.lowercased().hasPrefix(language.lowercased()) == true }) { return match }
            return list.first
        }
        let timedEntries = entries.filter { $0.synced == true }
        let plainEntries = entries.filter { $0.synced != true }
        if let e = pick(timedEntries), let l = clean(e, asTimed: true) { return l }
        if let e = pick(plainEntries), let l = clean(e, asTimed: false) { return l }
        return nil
    }

    /// Lyrics that only say the song has none ("[Instrumental]", "♪", "No lyrics"): an instrumental song shows no lyrics.
    static func isPlaceholder(_ lines: [LyricLine]) -> Bool {
        let words = lines.map { $0.text.lowercased().filter { $0.isLetter || $0.isNumber || $0 == " " }.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        let markers: Set<String> = ["instrumental", "instrumental music", "no lyrics", "music", "inst", "instrumental interlude", "solo", "intro", "outro"]
        return words.isEmpty ? lines.allSatisfy { $0.text.unicodeScalars.allSatisfy { !CharacterSet.alphanumerics.contains($0) } } : words.allSatisfy { markers.contains($0) }
    }

    /// A song whose title says it is instrumental has no lyrics, whatever a lyrics service matched to it.
    public static func titleSaysInstrumental(_ title: String?) -> Bool {
        title?.range(of: "instrumental", options: [.caseInsensitive, .diacriticInsensitive]) != nil
    }

    static func text(_ raw: String?) -> String {
        let cleaned = String(String.UnicodeScalarView((raw ?? "").unicodeScalars.filter { !CharacterSet.controlCharacters.contains($0) }))
        return cleaned.count > maxLineLength ? String(cleaned.prefix(maxLineLength)) : cleaned
    }

    static func clean(_ e: LyricsEntry, asTimed: Bool) -> Lyrics? {
        let raw = e.line ?? []
        if asTimed {
            let starts = raw.compactMap(\.start)
            let allEqual = starts.count > 1 && Set(starts).count == 1
            let backwards = starts.count > 1 && Set(starts).count > 1 && starts == starts.sorted(by: >)
            if !allEqual, !backwards {
                let offset = e.offset ?? 0
                let lines = raw.compactMap { l -> LyricLine? in
                    guard let s = l.start, s >= 0 else { return nil }
                    return LyricLine(startMs: max(0, s + offset), text: text(l.value))
                }
                .sorted { ($0.startMs ?? 0) < ($1.startMs ?? 0) }
                .prefix(maxLines)
                if !lines.isEmpty, !isPlaceholder(Array(lines)) { return Lyrics(timed: true, lines: Array(lines)) }
            }
        }
        // Plain, or timed lyrics that do not follow the music.
        let lines = raw.prefix(maxLines).map { LyricLine(startMs: nil, text: text($0.value)) }
        guard lines.contains(where: { !$0.text.isEmpty }), !isPlaceholder(lines) else { return nil }
        return Lyrics(timed: false, lines: Array(lines))
    }
}

/// Which line is current (ANDROID_LYRICS_CONTRACT.md section 6): the last line that started at or before the position.
public enum LyricsTimeline {
    public static func currentIndex(in lines: [LyricLine], positionMs: Int) -> Int? {
        var lo = 0, hi = lines.count - 1, found: Int?
        while lo <= hi {
            let mid = (lo + hi) / 2
            if let s = lines[mid].startMs, s <= positionMs { found = mid; lo = mid + 1 } else { hi = mid - 1 }
        }
        return found
    }
}
