import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct HeroAlignmentTests {
    @Test func albumAndArtistShareTheSameHeroInsetsAndActionRhythm() {
        #expect(CupertinoArtistLayout.heroTopInset == 76)
        #expect(CupertinoArtistLayout.heroLeadingInset == CU.Shell.contentLeading + CU.Space.xl)
        #expect(CupertinoArtistLayout.actionGap == 14)
    }

    @Test func collageTilesOverlapAtEverySharedEdgeAfterPixelRounding() {
        let size = CGSize(width: 1200, height: 356)
        for count in 2...CollageLayout.maxSlots {
            let slots = CollageLayout.slots(count: count)
            let frames = slots.map { CollageLayout.tileFrame(for: $0, in: size, scale: 2) }
            for i in slots.indices {
                for j in slots.indices where j > i {
                    let a = slots[i], b = slots[j]
                    let verticalEdge = abs(a.maxX - b.minX) < 0.0001 || abs(b.maxX - a.minX) < 0.0001
                    let horizontalEdge = abs(a.maxY - b.minY) < 0.0001 || abs(b.maxY - a.minY) < 0.0001
                    let verticalSpan = min(a.maxY, b.maxY) - max(a.minY, b.minY)
                    let horizontalSpan = min(a.maxX, b.maxX) - max(a.minX, b.minX)
                    let sharesEdge = (verticalEdge && verticalSpan > 0) || (horizontalEdge && horizontalSpan > 0)
                    if sharesEdge {
                        let intersection = frames[i].intersection(frames[j])
                        #expect(!intersection.isNull)
                        #expect(intersection.width >= CollageLayout.tileOverlap || intersection.height >= CollageLayout.tileOverlap)
                    }
                }
            }
        }
    }

    @Test func collageTileFrameStaysPixelAligned() {
        let frame = CollageLayout.tileFrame(for: CGRect(x: 0.42, y: 0.58, width: 0.58, height: 0.42),
                                            in: CGSize(width: 1177, height: 353), scale: 2)
        for value in [frame.minX, frame.minY, frame.width - CollageLayout.tileOverlap, frame.height - CollageLayout.tileOverlap] {
            #expect(abs(value * 2 - (value * 2).rounded()) < 0.0001)
        }
    }
}
