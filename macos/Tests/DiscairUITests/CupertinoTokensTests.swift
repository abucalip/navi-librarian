import Testing
@testable import DiscairUI

/// Section 4.1 and 4.2 of `docs/redesign.md`: the Cupertino tokens and their contrast.
struct CupertinoTokensTests {
    @Test func everyTextAndAccentPairReachesAA() {
        for pair in CU.contrastPairs {
            let ratio = pair.text.contrast(with: pair.ground)
            #expect(ratio >= 4.5, "\(pair.name) is \(ratio.formatted(.number.precision(.fractionLength(2)))):1")
        }
    }

    @Test func oldAccentFailedAAAndNewAccentPasses() {
        // The old accent #FA2D48 measured 3.79:1 on white; the new one is 5.06:1 with a white label.
        let old = CURGB(0xFA2D48)
        #expect(old.contrast(with: CURGB(0xFFFFFF)) < 4.5)
        #expect(CU.accentRGB.contrast(with: CU.contentRGB) >= 4.5)
    }

    @Test func aliasesPointAtTheNewRoles() {
        #expect(CU.accentRGB == CURGB(0xD61F4A))
        #expect(CU.textSecondaryRGB == CURGB(0x636368))   // old `muted` was #6E6E73 at 4.30:1 on fill
        #expect(CU.textRGB == CURGB(0x1D1D1F))
        #expect(CU.bgPanelRGB == CURGB(0xF5F5F7))
        #expect(CU.bgFillRGB == CURGB(0xECECF0))
    }

    @Test func spacingUsesOnlyTheScale() {
        #expect(CU.Space.scale == [4, 8, 16, 24, 32])
    }

    @Test func typeRolesMatchSection42() {
        #expect(CU.Font.largeTitle.size == 34 && CU.Font.largeTitle.lineHeight == 40)
        #expect(CU.Font.heroMetric.size == 44 && CU.Font.heroMetric.lineHeight == 48)
        #expect(CU.Font.body.size == 13 && CU.Font.body.lineHeight == 20 && CU.Font.body.weight == .regular)
        #expect(CU.Font.callout.size == 12 && CU.Font.callout.lineHeight == 18)
        #expect(CU.Font.caption.size == 11 && CU.Font.caption.lineHeight == 16)
        #expect(CU.Font.eyebrow.isCapitals && CU.Font.eyebrow.size == 11)
        #expect(CU.Font.title3.size == 17 && CU.Font.title3.lineHeight == 24)
        #expect(CU.Font.title1.size == 24 && CU.Font.title1.lineHeight == 32)
    }

    @Test func chartTokensMatchSection41() {
        #expect(CU.chart1 == CU.accent)
        #expect(CU.heatRGB.map(\.hex) == [0xECECF0, 0xF6C5D0, 0xEE8FA5, 0xE2537A, 0xD61F4A])
    }
}
