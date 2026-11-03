import Foundation
import DiscairCore

/// Recorded bodies from the Android contract fixtures (`android/contract-fixtures/navidrome/`), linked into this test
/// target as `Fixtures`. `xcodebuild` copies the linked files into the test bundle (and its test process may not be
/// allowed to read ~/Desktop); `swift build` copies only the link, so that case reads the source path instead.
func fixtureBody(_ dir: String, _ name: String, file: String = #filePath) throws -> Data {
    let inBundle = Bundle.module.url(forResource: name, withExtension: "json", subdirectory: "Fixtures")
    let root = URL(fileURLWithPath: file).deletingLastPathComponent()
    let url = [inBundle, root.appending(path: "Fixtures/\(name).json")].compactMap { $0 }
        .first { FileManager.default.isReadableFile(atPath: $0.path) }
    guard let url else { throw CocoaError(.fileNoSuchFile) }
    let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
    return try JSONSerialization.data(withJSONObject: (object["response"] as! [String: Any])["body"]!)
}

final class MockTransport: HTTPTransport, @unchecked Sendable {
    typealias Handler = @Sendable (URLRequest) throws -> (Int, Data)
    private let lock = NSLock()
    private var requests: [URLRequest] = []
    private let handler: Handler
    init(_ handler: @escaping Handler) { self.handler = handler }
    var sent: [URLRequest] { lock.withLock { requests } }

    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        lock.withLock { requests.append(request) }
        let (status, data) = try handler(request)
        return (data, HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

func queryValue(_ request: URLRequest, _ name: String) -> String? {
    URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems?.first { $0.name == name }?.value
}
func queryValue(_ url: URL, _ name: String) -> String? {
    URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first { $0.name == name }?.value
}
