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

    @Test func theSurfaceNeverMovesTheWindowAndReportsPressDragRelease() throws {
        let view = PointerNSView(frame: NSRect(x: 0, y: 0, width: 200, height: 20))
        #expect(view.mouseDownCanMoveWindow == false)
        #expect(view.acceptsFirstMouse(for: nil))
        var log: [String] = []
        view.onDown = { p, s in log.append("down \(Int(p.x))/\(Int(s.width))") }
        view.onDrag = { p, _ in log.append("drag \(Int(p.x))") }
        view.onUp = { p, _ in log.append("up \(Int(p.x))") }
        let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 200, height: 20), styleMask: [.borderless], backing: .buffered, defer: false)
        win.contentView = view
        func event(_ type: NSEvent.EventType, x: CGFloat) throws -> NSEvent {
            try #require(NSEvent.mouseEvent(with: type, location: NSPoint(x: x, y: 10), modifierFlags: [], timestamp: 0, windowNumber: win.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1))
        }
        view.mouseDown(with: try event(.leftMouseDown, x: 50))
        view.mouseDragged(with: try event(.leftMouseDragged, x: 150))
        view.mouseUp(with: try event(.leftMouseUp, x: 150))
        #expect(log == ["down 50/200", "drag 150", "up 150"])
    }

    @Test func aClickAtAPointOnTheBarMapsToThatFraction() {
        #expect(DragBar.fraction(CGPoint(x: 50, y: 3), CGSize(width: 200, height: 10)) == 0.25)
        #expect(DragBar.fraction(CGPoint(x: -30, y: 3), CGSize(width: 200, height: 10)) == 0)      // dragged past the ends
        #expect(DragBar.fraction(CGPoint(x: 400, y: 3), CGSize(width: 200, height: 10)) == 1)
    }

    /// A draggable row is an AppKit drag source that is not a window-drag area, and its payload is plain text.
    @Test func aDraggableRowCarriesItsIdAndNeverMovesTheWindow() {
        let row = RowDragNSView(frame: NSRect(x: 0, y: 0, width: 200, height: 40))
        row.payload = "abc"
        #expect(row.mouseDownCanMoveWindow == false)
        #expect(row.draggingSession(NSDraggingSession(), sourceOperationMaskFor: .withinApplication) == .move)
    }
}
