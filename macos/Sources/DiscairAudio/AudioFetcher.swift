import Foundation

/// Brings a song to a local file so `AVAudioFile` can read it (the spike measured about 4 s for a 52 MB FLAC over the LAN).
public protocol AudioFetcher: Sendable {
    func fetch(_ url: URL, suffix: String?) async throws -> URL
}

/// Downloads to the temporary directory. The URL carries the login token, so it is never logged or put in an error.
public struct URLSessionFetcher: AudioFetcher {
    private let directory: URL
    public init(directory: URL = FileManager.default.temporaryDirectory.appending(path: "discair-playback")) { self.directory = directory }

    public func fetch(_ url: URL, suffix: String?) async throws -> URL {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let (tmp, response) = try await URLSession.shared.download(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            try? FileManager.default.removeItem(at: tmp)
            throw AudioError("The server did not send the song.")
        }
        let ext = (suffix?.isEmpty == false ? suffix! : "audio").filter { $0.isLetter || $0.isNumber }
        let dest = directory.appending(path: "\(UUID().uuidString).\(ext)")
        try FileManager.default.moveItem(at: tmp, to: dest)
        return dest
    }

    /// Deletes everything downloaded so far (called at launch and quit).
    public func clear() { try? FileManager.default.removeItem(at: directory) }
}
