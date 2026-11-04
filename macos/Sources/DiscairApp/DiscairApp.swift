import AppKit
import DiscairCore
import DiscairUI
import SwiftUI

@main
struct DiscairApp: App {
    @State private var state = AppState(
        themeID: ProcessInfo.processInfo.environment["DISCAIR_THEME"].flatMap(ThemeID.init(rawValue:)) ?? .cupertino,
        session: SessionModel(store: ProfileStore(fileURL: SessionModel.defaultStoreURL))
    )

    @State private var updater = UpdaterModel()

    init() {
        // `swift run` starts a bare executable; without this the menu bar stays Terminal's and the Theme menu is not shown.
        NSApplication.shared.setActivationPolicy(.regular)
        NSApplication.shared.activate(ignoringOtherApps: true)
    }

    var body: some Scene {
        Window("Discair", id: "main") {
            RootView(state: state)
                .task { state.share.start(); await state.session?.connect() }
                // Best effort: a Not for me still inside its Undo window is sent before the app quits.
                .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in
                    state.player.restoreOutputRate()
                    Task { await state.acquisition.flush() }
                }
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1280, height: 800)

        // The floating mini player (contract section 10). Opened from Window > Mini Player.
        Window("Mini Player", id: "mini") {
            MiniPlayerView(state: state)
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentSize)
        .defaultSize(width: MiniPlayerView.size.width, height: MiniPlayerView.size.height)
        .commands {
            MiniPlayerCommands()
            UpdateCommands(updater: updater)
            CommandMenu("Theme") {
                ForEach(ThemeID.allCases) { id in
                    Button(ThemeRegistry.theme(id).name) { state.themeID = id }
                        .keyboardShortcut(id == .cupertino ? "1" : "2", modifiers: [.command, .option])
                }
            }
        }
    }
}

/// Window > Mini Player (⌥⌘M) opens the floating player.
struct MiniPlayerCommands: Commands {
    @Environment(\.openWindow) private var openWindow
    var body: some Commands {
        CommandGroup(after: .windowArrangement) {
            Button("Mini Player") { openWindow(id: "mini") }
                .keyboardShortcut("m", modifiers: [.command, .option])
        }
    }
}
