import Testing
@testable import DiscairAudio

@Suite struct ProgressiveStartTests {
    @Test func mp3AndOpusStartAt256KiB() {
        #expect(ProgressiveStart.requiredBytes(suffix: "mp3") == Int64(256 * 1024))
        #expect(ProgressiveStart.requiredBytes(suffix: "opus") == Int64(256 * 1024))
        #expect(!ProgressiveStart.canStart(suffix: "mp3", bytesOnDisk: 256 * 1024 - 1, complete: false))
        #expect(ProgressiveStart.canStart(suffix: "mp3", bytesOnDisk: 256 * 1024, complete: false))
    }

    @Test func flacNeedsTwoMiB() {
        #expect(!ProgressiveStart.canStart(suffix: "flac", bytesOnDisk: 1024 * 1024, complete: false))
        #expect(ProgressiveStart.canStart(suffix: "flac", bytesOnDisk: 2 * 1024 * 1024, complete: false))
    }

    @Test func m4aWaitsForTheWholeFile() {
        #expect(ProgressiveStart.requiredBytes(suffix: "m4a") == nil)
        #expect(!ProgressiveStart.canStart(suffix: "m4a", bytesOnDisk: 500 * 1024 * 1024, complete: false))
        #expect(ProgressiveStart.canStart(suffix: "m4a", bytesOnDisk: 1, complete: true))
    }

    @Test func unmeasuredFormatsWaitForTheWholeFile() {
        for suffix in ["ogg", "wma", "wav", "aiff", "alac", nil, ""] {
            #expect(!ProgressiveStart.canStart(suffix: suffix, bytesOnDisk: 10 * 1024 * 1024, complete: false))
        }
    }

    @Test func completeFileAlwaysStarts() {
        #expect(ProgressiveStart.canStart(suffix: nil, bytesOnDisk: 0, complete: true))
    }

    @Test func suffixIsCaseInsensitive() {
        #expect(ProgressiveStart.requiredBytes(suffix: "FLAC") == Int64(2 * 1024 * 1024))
        #expect(ProgressiveStart.requiredBytes(suffix: "Mp3") == Int64(256 * 1024))
    }
}
