import DiscairUI
import SwiftUI

@main
struct DiscairApp: App {
    @State private var state = AppState()

    var body: some Scene {
        Window("Discair", id: "main") {
            RootView(state: state)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1280, height: 800)
        .commands {
            CommandMenu("Theme") {
                ForEach(ThemeID.allCases) { id in
                    Button(id.rawValue.capitalized) { state.themeID = id }
                }
            }
        }
    }
}
