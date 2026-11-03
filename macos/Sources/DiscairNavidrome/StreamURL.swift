import DiscairCore
import Foundation

/// Maximum bit rates the stream call may ask for, in kbps (ANDROID_PLAYER_CONTRACT 3.1). `nil` means original.
public let allowedBitRates: [Int] = [64, 96, 128, 192, 256, 320]

/// Transcode formats the stream call may ask for. Original is expressed by omitting the parameter.
public enum TranscodeFormat: String, Sendable, CaseIterable {
    case mp3, opus
}

public func isValidSongID(_ id: String) -> Bool {
    (1...128).contains(id.utf8.count) && id.utf8.allSatisfy {
        ($0 >= 0x30 && $0 <= 0x39) || ($0 >= 0x41 && $0 <= 0x5A) || ($0 >= 0x61 && $0 <= 0x7A) || $0 == 0x2D || $0 == 0x5F
    }
}

/// Builds `rest/stream` and `rest/getCoverArt` URLs. These URLs contain a token and a salt: treat them as secrets
/// (never log or print them; pass them through `redactSecrets` if they must appear in text).
/// Only `id`, an allowlisted `maxBitRate` and an allowlisted `format` can be emitted by `streamURL`;
/// values are written from the allowlist, never copied from the caller.
public struct StreamURLBuilder: Sendable {
    private let base: URL
    private let auth: SubsonicAuth

    public init(baseURL: URL, auth: SubsonicAuth) throws {
        self.base = try AddressPolicy.validate(baseURL)
        self.auth = auth
    }

    public enum BuildError: Error, Equatable, Sendable { case invalidID, unsupportedBitRate }

    public func streamURL(songID: String, maxBitRate: Int? = nil, format: TranscodeFormat? = nil) throws -> URL {
        guard isValidSongID(songID) else { throw BuildError.invalidID }
        var extra = [URLQueryItem(name: "id", value: songID)]
        if let requested = maxBitRate {
            guard let allowed = allowedBitRates.first(where: { $0 == requested }) else { throw BuildError.unsupportedBitRate }
            extra.append(URLQueryItem(name: "maxBitRate", value: String(allowed)))
        }
        if let requested = format, let allowed = TranscodeFormat.allCases.first(where: { $0 == requested }) {
            extra.append(URLQueryItem(name: "format", value: allowed.rawValue))
        }
        return build(path: "rest/stream", json: false, extra: extra)
    }

    /// Cover art for an artist, album or song `coverArt` id as Navidrome returns it (for example `al-<id>_<hash>`).
    public func coverArtURL(coverArtID: String, size: Int? = nil) throws -> URL {
        guard isValidCoverArtID(coverArtID) else { throw BuildError.invalidID }
        var extra = [URLQueryItem(name: "id", value: coverArtID)]
        if let size, (16...2000).contains(size) { extra.append(URLQueryItem(name: "size", value: String(size))) }
        return build(path: "rest/getCoverArt", json: false, extra: extra)
    }

    func build(path: String, json: Bool, extra: [URLQueryItem]) -> URL {
        var comps = URLComponents(url: base, resolvingAgainstBaseURL: false)!
        comps.path = (comps.path.hasSuffix("/") ? comps.path : comps.path + "/") + path
        comps.queryItems = auth.queryItems(json: json) + extra
        return comps.url!
    }

    private func isValidCoverArtID(_ id: String) -> Bool { isValidSongID(id) }
}
