import Testing
@testable import DiscairUI

@Suite struct HeroCollapseTests {
    typealias L = CupertinoArtistLayout

    @Test func heroShrinksFromFullToCompactAndStops() {
        #expect(L.height(progress: L.progress(offset: 0, reduceMotion: false)) == L.bannerHeight)
        #expect(L.height(progress: L.progress(offset: -40, reduceMotion: false)) == L.bannerHeight)   // overscroll
        #expect(L.height(progress: L.progress(offset: L.span, reduceMotion: false)) == L.compactHeight)
        #expect(L.height(progress: L.progress(offset: 5000, reduceMotion: false)) == L.compactHeight)
        #expect(abs(L.height(progress: L.progress(offset: L.span / 2, reduceMotion: false)) - (L.bannerHeight + L.compactHeight) / 2) < 0.001)
    }

    @Test func reduceMotionSnapsBetweenTheTwoHeights() {
        #expect(L.height(progress: L.progress(offset: L.span * 0.4, reduceMotion: true)) == L.bannerHeight)
        #expect(L.height(progress: L.progress(offset: L.span * 0.6, reduceMotion: true)) == L.compactHeight)
    }
}
