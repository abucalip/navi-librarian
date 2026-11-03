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
        .executable(name: "discair-checks", targets: ["DiscairChecks"]),
    ],
    targets: [
        .target(name: "DiscairCore"),
        .target(name: "DiscairNavidrome", dependencies: ["DiscairCore"]),
        .target(name: "DiscairLibrarian", dependencies: ["DiscairCore"]),
        .executableTarget(
            name: "DiscairChecks",
            dependencies: ["DiscairCore", "DiscairNavidrome", "DiscairLibrarian"]
        ),
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
