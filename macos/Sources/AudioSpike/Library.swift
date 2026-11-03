import AVFoundation
import DiscairCore
import DiscairNavidrome
import Foundation

let smbRoot = "/Volumes/media/library/music"

func makeClient() throws -> NavidromeClient {
    let env = ProcessInfo.processInfo.environment
    guard let url = env["DISCAIR_NAVIDROME_URL"], let user = env["DISCAIR_NAVIDROME_USER"], let pw = env["DISCAIR_NAVIDROME_PASSWORD"] else {
        throw SpikeError("set DISCAIR_NAVIDROME_URL, DISCAIR_NAVIDROME_USER and DISCAIR_NAVIDROME_PASSWORD")
    }
    return try NavidromeClient(baseURL: try AddressPolicy.validate(url), credential: Credential(username: user, password: pw))
}

/// Maps the `path` Navidrome reports to the mounted share. With "Report Real Path" on, Navidrome reports the server's
/// absolute path (for example /music/Artist/Album/01 Song.flac, where /music is the folder inside the Navidrome container): the server music root is swapped for the
/// mount. With it off, Navidrome reports a rebuilt name that matches no file, so this finds nothing.
func localPath(forServerPath path: String) -> String {
    let serverRoot = ProcessInfo.processInfo.environment["DISCAIR_SERVER_MUSIC_ROOT"] ?? "/music"
    if path.hasPrefix(serverRoot + "/") { return smbRoot + path.dropFirst(serverRoot.count) }
    return path.hasPrefix("/") ? path : "\(smbRoot)/\(path)"
}

/// Finds one real song per file type, and a pair of consecutive tracks, from random albums. Prints ids and paths only.
func samples(client: NavidromeClient) async throws {
    print("Samples from the library (ids and relative paths only)")
    var byKind: [String: NavidromeSong] = [:]
    var pair: (NavidromeSong, NavidromeSong)?
    var seen = 0
    for _ in 0..<6 {
        for album in try await client.albumList(.random, size: 40) {
            let songs = try await client.album(id: album.id).songs.sorted { ($0.discNumber ?? 1, $0.track ?? 0) < ($1.discNumber ?? 1, $1.track ?? 0) }
            seen += 1
            for s in songs { if let k = s.suffix?.lowercased(), byKind[k] == nil { byKind[k] = s } }
            if pair == nil, let k = songs.first?.suffix?.lowercased(), k == "flac" || k == "mp3", songs.count >= 4 {
                pair = (songs[1], songs[2])
            }
        }
        if byKind["flac"] != nil && byKind["mp3"] != nil && byKind["opus"] != nil && pair != nil { break }
    }
    report("albums scanned", "\(seen)")
    for (k, s) in byKind.sorted(by: { $0.key < $1.key }) {
        let local = s.path.map { FileManager.default.fileExists(atPath: localPath(forServerPath: $0)) }
        report("\(k)", "id=\(s.id) \(s.bitRate ?? 0) kbps \(s.duration ?? 0)s mounted=\(local.map(String.init) ?? "n/a")")
        if let p = s.path { report("   path", p) }
    }
    if let (a, b) = pair { report("consecutive pair", "ids \(a.id) then \(b.id) (\(a.suffix ?? "?"), tracks \(a.track ?? 0), \(b.track ?? 0))") }
}

/// Downloads a song (original, or a transcode) to a temp file and times it. The URL is never printed.
func fetch(client: NavidromeClient, id: String, format: TranscodeFormat?, bitRate: Int?, to directory: URL) async throws -> URL {
    let url = try client.urls.streamURL(songID: id, maxBitRate: bitRate, format: format)
    var request = URLRequest(url: url); request.timeoutInterval = 120
    let t0 = Date()
    let (bytes, response) = try await URLSession(configuration: .ephemeral).bytes(for: request)
    let ttfb = Date().timeIntervalSince(t0)
    guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw SpikeError("server answered \((response as? HTTPURLResponse)?.statusCode ?? 0)") }
    let type = (response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Type") ?? "?"
    var data = Data(); data.reserveCapacity(Int(max(response.expectedContentLength, 0)))
    var firstChunk: TimeInterval?
    for try await b in bytes { if firstChunk == nil { firstChunk = Date().timeIntervalSince(t0) }; data.append(b) }
    let total = Date().timeIntervalSince(t0)
    let ext = ["audio/flac": "flac", "audio/x-flac": "flac", "audio/mpeg": "mp3", "audio/ogg": "ogg", "application/ogg": "ogg",
               "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/wav": "wav", "audio/x-wav": "wav", "audio/aac": "aac"][type.split(separator: ";")[0].lowercased()] ?? "bin"
    let out = directory.appending(path: "\(id)-\(format?.rawValue ?? "original").\(ext)")
    try data.write(to: out)
    report("fetch \(format?.rawValue ?? "original")\(bitRate.map { " @\($0)" } ?? "")",
           "\(data.count / 1024) KiB, \(type), first byte \(f(ttfb * 1000, 0)) ms, total \(f(total * 1000, 0)) ms (\(f(Double(data.count) * 8 / total / 1e6, 0)) Mbit/s)")
    return out
}

