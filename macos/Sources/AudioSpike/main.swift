import AVFoundation
import DiscairCore
import DiscairNavidrome
import Foundation

// discair-audio-spike: M2 measurements (docs/MACOS_CLIENT_CONTRACT.md section 12).
// Offline tests (eq, crossfade, gapless, device) need nothing and play no sound.
// Library tests need DISCAIR_NAVIDROME_* in the environment; nothing secret is printed.

let usage = """
usage: discair-audio-spike <command>
  offline          eq, crossfade, gapless and device-rate tests (silent)
  device [--switch]   list output rates; --switch tries a rate change and restores it
  samples          find one real song per file type in the library
  formats <id>... [--bitrate N]   download each song (original, mp3, opus) and test decoding
  gap <id> <id>    download two consecutive tracks and test gapless on real files
  partial <id>...  can a half-downloaded file be opened and read?
  smb <relative path>             time tag read, whole-file read and waveform over the SMB mount
"""

let args = Array(CommandLine.arguments.dropFirst())
let work = FileManager.default.temporaryDirectory.appending(path: "discair-audio-spike")
try? FileManager.default.createDirectory(at: work, withIntermediateDirectories: true)

do {
    switch args.first {
    case "offline":
        try eqTest(); print()
        try crossfadeTest(); print()
        try gaplessTest(directory: work); print()
        outputDeviceReport(trySwitch: false)
    case "device":
        outputDeviceReport(trySwitch: args.contains("--switch"))
    case "samples":
        try await samples(client: try makeClient())
    case "formats":
        let client = try makeClient()
        let rate = args.firstIndex(of: "--bitrate").flatMap { Int(args[$0 + 1]) }
        let ids = args.dropFirst().filter { !$0.hasPrefix("--") && Int($0) == nil }
        for id in ids {
            print("Song \(id)")
            for fmt in [nil, TranscodeFormat.mp3, .opus] {
                let file = try await fetch(client: client, id: id, format: fmt, bitRate: fmt == nil ? nil : rate, to: work)
                decode(file, label: fmt?.rawValue ?? "original")
            }
        }
    case "gap":
        let client = try makeClient()
        let ids = Array(args.dropFirst())
        guard ids.count == 2 else { throw SpikeError(usage) }
        let a = try await fetch(client: client, id: ids[0], format: nil, bitRate: nil, to: work)
        let b = try await fetch(client: client, id: ids[1], format: nil, bitRate: nil, to: work)
        try gapTest(a, b)
    case "partial":
        let client = try makeClient()
        for id in args.dropFirst() {
            let file = try await fetch(client: client, id: id, format: nil, bitRate: nil, to: work)
            for kiB in [256, 2048] { partialTest(file, kiB: kiB, directory: work) }
            let opus = try await fetch(client: client, id: id, format: .opus, bitRate: 192, to: work)
            for kiB in [256, 2048] { partialTest(opus, kiB: kiB, directory: work) }
        }
    case "smb":
        guard args.count > 1 else { throw SpikeError(usage) }
        try smbWaveform(relativePath: args.dropFirst().joined(separator: " "))
    default:
        print(usage)
    }
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8)); exit(1)
}
