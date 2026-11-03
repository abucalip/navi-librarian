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
        .library(name: "DiscairUI", targets: ["DiscairUI"]),
        .executable(name: "Discair", targets: ["DiscairApp"]),
        .executable(name: "discair-checks", targets: ["DiscairChecks"]),
        .executable(name: "discair-audio-spike", targets: ["AudioSpike"]),
    ],
    targets: [
        .target(name: "DiscairCore"),
        .target(name: "DiscairNavidrome", dependencies: ["DiscairCore"]),
        .target(name: "DiscairLibrarian", dependencies: ["DiscairCore"]),
        .target(
            name: "DiscairUI",
            dependencies: ["DiscairCore", "DiscairNavidrome", "DiscairLibrarian"],
            resources: [.copy("Resources/Fonts")]
        ),
        .executableTarget(name: "DiscairApp", dependencies: ["DiscairUI", "DiscairCore", "DiscairNavidrome", "DiscairLibrarian"]),
        .executableTarget(
            name: "DiscairChecks",
            dependencies: ["DiscairCore", "DiscairNavidrome", "DiscairLibrarian"]
        ),
        // M2 measurement tool (contract section 12). Not shipped in the app.
        .executableTarget(
            name: "AudioSpike",
            dependencies: ["DiscairCore", "DiscairNavidrome"]
        ),
        .testTarget(name: "DiscairUITests", dependencies: ["DiscairUI", "DiscairCore", "DiscairNavidrome", "DiscairLibrarian"]),
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
