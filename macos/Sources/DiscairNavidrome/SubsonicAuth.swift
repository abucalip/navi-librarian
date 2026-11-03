import CryptoKit
import DiscairCore
import Foundation

/// Subsonic token authentication: `t = md5(password + salt)`. The password is never sent.
/// (MD5 is what the Subsonic protocol defines; it is not used for anything else here.)
public struct SubsonicAuth: Sendable {
    public static let apiVersion = "1.16.1"
    public static let clientName = "discair"

    private let credential: Credential
    private let makeSalt: @Sendable () -> String

    public init(credential: Credential, makeSalt: @escaping @Sendable () -> String = SubsonicAuth.randomSalt) {
        self.credential = credential
        self.makeSalt = makeSalt
    }

    /// 16 hex characters from the system random generator.
    public static func randomSalt() -> String {
        var rng = SystemRandomNumberGenerator()
        return (0..<8).map { _ in String(format: "%02x", UInt8.random(in: .min ... .max, using: &rng)) }.joined()
    }

    public static func token(password: String, salt: String) -> String {
        Insecure.MD5.hash(data: Data((password + salt).utf8)).map { String(format: "%02x", $0) }.joined()
    }

    /// Query items for one request: a fresh salt every call.
    public func queryItems(json: Bool = true) -> [URLQueryItem] {
        let salt = makeSalt()
        var items = [
            URLQueryItem(name: "u", value: credential.username),
            URLQueryItem(name: "t", value: credential.withPassword { Self.token(password: $0, salt: salt) }),
            URLQueryItem(name: "s", value: salt),
            URLQueryItem(name: "v", value: Self.apiVersion),
            URLQueryItem(name: "c", value: Self.clientName),
        ]
        if json { items.append(URLQueryItem(name: "f", value: "json")) }
        return items
    }
}
