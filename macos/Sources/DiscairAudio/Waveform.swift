import AVFoundation
import CryptoKit
import Foundation

/// Waveform peaks for the seek bar (contract section 7). Read from the music folder over SMB only, never over HTTP, and
/// never invented: no readable file means no waveform and the seek bar stays plain.
public enum WaveformReader {
    public static let bins = 1000

    /// 1000 peaks, each 0...1 (the loudest sample of any channel in that slice of the song), from a full decode of the file.
    /// Blocking: call it off the main actor. Returns nil when the file cannot be decoded or `shouldCancel` says stop.
    public static func peaks(of url: URL, bins: Int = WaveformReader.bins, shouldCancel: () -> Bool = { false }) -> [Float]? {
        guard bins > 0, let file = try? AVAudioFile(forReading: url, commonFormat: .pcmFormatFloat32, interleaved: false) else { return nil }
        let frames = Int(file.length)
        guard frames > 0, let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 65_536) else { return nil }
        let per = max(frames / bins, 1)
        var out = [Float](repeating: 0, count: bins)
        var pos = 0
        while pos < frames {
            if shouldCancel() { return nil }
            do { try file.read(into: buffer) } catch { return nil }
            let n = Int(buffer.frameLength)
            if n == 0 { break }
            guard let data = buffer.floatChannelData else { return nil }
            for ch in 0..<Int(buffer.format.channelCount) {
                let p = data[ch]
                for i in 0..<n {
                    let b = min((pos + i) / per, bins - 1)
                    let v = abs(p[i])
                    if v > out[b] { out[b] = v }
                }
            }
            pos += n
        }
        return normalised(out)
    }

    /// Clamps to 0...1 and rejects a silent or empty result (nothing to draw is no waveform, not a flat one).
    static func normalised(_ peaks: [Float]) -> [Float]? {
        let clean = peaks.map { $0.isFinite ? min(max($0, 0), 1) : 0 }
        return (clean.max() ?? 0) > 0 ? clean : nil
    }
}

/// Computed peaks kept on disk so a song never has to be decoded twice: 1000 values of 16 bits, about 2 KB each. File names
/// are a hash of the server user and song id, so a key can never name a path.
public final class WaveformCache: @unchecked Sendable {
    private let root: URL
    private let lock = NSLock()
    private var folder: URL?

    public init(root: URL = WaveformCache.defaultRoot) { self.root = root }

    public static var defaultRoot: URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appending(path: "Discair/waveforms")
    }

    /// Points the cache at one server user (nil: none).
    public func setScope(_ scope: String?) {
        lock.withLock { folder = scope.map { root.appending(path: Self.hash($0)) } }
    }

    private static func hash(_ text: String) -> String {
        SHA256.hash(data: Data(text.utf8)).prefix(10).map { String(format: "%02x", $0) }.joined()
    }

    private func file(_ songID: String) -> URL? {
        lock.withLock { folder }?.appending(path: Self.hash(songID) + ".wave")
    }

    public func peaks(songID: String, bins: Int = WaveformReader.bins) -> [Float]? {
        guard let url = file(songID), let data = try? Data(contentsOf: url), data.count == bins * 2 else { return nil }
        return stride(from: 0, to: data.count, by: 2).map { Float(UInt16(data[$0]) | UInt16(data[$0 + 1]) << 8) / 65_535 }
    }

    public func put(_ peaks: [Float], songID: String) {
        guard let url = file(songID), !peaks.isEmpty else { return }
        var data = Data(capacity: peaks.count * 2)
        for p in peaks {
            let q = UInt16((min(max(p, 0), 1) * 65_535).rounded())
            data.append(UInt8(q & 0xff)); data.append(UInt8(q >> 8))
        }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? data.write(to: url, options: .atomic)
    }

    public func clear() { try? FileManager.default.removeItem(at: root) }
}
