import AVFoundation
import DiscairAudio
import DiscairCore
import DiscairLibrarian
import Foundation

/// S2-2 item 1, the proof: does a live MP3 or AAC stream play, and does the tap give samples? Addresses are never printed.
@MainActor
func liveSpike(args: [String], seconds: Double, volume: Float) async throws {
    var targets: [(label: String, url: URL)] = []
    if args.contains("--relayed") {
        let env = ProcessInfo.processInfo.environment
        guard let a = env["DISCAIR_LIBRARIAN_URL"], let u = env["DISCAIR_LIBRARIAN_USER"], let pw = env["DISCAIR_LIBRARIAN_PASSWORD"] else {
            throw SpikeError("set DISCAIR_LIBRARIAN_URL, DISCAIR_LIBRARIAN_USER and DISCAIR_LIBRARIAN_PASSWORD")
        }
        let client = try LibrarianClient(baseURL: try AddressPolicy.validate(a), credential: Credential(username: u, password: pw))
        try await client.login()
        var wanted = ["mpeg": 1, "aac": 1]
        for s in try await client.radioStations() where s.proxied {
            guard let url = URL(string: s.playableURL, relativeTo: URL(string: a)) else { continue }
            let kind = await contentKind(url)
            if let n = wanted[kind], n > 0 { wanted[kind] = n - 1; targets.append(("relayed \(kind) · \(s.name)", url.absoluteURL)) }
            if wanted.values.allSatisfy({ $0 == 0 }) { break }
        }
        if targets.isEmpty { print("  no relayed station found") }
    }
    for a in args.dropFirst() where a.hasPrefix("http") || a.hasPrefix("file") {
        if let url = URL(string: a) { targets.append((url.isFileURL ? "file" : "url \(await contentKind(url))", url)) }
    }
    for t in targets { await runOne(label: t.label, url: t.url, seconds: seconds, volume: volume) }
}

/// Content type family of the answer ("mpeg", "aac", "other"), from the response headers only.
func contentKind(_ url: URL) async -> String {
    var req = URLRequest(url: url); req.timeoutInterval = 10
    guard let (bytes, resp) = try? await URLSession.shared.bytes(for: req), let http = resp as? HTTPURLResponse else { return "unreachable" }
    _ = bytes
    let type = (http.value(forHTTPHeaderField: "Content-Type") ?? "").lowercased()
    return type.contains("mpeg") ? "mpeg" : type.contains("aac") ? "aac" : "other(\(type))"
}

@MainActor
func runOne(label: String, url: URL, seconds: Double, volume: Float) async {
    print("Live: \(label)")
    let player = LiveStreamPlayer()
    player.volume = volume
    var states: [String] = []
    var levels: [Float] = []
    let start = Date()
    var firstSound: Double?
    player.onState = { states.append("\($0)@\(f(Date().timeIntervalSince(start), 1))s"); if $0 == .playing, firstSound == nil { firstSound = Date().timeIntervalSince(start) } }
    player.onLevel = { levels.append($0) }
    player.start(url: url)
    try? await Task.sleep(for: .seconds(seconds))
    player.stop()
    report("states", states.joined(separator: " → "))
    report("seconds to first sound", firstSound.map { f($0, 1) } ?? "never")
    report("tap samples", player.hasTapSamples ? "yes" : "NO")
    report("level values (15 Hz expected ≈ \(Int(seconds * 15)))", "\(levels.count)")
    if let mx = levels.max() { report("level min / mean / max", "\(f(Double(levels.min()!), 3)) / \(f(Double(levels.reduce(0, +)) / Double(levels.count), 3)) / \(f(Double(mx), 3))") }
    print()
}
