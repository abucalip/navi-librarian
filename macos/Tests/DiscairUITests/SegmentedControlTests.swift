import Testing
@testable import DiscairUI

/// D4.1 (`docs/plans/MACOS_DESIGN_DETAILS.md`): four looks converge on one neutral segmented control. The accent stays for the
/// page's one main action; selection is the chip plus the semibold weight, and Night needs a hairline because its drop shadow
/// cannot read on near black.
struct SegmentedControlTests {
    @Test func sizesAndRadiiMatchTheSpecTable() {
        #expect(CUSegmentedSpec.trackRadius == 8)
        #expect(CUSegmentedSpec.chipRadius == 4)
        #expect(CUSegmentedSpec.trackPadding == 2)
        #expect(CUSegmentedSpec.segmentHeight == 24)
        #expect(CUSegmentedSpec.controlBarSegmentHeight == 28)
    }

    @Test func nightUsesAHairlineAndDayUsesTheShadow() {
        #expect(CUSegmentedSpec.chipEdge(isNight: true) == .hairline)
        #expect(CUSegmentedSpec.chipEdge(isNight: false) == .shadow)
    }

    /// Day and Night are inversions: the selected chip is darker than its track at night and lighter by day, on the content
    /// ground and on a panel.
    @Test func selectedChipIsDarkerAtNightAndLighterByDay() {
        #expect(CUPalette.night.content.luminance < CUPalette.night.fill.luminance)
        #expect(CUPalette.night.content.luminance < CUPalette.night.fillOnPanel.luminance)
        #expect(CUPalette.day.content.luminance > CUPalette.day.fill.luminance)
        #expect(CUPalette.day.content.luminance > CUPalette.day.fillOnPanel.luminance)
    }

    @Test func segmentedAndFilterChipLabelsReachAAInBothModes() {
        for p in [CUPalette.day, CUPalette.night] {
            #expect(p.text.contrast(with: p.content) >= 4.5, "selected segment label on its chip")
            #expect(p.textSecondary.contrast(with: p.fill) >= 4.5, "unselected segment label on the track")
            #expect(p.textSecondary.contrast(with: p.fillOnPanel) >= 4.5, "unselected segment label on a panel track")
            #expect(p.content.contrast(with: p.text) >= 4.5, "filter chip label on its inverted ground")
        }
    }
}
