// swift-tools-version: 6.2
import PackageDescription

// Discair for Mac: logic package (contract docs/MACOS_CLIENT_CONTRACT.md, phase M1).
// No third-party dependencies. The app shell (Xcode project) arrives in M4 and depends on these products.
let package = Package(
    name: "Discair",
    platforms: [.macOS(.v26)],
    products: [
        .library(name: "DiscairCore", targets: ["DiscairCore"]),
        .library(name: "DiscairNavidrome", targets: ["DiscairNavidrome"]),
        .library(name: "DiscairLibrarian", targets: ["DiscairLibrarian"]),
        .library(name: "DiscairAudio", targets: ["DiscairAudio"]),
        .library(name: "DiscairUI", targets: ["DiscairUI"]),
        .executable(name: "Discair", targets: ["DiscairApp"]),
        .executable(name: "DiscairWidget", targets: ["DiscairWidget"]),
        .executable(name: "discair-checks", targets: ["DiscairChecks"]),
        .executable(name: "discair-audio-spike", targets: ["AudioSpike"]),
    ],
    dependencies: [
        // Auto-update (contract section 10). Only the app target links it; the libraries stay dependency-free.
        .package(url: "https://github.com/sparkle-project/Sparkle", exact: "2.10.1"),
    ],
    targets: [
        .target(name: "DiscairCore"),
        .target(name: "DiscairNavidrome", dependencies: ["DiscairCore"]),
        .target(name: "DiscairLibrarian", dependencies: ["DiscairCore"]),
        .target(name: "DiscairAudio", dependencies: ["DiscairCore", "DiscairNavidrome"]),
        .target(
            name: "DiscairUI",
            dependencies: ["DiscairCore", "DiscairNavidrome", "DiscairLibrarian", "DiscairAudio"]
        ),
        .executableTarget(name: "DiscairApp", dependencies: ["DiscairUI", "DiscairCore", "DiscairNavidrome", "DiscairLibrarian", .product(name: "Sparkle", package: "Sparkle")]),
        // The Notification Center widget (M6). Built as an app extension: `NSExtensionMain` is the entry point that WidgetKit
        // starts, and `bundle.sh` puts the binary in Discair.app/Contents/PlugIns/DiscairWidget.appex. It reads only DiscairCore.
        .executableTarget(
            name: "DiscairWidget",
            dependencies: ["DiscairCore"],
            swiftSettings: [.unsafeFlags(["-application-extension"])],
            linkerSettings: [.unsafeFlags(["-Xlinker", "-e", "-Xlinker", "_NSExtensionMain", "-Xlinker", "-application_extension"])]
        ),
        .executableTarget(
            name: "DiscairChecks",
            dependencies: ["DiscairCore", "DiscairNavidrome", "DiscairLibrarian"]
        ),
        // M2 measurement tool (contract section 12). Not shipped in the app.
        .executableTarget(
            name: "AudioSpike",
            dependencies: ["DiscairCore", "DiscairNavidrome"]
        ),
        .testTarget(name: "DiscairAudioTests", dependencies: ["DiscairAudio"]),
        .testTarget(name: "DiscairUITests", dependencies: ["DiscairUI", "DiscairAudio", "DiscairCore", "DiscairNavidrome", "DiscairLibrarian"]),
        .testTarget(
            name: "DiscairCoreTests",
            dependencies: ["DiscairCore"]
        ),
        .testTarget(
            name: "DiscairNavidromeTests",
            dependencies: ["DiscairNavidrome", "DiscairCore"],
            resources: [.copy("Fixtures")]
        ),
        .testTarget(
            name: "DiscairLibrarianTests",
            dependencies: ["DiscairLibrarian", "DiscairCore"],
            resources: [.copy("Fixtures")]
        ),
    ],
    swiftLanguageModes: [.v6]
)
