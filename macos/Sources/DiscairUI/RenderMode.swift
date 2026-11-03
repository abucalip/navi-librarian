/// Test-only switches. The app never sets these.
public enum RenderMode {
    /// Set by screenshot tests: glass tints make an offscreen `NSHostingView` render blank, so they are skipped there.
    nonisolated(unsafe) public static var offscreenScreenshot = false
}
