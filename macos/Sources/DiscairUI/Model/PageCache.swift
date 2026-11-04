import CryptoKit
import Foundation

/// The last good answer of each read-only page (Home, album, artist, Songs), kept on disk so the library still opens when
/// the server cannot be reached. One folder per server and user, so another server or login never reads it. File names are
/// a hash of the key, so a key can never name a path. At most 400 files or 20 MB, oldest removed first. Deleted at sign-out.
struct PageCache {
    struct Stamped<Value: Codable>: Codable { var savedAt: Date; var value: Value }
    static let maxFiles = 400
    static let maxBytes = 20_000_000
    let directory: URL
    var now: () -> Date = { .now }

    init(root: URL, scope: String, now: @escaping () -> Date = { .now }) {
        directory = root.appending(path: Self.hash(scope))
        self.now = now
    }

    static var defaultRoot: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appending(path: "Discair/pages")
    }

    private static func hash(_ text: String) -> String {
        SHA256.hash(data: Data(text.utf8)).prefix(10).map { String(format: "%02x", $0) }.joined()
    }

    private func file(_ key: String) -> URL { directory.appending(path: "\(Self.hash(key)).json") }

    func get<Value: Codable>(_ key: String, as: Value.Type = Value.self) -> (value: Value, savedAt: Date)? {
        guard let data = try? Data(contentsOf: file(key)), let s = try? JSONDecoder().decode(Stamped<Value>.self, from: data) else { return nil }
        return (s.value, s.savedAt)
    }

    func put<Value: Codable>(_ key: String, _ value: Value) {
        guard let data = try? JSONEncoder().encode(Stamped(savedAt: now(), value: value)) else { return }
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try? data.write(to: file(key), options: .atomic)
        trim()
    }

    private func trim() {
        let keys: [URLResourceKey] = [.contentModificationDateKey, .fileSizeKey]
        guard let files = try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: keys) else { return }
        var info = files.compactMap { u -> (URL, Date, Int)? in
            guard let v = try? u.resourceValues(forKeys: Set(keys)) else { return nil }
            return (u, v.contentModificationDate ?? .distantPast, v.fileSize ?? 0)
        }.sorted { $0.1 < $1.1 }
        var total = info.reduce(0) { $0 + $1.2 }
        while info.count > Self.maxFiles || total > Self.maxBytes, let oldest = info.first {
            try? FileManager.default.removeItem(at: oldest.0)
            total -= oldest.2
            info.removeFirst()
        }
    }

    /// Sign-out: removes every server's saved pages, not only this one's.
    func clear() { try? FileManager.default.removeItem(at: directory.deletingLastPathComponent()) }
}
