import AppKit
import Foundation
import SwiftUI
import Testing
@testable import DiscairUI

@MainActor
@Suite("Window drag and EQ drag")
struct DragTests {
    @Test func bandHeightMapsToGain() {
        #expect(EQBandDrag.gain(y: 60, trackHeight: 120) == 0)
        #expect(EQBandDrag.gain(y: 0, trackHeight: 120) == 12)
        #expect(EQBandDrag.gain(y: 120, trackHeight: 120) == -12)
        #expect(EQBandDrag.gain(y: -40, trackHeight: 120) == 12)      // dragging past the ends clamps
    }

    @Test func blockedViewDoesNotMoveTheWindowButTheBackgroundDoes() {
        let host = NSHostingView(rootView: ZStack(alignment: .topLeading) {
            Color.clear
            Color.clear.frame(width: 100, height: 100).blocksWindowDrag().padding(20)
        }.frame(width: 400, height: 300))
        let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 400, height: 300), styleMask: [.titled], backing: .buffered, defer: false)
        win.contentView = host
        host.layoutSubtreeIfNeeded()
        let inside = host.hitTest(NSPoint(x: 70, y: 230))
        let outside = host.hitTest(NSPoint(x: 350, y: 30))
        #expect(inside?.mouseDownCanMoveWindow == false)
        #expect(outside?.mouseDownCanMoveWindow != false)
    }
}
