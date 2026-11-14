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
                .onAppear { AppIcon.apply(state.themeID) }
                .onChange(of: state.themeID) { _, id in AppIcon.apply(id) }
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
            CommandPaletteCommands(state: state)
            // Discair has no documents or text editing, so the Edit menu keeps only the command palette.
            CommandGroup(replacing: .undoRedo) {}
            CommandGroup(replacing: .pasteboard) {}
            PlaybackCommands(state: state)
            PathsCommands(state: state)
            UpdateCommands(updater: updater)
        }
    }
}

/// The Dock icon follows the theme. The icons ship in the app bundle (`Packaging/Icons`); a bare `swift run` has none, so the
/// default icon stays.
enum AppIcon {
    @MainActor static func apply(_ id: ThemeID) {
        let name = "Discair-" + id.rawValue.capitalized
        guard let url = Bundle.main.url(forResource: name, withExtension: "icns"), let image = NSImage(contentsOf: url) else { return }
        NSApplication.shared.applicationIconImage = image
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

/// Edit > Command Palette (⌘K).
struct CommandPaletteCommands: Commands {
    let state: AppState
    var body: some Commands {
        CommandGroup(replacing: .textEditing) {
            Button("Command Palette") { state.palette.toggle() }
                .keyboardShortcut("k", modifiers: .command)
        }
    }
}

/// Controls > Stations (the first nine favourites with ⌘1 to ⌘9, then Stop Radio; mockup "Controls › Stations", E1) and
/// Controls > Sleep Timer (Off, 15 to 90 minutes, a check mark on the running length). Menu shortcuts work from any screen.
struct PlaybackCommands: Commands {
    let state: AppState
    var body: some Commands {
        CommandMenu("Controls") {
            StationsMenu(state: state)
            Menu("Sleep Timer") { SleepTimerChoices(timer: state.player.sleepTimer) }
        }
    }
}

/// The Stations submenu. With no favourite it says so (disabled) instead of being empty.
struct StationsMenu: View {
    let state: AppState
    var body: some View {
        let favourites = state.stationShortcuts
        Menu("Stations") {
            if favourites.isEmpty {
                Text("No favourite stations")
            } else {
                ForEach(favourites) { shortcut in
                    Button(shortcut.name) { state.tuneShortcut(shortcut.number) }
                        .keyboardShortcut(KeyEquivalent(Character(String(shortcut.number))), modifiers: .command)
                }
            }
            Divider()
            Button("Stop Radio") { state.player.stopStation() }.disabled(state.player.live == nil)
        }
    }
}

/// Paths > Album Paths… (⌥⌘P) and Artist Paths… (⇧⌥⌘P): the same actions as the Paths buttons on the album and artist pages.
struct PathsCommands: Commands {
    let state: AppState
    var body: some Commands {
        CommandMenu("Paths") {
            Button("Album Paths…") { state.showAlbumPaths() }
                .keyboardShortcut("p", modifiers: [.command, .option])
                .disabled(!state.canShowAlbumPaths)
            Button("Artist Paths…") { state.showArtistPaths() }
                .keyboardShortcut("p", modifiers: [.command, .option, .shift])
                .disabled(!state.canShowArtistPaths)
        }
    }
}