/// Opens a file with AVAudioFile and decodes it fully; reports format and decode speed.
@discardableResult
func decode(_ url: URL, label: String) -> Bool {
    do {
        let file = try AVAudioFile(forReading: url, commonFormat: .pcmFormatFloat32, interleaved: false)
        let fmt = file.processingFormat
        let seconds = Double(file.length) / fmt.sampleRate
        let buf = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: 65_536)!
        let t0 = Date(); var peak: Float = 0
        while file.framePosition < file.length {
            try file.read(into: buf)
            for ch in 0..<Int(fmt.channelCount) { for i in 0..<Int(buf.frameLength) { peak = max(peak, abs(buf.floatChannelData![ch][i])) } }
        }
        let took = Date().timeIntervalSince(t0)
        report("decode \(label)", "OK \(Int(fmt.sampleRate)) Hz \(fmt.channelCount) ch, file format \(file.fileFormat.settings[AVFormatIDKey] ?? "?"), \(f(seconds, 1)) s in \(f(took * 1000, 0)) ms (\(f(seconds / took, 0))x real time), peak \(f(Double(peak), 2))")
        return true
    } catch {
        report("decode \(label)", "FAILED: \((error as NSError).domain) \((error as NSError).code)")
        return false
    }
}

/// SMB: quick tag-sized read, whole-file read, and a 1000-peak waveform from a full decode.
func smbWaveform(relativePath: String) throws {
    let url = URL(fileURLWithPath: "\(smbRoot)/\(relativePath)")
    guard FileManager.default.fileExists(atPath: url.path) else { throw SpikeError("not found under the mount: path mapping or mount is wrong") }
    let size = (try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int) ?? 0
    report("file size", "\(size / 1024) KiB")

    var t0 = Date()
    let handle = try FileHandle(forReadingFrom: url)
    let head = try handle.read(upToCount: 64 * 1024) ?? Data()
    report("first 64 KiB (tag read)", "\(f(Date().timeIntervalSince(t0) * 1000, 0)) ms, \(head.count) bytes")
    try? handle.close()

    t0 = Date()
    let whole = try Data(contentsOf: url)
    let readSec = Date().timeIntervalSince(t0)
    report("whole file read", "\(f(readSec * 1000, 0)) ms (\(f(Double(whole.count) * 8 / readSec / 1e6, 0)) Mbit/s)")

    t0 = Date()
    let file = try AVAudioFile(forReading: url, commonFormat: .pcmFormatFloat32, interleaved: false)
    let frames = Int(file.length), bins = 1000, per = max(frames / bins, 1)
    var peaks = [Float](repeating: 0, count: bins)
    let buf = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 65_536)!
    var pos = 0
    while file.framePosition < file.length {
        try file.read(into: buf)
        let p = buf.floatChannelData![0]
        for i in 0..<Int(buf.frameLength) { let b = min((pos + i) / per, bins - 1); peaks[b] = max(peaks[b], abs(p[i])) }
        pos += Int(buf.frameLength)
    }
    let took = Date().timeIntervalSince(t0)
    report("decode + 1000 peaks (page-cache warm)", "\(f(took * 1000, 0)) ms for \(f(Double(frames) / file.processingFormat.sampleRate, 0)) s of audio; loudest bin \(f(Double(peaks.max() ?? 0), 2))")
}

// MARK: real-track gapless and partial files

func decodeAll(_ url: URL) throws -> (samples: [Float], rate: Double, length: Int64) {
    let file = try AVAudioFile(forReading: url, commonFormat: .pcmFormatFloat32, interleaved: false)
    let buf = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 65_536)!
    var out: [Float] = []
    while file.framePosition < file.length {
        try file.read(into: buf)
        out += UnsafeBufferPointer(start: buf.floatChannelData![0], count: Int(buf.frameLength))
    }
    return (out, file.processingFormat.sampleRate, file.length)
}

