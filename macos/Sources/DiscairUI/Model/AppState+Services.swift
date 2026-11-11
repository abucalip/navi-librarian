import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation

/// The checks, tests and saves behind the Services screen (`docs/redesign.md` section 6, step M9). `ServicesModel` decides what the
/// answers mean; this only asks. Each read fails on its own, so one service that does not answer never hides the others.
extension AppState {

    // MARK: Check

    /// Reads every service's state: the app's own checks of Navidrome and the music folder, and, through the Librarian, the
    /// capabilities, the five settings routes and a test of each service that is set up. With the Librarian down nothing it would
    /// report is read, so those services stay Unknown (section 6.2).
    public func refreshServices(now: Date = Date()) async {
        guard let session else { return }
        // Before the first connect finishes nothing has failed yet: the button keeps saying "Checking…" and `onConnected` checks again.
        switch session.status {
        case .connecting, .notConfigured: return
        case .connected, .failed: break
        }
        services.beginChecking()
        var input = ServicesModel.Inputs(now: now)
        let profile = session.activeProfile ?? session.profiles.profiles.first
        input.librarianAddress = profile.map { Self.addressText($0.librarianURL) }
        input.tailscaleHint = profile.map { Self.looksLikeTailscale($0.librarianURL) } ?? false
        input.share = Self.shareState(share)
        input.shareAddress = share.settings.address

        input.navidromeCheck = await Self.navidromeCheck(session)

        guard let librarian = session.librarian, let caps = try? await librarian.capabilities() else {
            input.librarianReachable = false
            // Sonic analysis is a Navidrome extension: read it directly. If that fails too, it stays Unknown.
            if let navidrome = session.navidrome { input.sonicAvailable = try? await navidrome.supportsSonicSimilarity() }
            services.finish(input)
            return
        }
        input.librarianReachable = true
        input.capabilities = caps

        async let navi = try? librarian.navidromeSettings()
        async let slskd = try? librarian.slskdSettings()
        async let lastfm = try? librarian.lastFMSettings()
        async let lb = try? librarian.listenBrainzSettings()
        async let discogs = try? librarian.discogsSettings()
        let (naviSettings, slskdSettings, lastFMSettings, lbSettings, discogsSettings) = (await navi, await slskd, await lastfm, await lb, await discogs)
        input.navidromeSettings = naviSettings; input.slskdSettings = slskdSettings; input.lastFMSettings = lastFMSettings
        input.listenBrainzSettings = lbSettings; input.discogsSettings = discogsSettings

        // A service is tested only when it is set up; the others are Not set up without asking.
        async let tSlskd = Self.test(configured: slskdSettings.map { $0.apiKeyConfigured && !$0.url.isEmpty }) { try await librarian.testSlskd() }
        async let tLast = Self.test(configured: lastFMSettings?.apiKeyConfigured) { try await librarian.testLastFM() }
        async let tLB = Self.test(configured: lbSettings.map { !$0.username.isEmpty }) {
            let r = try await librarian.testListenBrainz(); return ServiceTestResult(ok: r.ok, status: r.status, message: r.message)
        }
        async let tDiscogs = Self.test(configured: discogsSettings?.tokenConfigured) { try await librarian.testDiscogs() }
        for (id, result) in [(ServicesModel.ServiceID.slskd, await tSlskd), (.lastfm, await tLast), (.listenbrainz, await tLB), (.discogs, await tDiscogs)] {
            if let result { input.tests[id] = result }
        }
        services.finish(input)
    }

    private static func test(configured: Bool?, _ run: () async throws -> ServiceTestResult) async -> ServiceTestResult? {
        guard configured == true else { return nil }
        do { return try await run() } catch { return ServiceTestResult(ok: false, status: "connection_failed") }
    }

    private static func navidromeCheck(_ session: SessionModel) async -> ServicesModel.DirectCheck {
        guard let navidrome = session.navidrome else {
            if case .failed(let e) = session.status { if case .unauthorised = e { return .rejected }; return .noAnswer }
            return .unchecked
        }
        do { try await navidrome.ping(); return .ok }
        catch let e as DiscairError { if case .unauthorised = e { return .rejected }; return .noAnswer }
        catch { return .noAnswer }
    }

    static func shareState(_ share: ShareModel) -> ServicesModel.ShareState {
        guard share.settings.enabled else { return .off }
        switch share.status {
        case .ready: return share.isReady ? .mounted : .failed
        case .unavailable: return .failed
        case .off, .needsAddress, .mounting: return .off
        }
    }

    /// "100.92.14.7:8080": the host and port as the mockup writes them, without the scheme.
    static func addressText(_ url: URL) -> String {
        guard let host = url.host else { return url.absoluteString }
        return url.port.map { "\(host):\($0)" } ?? host
    }

    /// True for a Tailscale address: a name ending `.ts.net` or an address in 100.64.0.0/10.
    static func looksLikeTailscale(_ url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        if host.hasSuffix(".ts.net") { return true }
        let parts = host.split(separator: ".").compactMap { Int($0) }
        return parts.count == 4 && parts[0] == 100 && (64...127).contains(parts[1])
    }

