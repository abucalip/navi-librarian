import Foundation

/// One artist on the Gap radar: the albums the library holds and the ones the Librarian says are missing.
public struct GapArtist: Identifiable, Equatable, Sendable {
    public var id: String { name.lowercased() }
    public let name: String
    /// Albums in the library, oldest first (unknown years last).
    public let owned: [AlbumItem]
    /// Missing albums with a known year come first, then the ones without a year (Librarian picks carry none).
    public let missing: [AlbumItem]

    public var total: Int { owned.count + missing.count }
    /// Share of the known discography the library holds, 0 to 1.
    public var completeness: Double { total == 0 ? 1 : Double(owned.count) / Double(total) }
    public var summary: String { "\(owned.count) of \(total) albums owned" }

    /// First and last known year across owned and missing albums; nil when no album has one.
    public var yearSpan: ClosedRange<Int>? {
        let years = (owned + missing).map(\.year).filter { $0 > 0 }
        guard let lo = years.min(), let hi = years.max() else { return nil }
        return lo...hi
    }
    /// Albums that can sit on the year axis, and missing ones that cannot (year unknown).
    public var dated: [AlbumItem] { (owned + missing).filter { $0.year > 0 }.sorted { ($0.year, $0.title) < ($1.year, $1.title) } }
    public var undatedMissing: [AlbumItem] { missing.filter { $0.year == 0 } }
    public var undatedOwned: [AlbumItem] { owned.filter { $0.year == 0 } }
}

/// Builds the Gap radar list. Pure, so a test can drive it.
public enum GapRadar {
    /// Artists the library holds at least one album of and that have at least one missing album, the biggest gaps
    /// first (most missing, then least complete, then name). Artists are matched without regard to case.
    public static func build(owned: [AlbumItem], missing: [AlbumItem]) -> [GapArtist] {
        func key(_ s: String) -> String { s.lowercased() }
        var ownedBy: [String: [AlbumItem]] = [:]
        var seen = Set<String>()
        for a in owned where seen.insert(key(a.artist) + "|" + key(a.title)).inserted { ownedBy[key(a.artist), default: []].append(a) }
        var missingBy: [String: [AlbumItem]] = [:]
        var seenMissing = Set<String>()
        for m in missing where seenMissing.insert(key(m.artist) + "|" + key(m.title)).inserted { missingBy[key(m.artist), default: []].append(m) }

        let list: [GapArtist] = missingBy.compactMap { k, miss in
            guard let have = ownedBy[k], let first = have.first else { return nil }
            // A pick the library already holds under the same title is not a gap.
            let haveTitles = Set(have.map { key($0.title) })
            let gaps = miss.filter { !haveTitles.contains(key($0.title)) }
            guard !gaps.isEmpty else { return nil }
            func order(_ a: AlbumItem, _ b: AlbumItem) -> Bool {
                if (a.year == 0) != (b.year == 0) { return a.year != 0 }
                return (a.year, a.title) < (b.year, b.title)
            }
            return GapArtist(name: first.artist, owned: have.sorted(by: order), missing: gaps.sorted(by: order))
        }
        return list.sorted {
            if $0.missing.count != $1.missing.count { return $0.missing.count > $1.missing.count }
            if $0.completeness != $1.completeness { return $0.completeness < $1.completeness }
            return $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending
        }
    }

    /// Where a year sits on the axis, 0 (first year) to 1 (last year). One-year spans sit in the middle.
    public static func position(of year: Int, in span: ClosedRange<Int>) -> Double {
        guard span.upperBound > span.lowerBound else { return 0.5 }
        return Double(year - span.lowerBound) / Double(span.upperBound - span.lowerBound)
    }
}