/// Two real consecutive tracks: stored silence at both ends, and exact continuity through one player node.
func gapTest(_ a: URL, _ b: URL) throws {
    print("Gapless with two real tracks")
    let da = try decodeAll(a), db = try decodeAll(b)
    func silence(_ x: [Float], rate: Double) -> (lead: Double, trail: Double) {
        let lead = x.firstIndex { abs($0) > 1e-4 } ?? x.count
        let trail = x.reversed().firstIndex { abs($0) > 1e-4 } ?? x.count
        return (Double(lead) / rate * 1000, Double(trail) / rate * 1000)
    }
    let sa = silence(da.samples, rate: da.rate), sb = silence(db.samples, rate: db.rate)
    report("track A frames / rate", "\(da.length) / \(Int(da.rate)) Hz")
    report("track A silence lead / trail (ms)", "\(f(sa.lead, 1)) / \(f(sa.trail, 1))")
    report("track B silence lead / trail (ms)", "\(f(sb.lead, 1)) / \(f(sb.trail, 1))")
    report("stored gap at the join (ms)", f(sa.trail + sb.lead, 1))

    guard da.rate == db.rate else { report("join test", "skipped: different sample rates"); return }
    let fa = try AVAudioFile(forReading: a, commonFormat: .pcmFormatFloat32, interleaved: false)
    let fb = try AVAudioFile(forReading: b, commonFormat: .pcmFormatFloat32, interleaved: false)
    let fmt = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: da.rate, channels: 2, interleaved: false)!
    let engine = AVAudioEngine(), player = AVAudioPlayerNode()
    engine.attach(player); engine.connect(player, to: engine.mainMixerNode, format: fmt)
    player.scheduleFile(fa, at: nil, completionHandler: nil)
    player.scheduleFile(fb, at: nil, completionHandler: nil)
    try engine.enableManualRenderingMode(.offline, format: fmt, maximumFrameCount: 4096)
    try engine.start(); player.play()
    let total = da.samples.count + db.samples.count
    let out = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: 4096)!
    var left: [Float] = []; left.reserveCapacity(total)
    while left.count < total {
        let n = AVAudioFrameCount(min(4096, total - left.count))
        guard try engine.renderOffline(n, to: out) == .success else { break }
        left += UnsafeBufferPointer(start: out.floatChannelData![0], count: Int(out.frameLength))
    }
    engine.stop()
    let expected = da.samples + db.samples
    var maxErr: Float = 0
    for i in 0..<min(left.count, expected.count) { maxErr = max(maxErr, abs(left[i] - expected[i])) }
    report("rendered frames / expected", "\(left.count) / \(expected.count)")
    report("max sample error across the join", String(format: "%.2e", maxErr))
}

/// Can a half-downloaded file be opened and read? Decides whether playback can start before the download ends.
func partialTest(_ source: URL, kiB: Int, directory: URL) {
    let ext = source.pathExtension
    let part = directory.appending(path: "partial.\(ext)")
    guard let all = try? Data(contentsOf: source) else { return }
    try? all.prefix(kiB * 1024).write(to: part)
    do {
        let file = try AVAudioFile(forReading: part, commonFormat: .pcmFormatFloat32, interleaved: false)
        let buf = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 16_384)!
        var frames = 0
        do { while true { try file.read(into: buf); if buf.frameLength == 0 { break }; frames += Int(buf.frameLength) } } catch {}
        let rate = file.processingFormat.sampleRate
        report("\(ext): first \(kiB) KiB of \(all.count / 1024)", "opens; header claims \(f(Double(file.length) / rate, 0)) s; \(f(Double(frames) / rate, 1)) s decodable")
    } catch {
        report("\(ext): first \(kiB) KiB of \(all.count / 1024)", "does not open")
    }
}

// MARK: find and listen

/// Lists albums whose artist or title contains `text` (case and accent insensitive), with song ids on request.
func find(client: NavidromeClient, text: String, songs: Bool) async throws {
    let needle = text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: nil)
    var hits = 0
    for album in try await client.allAlbums() {
        let hay = "\(album.artist ?? "") \(album.name)".folding(options: [.caseInsensitive, .diacriticInsensitive], locale: nil)
        guard hay.contains(needle) else { continue }
        hits += 1
        print("  \(album.artist ?? "?") | \(album.name) | \(album.year.map(String.init) ?? "?") | \(album.songCount ?? 0) songs | album id \(album.id)")
        if songs {
            for s in try await client.album(id: album.id).songs.sorted(by: { ($0.discNumber ?? 1, $0.track ?? 0) < ($1.discNumber ?? 1, $1.track ?? 0) }) {
                print("      \(s.discNumber ?? 1)-\(s.track ?? 0) \(s.title) | \(s.suffix ?? "?") | \(s.duration ?? 0)s | song id \(s.id)")
            }
        }
    }
    if hits == 0 { print("  no album matches \"\(text)\"") }
}