    // MARK: Row actions

    /// "Fix <service>": opens Settings on the Services tab with that row open, and its edit sheet when it has one.
    public func fixService(_ id: ServicesModel.ServiceID) {
        settingsTab = .services
        screen = .settings
        services.expanded.insert(id)
        if let tab = ServiceEditSpec.settingsTab(for: id) { settingsTab = tab }
        else if ServiceEditSpec.canEdit(id) { services.startEditing(id) }
    }

    /// Edit on an expanded row: the sheet, or the tab where that setting lives.
    public func editService(_ id: ServicesModel.ServiceID) {
        if let tab = ServiceEditSpec.settingsTab(for: id) { settingsTab = tab } else { services.startEditing(id) }
    }

    /// Test again on one row: asks the server to test that service now and keeps the answer.
    public func testService(_ id: ServicesModel.ServiceID) async {
        guard let librarian = session?.librarian else { await refreshServices(); return }
        services.setWorking(true); defer { services.setWorking(false) }
        let result: ServiceTestResult?
        switch id {
        case .slskd: result = try? await librarian.testSlskd()
        case .lastfm: result = try? await librarian.testLastFM()
        case .discogs: result = try? await librarian.testDiscogs()
        case .listenbrainz: result = (try? await librarian.testListenBrainz()).map { ServiceTestResult(ok: $0.ok, status: $0.status, message: $0.message) }
        default: await refreshServices(); return
        }
        services.record(test: result ?? ServiceTestResult(ok: false, status: "connection_failed"), for: id)
    }

    /// The sheet's Test: tests what is saved on the server and says so in a notice. The sheet's Save comes first when values changed.
    public func testFromSheet(_ id: ServicesModel.ServiceID) async {
        guard let librarian = session?.librarian else { services.editNotice = .init(kind: .danger, lead: "Test failed.", message: "The Librarian is not connected."); return }
        services.setWorking(true); defer { services.setWorking(false) }
        let result: ServiceTestResult
        do {
            switch id {
            case .slskd: result = try await librarian.testSlskd()
            case .lastfm: result = try await librarian.testLastFM()
            case .discogs: result = try await librarian.testDiscogs()
            case .navidrome: result = try await librarian.testNavidrome()
            case .listenbrainz:
                let r = try await librarian.testListenBrainz(); result = ServiceTestResult(ok: r.ok, status: r.status, message: r.message)
            default: return
            }
        } catch { result = ServiceTestResult(ok: false, status: "connection_failed") }
        services.editNotice = ServicesController.notice(for: result, name: ServicesModel.name(for: id), noun: ServicesModel.noun(for: id))
    }

    /// Saves the sheet through the settings route of that service. An empty secret keeps the saved one. Closes the sheet and
    /// re-checks on success; on failure the server's sentence stays in the sheet.
    public func saveService(_ id: ServicesModel.ServiceID) async {
        guard let librarian = session?.librarian else { services.actionError = "The Librarian is not connected."; return }
        let d = services.draft
        services.setWorking(true); defer { services.setWorking(false) }
        do {
            switch id {
            case .navidrome: try await librarian.saveNavidrome(url: d.address.trimmed, username: d.username.trimmed, password: d.secret)
            case .slskd:
                try await librarian.saveSlskd(url: d.address.trimmed, apiKey: d.secret, qualityPriority: services.inputs.slskdSettings?.qualityPriority ?? [],
                                              downloadsPath: d.downloadsPath.trimmed, musicLibraryPath: d.libraryPath.trimmed)
            case .lastfm: try await librarian.saveLastFM(apiKey: d.secret, username: d.username.trimmed)
            case .listenbrainz:
                listenBrainz.username = d.username; listenBrainz.token = d.secret
                await connectListenBrainz()
            case .discogs: if !d.secret.isEmpty { try await librarian.saveDiscogs(token: d.secret) }
            default: break
            }
            services.stopEditing()
            await refreshServices()
        } catch {
            services.editNotice = .init(kind: .danger, lead: "Could not save.", message: (error as? DiscairError)?.summary ?? "The server did not accept the change.")
        }
    }

    /// Disconnect, after the alert: clears the saved Discogs token, or the ListenBrainz account on the server and in the Keychain.
    public func disconnectService(_ id: ServicesModel.ServiceID) async {
        guard let librarian = session?.librarian else { return }
        services.setWorking(true); defer { services.setWorking(false) }
        do {
            switch id {
            case .discogs: try await librarian.saveDiscogs(token: "")
            case .listenbrainz:
                try await librarian.saveListenBrainz(username: "", token: "")
                try? session?.removeLogin(.listenbrainz)
            default: break
            }
            services.actionError = nil
            await refreshServices()
        } catch {
            services.actionError = (error as? DiscairError)?.summary ?? "The server did not accept the change."
        }
    }
}

private extension String {
    var trimmed: String { trimmingCharacters(in: .whitespacesAndNewlines) }
}
