import Foundation

/// A song written to disk as its bytes arrive (contract 12.2). Readers see the file grow. `bytesOnDisk`, `isComplete` and
/// `failure` are safe to read from any thread.
public final class GrowingDownload: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    public let file: URL
    private let lock = NSLock()
    private var written: Int64 = 0
    private var complete = false
    private var failed: String?
    /// Written only on the session's serial queue.
    private var handle: FileHandle?
    private var session: URLSession?
    private var task: URLSessionDataTask?
    /// Called once, on the session queue, when the whole file is on disk. Not called after a failure or `cancel`.
    public var onComplete: ((URL) -> Void)?

    private let configuration: URLSessionConfiguration

    public init(file: URL, configuration: URLSessionConfiguration = .ephemeral) {
        self.file = file
        self.configuration = configuration
        super.init()
    }

    /// Test seam: sets what the download reports, without a transfer.
    func setState(bytes: Int64, complete: Bool, failure: String? = nil) { lock.withLock { written = bytes; self.complete = complete; failed = failure } }

    public var bytesOnDisk: Int64 { lock.withLock { written } }
    public var isComplete: Bool { lock.withLock { complete } }
    public var failure: String? { lock.withLock { failed } }

    /// Starts the transfer. The URL carries the login token, so it is never put in an error.
    public func start(_ url: URL) throws {
        try FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
        guard FileManager.default.createFile(atPath: file.path, contents: nil) else { throw AudioError("The song could not be saved.") }
        handle = try FileHandle(forWritingTo: file)
        let queue = OperationQueue()
        queue.maxConcurrentOperationCount = 1
        let s = URLSession(configuration: configuration, delegate: self, delegateQueue: queue)
        session = s
        let t = s.dataTask(with: url)
        task = t
        t.resume()
    }

    /// Stops the transfer. The file is left for the caller to delete.
    public func cancel() { task?.cancel() }

    private func fail(_ message: String) {
        lock.withLock { if failed == nil, !complete { failed = message } }
    }

    // MARK: URLSessionDataDelegate

    public func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse,
                           completionHandler: @escaping (URLSession.ResponseDisposition) -> Void) {
        if let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) {
            completionHandler(.allow)
        } else {
            fail("The server did not send the song.")
            completionHandler(.cancel)
        }
    }

    public func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard let handle else { return }
        do {
            try handle.write(contentsOf: data)
            lock.withLock { written += Int64(data.count) }
        } catch {
            fail("The song could not be saved.")
            task?.cancel()
        }
    }

    public func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        try? handle?.close()
        handle = nil
        if error == nil, failure == nil {
            lock.withLock { complete = true }
            onComplete?(file)
        } else {
            fail("The song could not be streamed.")
        }
        session.finishTasksAndInvalidate()
        self.session = nil
    }
}