/// Real-time playback of the end of track A into the start of track B, to listen for gaps.
/// `crossfade` 0 means gapless (B queued on the same player node); above 0 is an equal-power crossfade.
func listen(a: URL, b: URL, crossfade: Double, tail: Double, head: Double, volume: Float) async throws {
    let fa = try AVAudioFile(forReading: a), fb = try AVAudioFile(forReading: b)
    let rate = fa.processingFormat.sampleRate
    let startA = max(0, fa.length - AVAudioFramePosition(tail * rate))
    let countA = AVAudioFrameCount(fa.length - startA)
    let countB = AVAudioFrameCount(min(fb.length, AVAudioFramePosition(head * fb.processingFormat.sampleRate)))
    let engine = AVAudioEngine()
    engine.mainMixerNode.outputVolume = volume
    let pa = AVAudioPlayerNode(), pb = AVAudioPlayerNode()
    engine.attach(pa); engine.attach(pb)
    if crossfade <= 0 {
        guard fa.processingFormat.sampleRate == fb.processingFormat.sampleRate, fa.processingFormat.channelCount == fb.processingFormat.channelCount else {
            throw SpikeError("the two tracks differ in sample rate or channels; gapless needs a conversion step")
        }
        engine.connect(pa, to: engine.mainMixerNode, format: fa.processingFormat)
        pa.scheduleSegment(fa, startingFrame: startA, frameCount: countA, at: nil, completionHandler: nil)
        pa.scheduleSegment(fb, startingFrame: 0, frameCount: countB, at: nil, completionHandler: nil)
        try engine.start(); pa.play()
        print("  playing the last \(f(Double(countA) / rate, 0)) s of A, then B, gapless (volume \(f(Double(volume))))")
        try await Task.sleep(for: .seconds(Double(countA) / rate + Double(countB) / fb.processingFormat.sampleRate + 0.5))
    } else {
        engine.connect(pa, to: engine.mainMixerNode, format: fa.processingFormat)
        engine.connect(pb, to: engine.mainMixerNode, format: fb.processingFormat)
        pa.scheduleSegment(fa, startingFrame: startA, frameCount: countA, at: nil, completionHandler: nil)
        pb.scheduleSegment(fb, startingFrame: 0, frameCount: countB, at: nil, completionHandler: nil)
        pb.volume = 0
        try engine.start(); pa.play()
        print("  playing the last \(f(Double(countA) / rate, 0)) s of A with a \(f(crossfade, 1)) s equal-power crossfade into B (volume \(f(Double(volume))))")
        let fadeStart = Double(countA) / rate - crossfade
        var bStarted = false
        while true {
            guard let t = pa.lastRenderTime, let p = pa.playerTime(forNodeTime: t) else { try await Task.sleep(for: .milliseconds(10)); continue }
            let pos = Double(p.sampleTime) / p.sampleRate
            if pos >= Double(countA) / rate { break }
            if pos >= fadeStart {
                if !bStarted { pb.play(); bStarted = true }
                let x = min((pos - fadeStart) / crossfade, 1)
                pa.volume = Float(cos(x * .pi / 2)); pb.volume = Float(sin(x * .pi / 2))
            }
            try await Task.sleep(for: .milliseconds(10))
        }
        pb.volume = 1
        try await Task.sleep(for: .seconds(Double(countB) / fb.processingFormat.sampleRate - crossfade + 0.5))
    }
    engine.stop()
    print("  done")
}

/// How many songs resolve to a file on the mounted share through `localPath`. Prints a few misses (relative paths only).
func mapCheck(client: NavidromeClient, albums wanted: Int) async throws {
    print("Path mapping over the SMB mount (server root \(ProcessInfo.processInfo.environment["DISCAIR_SERVER_MUSIC_ROOT"] ?? "/music"))")
    var found = 0, missing: [String] = [], total = 0, albumsSeen = 0
    while albumsSeen < wanted {
        for album in try await client.albumList(.random, size: min(50, wanted - albumsSeen)) {
            albumsSeen += 1
            for song in try await client.album(id: album.id).songs {
                guard let path = song.path else { continue }
                total += 1
                if FileManager.default.fileExists(atPath: localPath(forServerPath: path)) { found += 1 } else { missing.append(path) }
            }
        }
    }
    report("albums / songs checked", "\(albumsSeen) / \(total)")
    report("found on the share", "\(found) (\(f(100 * Double(found) / Double(max(total, 1)), 1)) %)")
    for m in missing.prefix(8) { report("   missing", m) }
}
