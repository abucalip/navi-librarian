import DiscairCore
import Observation
import Sparkle
import SwiftUI

/// Sparkle behind one small object. It starts only when `UpdateConfiguration` says the build is a packaged app with an
/// https feed and an EdDSA public key; otherwise the menu item is greyed with the reason and nothing runs.
@MainActor
@Observable
final class UpdaterModel {
    let configuration: UpdateConfiguration
    @ObservationIgnored private let controller: SPUStandardUpdaterController?

    init(configuration: UpdateConfiguration = .current) {
        self.configuration = configuration
        controller = configuration.isReady
            ? SPUStandardUpdaterController(startingUpdater: true, updaterDelegate: nil, userDriverDelegate: nil)
            : nil
    }

    var canCheck: Bool { controller?.updater.canCheckForUpdates ?? false }

    func checkForUpdates() { controller?.checkForUpdates(nil) }
}

struct UpdateCommands: Commands {
    let updater: UpdaterModel

    var body: some Commands {
        CommandGroup(after: .appInfo) {
            Button("Check for Updates…") { updater.checkForUpdates() }
                .disabled(!updater.configuration.isReady)
                .help(updater.configuration.summary)
            if !updater.configuration.isReady {
                Text(updater.configuration.summary)
            }
        }
    }
}
