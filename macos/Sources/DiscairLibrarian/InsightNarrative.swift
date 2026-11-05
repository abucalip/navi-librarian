import Foundation

/// The "Why?" text of an insight card: one short paragraph written from the numbers and names the card carries, so what
/// the owner reads matches what is on screen. It states facts (a count, a date, a listen total) and never advises.
public enum InsightNarrative {
    public static func why(_ card: InsightCard) -> String {
        let text: String
        switch card.kind {
        case "series_completion": text = series(card)
        case "hidden_canon": text = hiddenCanon(card)
        case "anniversary": text = anniversary(card)
        case "forgotten_gem": text = forgottenGem(card)
        case "blind_spot": text = blindSpot(card)
        default: text = generic(card)
        }
        return text.isEmpty ? generic(card) : text
    }

    // MARK: Per lens

    private static func series(_ c: InsightCard) -> String {
        guard let owned = c.owned ?? num(c, "owned"), let total = c.total ?? num(c, "total") else { return "" }
        let name = c.subject.title ?? c.title
        var s = "\(name) is a series on \(source(c, default: "MusicBrainz")) with \(total) \(plural(total, "release")), and your library holds \(owned) of them."
        let missing = max(total - owned, 0)
        if missing > 0 {
            s += " The \(missing) you do not have \(c.missingRuns.count == 1 ? "form one run" : "fall in \(c.missingRuns.count) runs")"
            let runs = c.missingRuns.map { r -> String in
                let span = r.firstPosition == r.lastPosition ? "position \(r.firstPosition)" : "positions \(r.firstPosition) to \(r.lastPosition)"
                let names = r.labels.isEmpty ? "" : ": " + list(r.labels)
                return span + names
            }
            s += runs.isEmpty ? "." : " (" + runs.joined(separator: "; ") + ")."
        } else {
            s += " Nothing in the series is missing."
        }
        return s
    }

    private static func hiddenCanon(_ c: InsightCard) -> String {
        guard let listens = num(c, "listens") else { return "" }
        let who = [c.subject.title ?? c.title, c.subject.artist.map { "by \($0)" }].compactMap { $0 }.joined(separator: " ")
        let year = (c.subject.year).map { " (\($0))" } ?? ""
        var s = "\(who)\(year) has been listened to \(grouped(listens)) times on \(source(c, default: "ListenBrainz"))."
        if let genre = str(c, "matched_genre") {
            let rank = num(c, "genre_rank")
            s += " It belongs to \(genre), which is " + (rank == 1 ? "your top genre" : rank.map { "number \($0) among your genres" } ?? "one of your top genres") + ", and it is not in your library."
        } else {
            s += " It is not in your library."
        }
        return s
    }

    private static func anniversary(_ c: InsightCard) -> String {
        guard let years = num(c, "years") else { return "" }
        let what = (str(c, "event") ?? "album_release") == "album_release" ? "was released" : "marks " + humanize(str(c, "event") ?? "")
        let who = [c.subject.title ?? c.title, c.subject.artist.map { "by \($0)" }].compactMap { $0 }.joined(separator: " ")
        var s = "\(who) \(what)"
        if let d = str(c, "date"), let pretty = longDate(d) { s += " on \(pretty)" }
        s += ", which is \(years) \(plural(years, "year")) ago today."
        return s
    }

    private static func forgottenGem(_ c: InsightCard) -> String {
        guard let days = num(c, "days_since_last_play") else { return "" }
        let who = [c.subject.title ?? c.title, c.subject.artist.map { "by \($0)" }].compactMap { $0 }.joined(separator: " ")
        var s = "You have not played \(who) for \(span(days))."
        var past: [String] = []
        if let plays = num(c, "play_count") { past.append("played it \(grouped(plays)) \(plural(plays, "time"))") }
        if has(c, "starred") { past.append("starred it") }
        if let r = num(c, "rating") { past.append("rated it \(r) out of 5") }
        if !past.isEmpty { s += " Before that you " + list(past) + "." }
        return s
    }

    private static func blindSpot(_ c: InsightCard) -> String {
        guard let owned = num(c, "owned") ?? c.owned, let total = num(c, "total") ?? c.total else { return "" }
        let set = humanize(str(c, "set_kind") ?? "releases")
        let artist = c.subject.artist ?? c.subject.title ?? c.title
        var s = "\(source(c, default: "MusicBrainz")) lists \(total) \(set) for \(artist), and your library holds \(owned) of them."
        if total > owned { s += " The other \(total - owned) are shown as a comparison, not as a recommendation." }
        return s
    }

    /// For a lens this app does not know yet: every reason in words, so the card still explains itself.
    private static func generic(_ c: InsightCard) -> String {
        let parts = c.reasons.map { r -> String in
            let facts = r.evidence.keys.sorted().map { "\(humanize($0)) \(r.evidence[$0]!.text)" }
            return humanize(r.kind) + (facts.isEmpty ? "" : " (" + facts.joined(separator: ", ") + ")")
        }
        return parts.isEmpty ? "" : "\(c.title) is shown because of " + list(parts) + "."
    }

    // MARK: Helpers

    private static func value(_ c: InsightCard, _ key: String) -> InsightValue? {
        for r in c.reasons { if let v = r.evidence[key], v != .null { return v } }
        return nil
    }
    private static func num(_ c: InsightCard, _ key: String) -> Int? {
        if case .number(let n)? = value(c, key) { return Int(n) }
        return nil
    }
    private static func str(_ c: InsightCard, _ key: String) -> String? {
        if case .string(let s)? = value(c, key), !s.isEmpty { return s }
        return nil
    }
    private static func has(_ c: InsightCard, _ kind: String) -> Bool { c.reasons.contains { $0.kind == kind } }

    private static func source(_ c: InsightCard, default d: String) -> String {
        switch str(c, "source")?.lowercased() {
        case "musicbrainz": "MusicBrainz"
        case "listenbrainz": "ListenBrainz"
        case let s?: humanize(s)
        case nil: d
        }
    }
    static func humanize(_ s: String) -> String { s.replacingOccurrences(of: "_", with: " ") }
    static func plural(_ n: Int, _ word: String) -> String { n == 1 ? word : word + "s" }
    static func list(_ items: [String]) -> String {
        switch items.count {
        case 0: ""
        case 1: items[0]
        case 2: items[0] + " and " + items[1]
        default: items.dropLast().joined(separator: ", ") + " and " + items.last!
        }
    }
    static func grouped(_ n: Int) -> String {
        let f = NumberFormatter(); f.numberStyle = .decimal; f.locale = Locale(identifier: "en_US")
        return f.string(from: NSNumber(value: n)) ?? String(n)
    }
    static func span(_ days: Int) -> String {
        if days < 60 { return "\(days) \(plural(days, "day"))" }
        if days < 730 { let m = days / 30; return "about \(m) months" }
        return "about \(days / 365) years"
    }
    static func longDate(_ iso: String) -> String? {
        let p = DateFormatter(); p.locale = Locale(identifier: "en_US_POSIX"); p.timeZone = TimeZone(identifier: "UTC"); p.dateFormat = "yyyy-MM-dd"
        guard let d = p.date(from: iso) else { return nil }
        let o = DateFormatter(); o.locale = Locale(identifier: "en_GB"); o.timeZone = TimeZone(identifier: "UTC"); o.dateFormat = "d MMMM yyyy"
        return o.string(from: d)
    }
}
