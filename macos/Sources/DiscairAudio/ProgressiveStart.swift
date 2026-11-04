import Foundation

/// When a song that is still downloading may start playing (contract 12.2). Pure: the download and the engine decide nothing themselves.
///
/// The thresholds are the measured points where `AVAudioFile` opens a truncated copy: MP3 and Ogg Opus at 256 KiB, FLAC only at 2 MiB
/// (its header is large). M4A keeps its index at the end of the file, so it never opens early. Any other suffix, including Vorbis `ogg`
/// and WMA, is not measured and waits for the whole file.
public enum ProgressiveStart {
    /// Bytes that must be on disk before playback may start, or nil when the file must be complete first.
    public static func requiredBytes(suffix: String?) -> Int64? {
        switch (suffix ?? "").lowercased() {
        case "mp3", "opus": return 256 * 1024
        case "flac": return 2 * 1024 * 1024
        default: return nil
        }
    }

    /// True when playback may start now. A complete file always may, whatever its format.
    public static func canStart(suffix: String?, bytesOnDisk: Int64, complete: Bool) -> Bool {
        if complete { return true }
        guard let needed = requiredBytes(suffix: suffix) else { return false }
        return bytesOnDisk >= needed
    }
}
