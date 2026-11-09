import AppKit
import SwiftUI

/// The colour a cover gives the player: its average colour, made a little richer and kept dark enough for white text.
struct ArtworkTint: Equatable {
    var hue: Double
    var saturation: Double
    var brightness: Double

    var color: Color { Color(hue: hue, saturation: saturation, brightness: brightness) }

    /// Averages the image on an 8 by 8 grid. Nil for an image that cannot be read or is nearly transparent.
    static func from(_ image: NSImage) -> ArtworkTint? {
        guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
        let n = 8
        var pixels = [UInt8](repeating: 0, count: n * n * 4)
        let drew = pixels.withUnsafeMutableBytes { buf -> Bool in
            guard let ctx = CGContext(data: buf.baseAddress, width: n, height: n, bitsPerComponent: 8, bytesPerRow: n * 4,
                                      space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            ctx.interpolationQuality = .medium
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: n, height: n))
            return true
        }
        guard drew else { return nil }
        var r = 0.0, g = 0.0, b = 0.0, a = 0.0
        for i in stride(from: 0, to: pixels.count, by: 4) {
            r += Double(pixels[i]); g += Double(pixels[i + 1]); b += Double(pixels[i + 2]); a += Double(pixels[i + 3])
        }
        guard a > 0 else { return nil }
        // Premultiplied sums: dividing by the alpha total gives the average opaque colour.
        return from(red: r / a, green: g / a, blue: b / a)
    }

    /// Richer than the plain average, and dark: brightness stays between 0.28 and 0.5 so white text always reads.
    static func from(red: Double, green: Double, blue: Double) -> ArtworkTint {
        let c = NSColor(srgbRed: red, green: green, blue: blue, alpha: 1)
        var h: CGFloat = 0, s: CGFloat = 0, v: CGFloat = 0
        c.getHue(&h, saturation: &s, brightness: &v, alpha: nil)
        return ArtworkTint(hue: Double(h), saturation: min(1, Double(s) * 1.25 + 0.05), brightness: min(0.5, max(0.28, Double(v) * 0.7)))
    }
}

extension ArtworkStore {
    /// The tint of an owned cover (nil until the image is available or when it cannot be read).
    func tint(coverArt: String) async -> ArtworkTint? {
        guard let image = await image(coverArt: coverArt, px: 300) else { return nil }
        return ArtworkTint.from(image)
    }
}
