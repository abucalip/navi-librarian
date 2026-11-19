import Testing
@testable import DiscairUI

/// D4.2 (`docs/plans/MACOS_DESIGN_DETAILS.md`): capsule buttons in one row share one size variant. The Home marquee's "More"
/// menu is regular (32) beside Get album / Save / Not for me, and the Home radio card's Resume / Stop / Open Radio are regular,
/// so "Resume" matches the Home primary capsules; the Discover row's "More" keeps the small (24) variant beside its small row.
struct D4CapsuleTests {
    @Test func marqueeMoreUsesTheRegularHeight() {
        #expect(CupertinoPickFeedbackMenu.capsuleStyle(marquee: true).size.height == 32)
    }

    @Test func discoverMoreKeepsTheSmallHeight() {
        #expect(CupertinoPickFeedbackMenu.capsuleStyle(marquee: false).size.height == 24)
    }

    @Test func radioCardCapsulesAreRegular() {
        #expect(HomeRadioCardView.capsuleStyle(primary: true).size.height == 32)
        #expect(HomeRadioCardView.capsuleStyle(primary: false).size.height == 32)
    }
}
