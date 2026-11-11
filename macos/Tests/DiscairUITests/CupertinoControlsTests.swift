import Testing
@testable import DiscairUI

/// Redesign M2: the shared vocabulary of `CUStatus` (section 3) and the button sizes of section 4.3.
struct CupertinoControlsTests {
    @Test func statusWordsMatchTheVocabulary() {
        let all: [(CUStatus, String)] = [
            (.connected, "Connected"), (.loaded, "Loaded"), (.done, "Done"), (.paused, "Paused"),
            (.notSetUp, "Not set up"), (.notLoaded, "Not loaded"), (.unknown, "Unknown"),
            (.notUpdating, "Not updating"), (.noAnswer, "No answer"), (.rejected("Token"), "Token rejected"),
        ]
        for (status, word) in all { #expect(status.text == word) }
    }

    @Test func everyStatusHasItsIconAndKind() {
        #expect(CUStatus.connected.symbol == "checkmark.circle" && CUStatus.connected.kind == .success)
        #expect(CUStatus.notUpdating.symbol == "exclamationmark.triangle" && CUStatus.notUpdating.kind == .warning)
        #expect(CUStatus.rejected("Key").symbol == "xmark.circle" && CUStatus.noAnswer.kind == .danger)
        #expect(CUStatus.paused.symbol == "info.circle" && CUStatus.notLoaded.kind == .info)
        #expect(CUStatus.unknown.symbol == "minus" && CUStatus.notSetUp.kind == .neutral)
    }

    @Test func buttonSizesAre40And32And24() {
        #expect(CapsuleButtonStyle(large: true).size.height == 40)
        #expect(CapsuleButtonStyle().size.height == 32)
        #expect(CapsuleButtonStyle(small: true).size.height == 24)
        #expect(CUButtonSize.large.labelSize == 14 && CUButtonSize.regular.labelSize == 13 && CUButtonSize.small.labelSize == 12)
    }

    @Test func buttonPaddingStaysOnTheScaleExceptTheSmallException() {
        #expect(CUButtonSize.large.horizontalPadding == 24)
        #expect(CUButtonSize.regular.horizontalPadding == 16)
        #expect(CUButtonSize.small.horizontalPadding == 12)   // the one documented exception
    }
}
