import DiscairCore
import SwiftUI

/// Settings, in four tabs (`docs/redesign.md` sections 5.3 and 6.2): Services (the connected services, their health and setup,
/// `CupertinoServices`), Playback, Music folder and Profiles. The cards inside the last three keep their form until step M10.
/// Passwords go to the Keychain and are never shown or read back.
struct CupertinoSettings: View {
    let state: AppState
    @State private var name = ""
    @State private var librarianURL = ""
    @State private var navidromeURL = ""
    @State private var lbUser = ""
    @State private var naviUser = ""
    @State private var naviPass = ""
    @State private var libUser = ""
    @State private var libPass = ""
    @State private var message: String?
    @State private var shareAddress = ""
    @State private var shareServerRoot = ""
    @State private var shareLocalRoot = ""
    @State private var shareUser = ""
    @State private var sharePass = ""
    @State private var confirmClearCache = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                Text("Settings").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).padding(.top, 4).accessibilityAddTraits(.isHeader)
                CUSegmented(SettingsTab.allCases.map { (value: $0, label: $0.rawValue) }, selection: Binding(get: { state.settingsTab }, set: { state.settingsTab = $0 }),
                            accessibilityName: "Settings section", inControlBar: true)
                if state.settingsTab == .services {
                    CupertinoServices(state: state)
                } else if let s = state.session {
                    switch state.settingsTab {
                    case .playback: playback
                    case .musicFolder: musicFolder(s)
                    case .profiles:
                        connection(s)
                        profiles(s)
                        listenBrainz()
                        logins(s)
                    case .services: EmptyView()
                    }
                    if let message { CUNotice(kind: .danger, lead: "Could not save.", message: message) }
                } else {
                    Text("Settings are available in the running app.").foregroundStyle(CU.textSecondary)
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }

    private func card<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        CUPanel(title) { VStack(alignment: .leading, spacing: CU.Space.s) { content() } }
    }

    private func note(_ text: String) -> some View {
        Text(text).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary)
    }

    /// Playback (redesign 5.3, mockup `settings--playback`): one grouped panel of rows. Each row has its words on the left and
    /// its control on the trailing edge: a segmented control for a choice, a switch for on or off, a neutral or danger button
    /// for an action. The Clear button names what it removes.
    private var playback: some View {
        let player = state.player
        return CUPanel {
            playbackRow("Crossfade between songs", detail: "Tracks that follow each other on one album always play gapless, so the fade happens between unrelated songs.") {
                CUSegmented(PlayerModel.crossfadeChoices.map { (value: $0, label: $0 == 0 ? "Off" : "\($0) s") },
                            selection: Binding(get: { player.crossfadeSeconds }, set: { player.crossfadeSeconds = $0 }),
                            accessibilityName: "Crossfade between songs")
            }
            Divider()
            playbackRow("Streaming quality", detail: "Original plays the file as it is. A number is the most the server may send, in kbps. Applies to songs started afterwards.") {
                CUSegmented(PlayerModel.qualityChoices.map { (value: $0, label: $0.map { "\($0)" } ?? "Original") },
                            selection: Binding(get: { player.qualityCap }, set: { player.qualityCap = $0 }),
                            accessibilityName: "Streaming quality")
            }
            Divider()
            playbackRow("Match the output sample rate", detail: "Switches your Mac's output device to each song's rate when the device offers it. Put back when you switch this off or quit. A short pause between songs of different rates is normal.") {
                switchControl("Match the output sample rate", Binding(get: { player.matchOutputRate }, set: { player.matchOutputRate = $0 }))
            }
            Divider()
            playbackRow("Scrobble plays", detail: "Reports what you play to Navidrome, which feeds your history and recommendations. Off sends nothing from this Mac.") {
                switchControl("Scrobble plays", Binding(get: { player.scrobbling }, set: { player.scrobbling = $0 }))
            }
            Divider()
            playbackRow("Tell me when a Get finishes", detail: "A macOS notification when an album is in your library, or could not be found. macOS asks permission the first time.") {
                switchControl("Tell me when a Get finishes", Binding(get: { state.acquisition.notifiesWhenFinished }, set: { state.acquisition.notifiesWhenFinished = $0 }))
            }
            Divider()
            playbackRow("Keep played songs and covers", detail: "Up to 2 GB on this Mac, oldest-used removed first. Off by default; songs and covers then play and show without the server. \(state.cache.readout)") {
                HStack(spacing: CU.Space.s) {
                    Button("Clear…") { confirmClearCache = true }
                        .buttonStyle(CapsuleButtonStyle(small: true, destructive: true))
                        .accessibilityLabel("Clear the saved songs and covers")
                    switchControl("Keep played songs and covers", Binding(get: { state.cache.isEnabled }, set: { state.cache.isEnabled = $0 }))
                }
            }
            Divider()
            playbackRow("Equalizer", detail: "10 bands. Now: \(player.eq.enabled ? player.eq.presetLabel : "Off").") {
                Button { state.screen = .equalizer } label: { HStack(spacing: CU.Space.xs) { Text("Open"); Image(systemName: "chevron.right").font(CU.Icon.small(.semibold)) } }
                    .buttonStyle(CapsuleButtonStyle(small: true))
            }
        }
        .task { await state.cache.refresh() }
        .alert("Clear the saved songs and covers?", isPresented: $confirmClearCache) {
            Button("Cancel", role: .cancel) {}
            Button("Clear", role: .destructive) { Task { await state.cache.clear() } }
        } message: {
            Text("Removes the songs and covers kept on this Mac. Your library on the server is not changed.")
        }
    }

    /// One settings row: words on the left, the control on the trailing edge, 16 of padding above and below.
    private func playbackRow<Control: View>(_ title: String, detail: String, @ViewBuilder control: () -> Control) -> some View {
        HStack(alignment: .center, spacing: CU.Space.l) {
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(title).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                Text(detail).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            control()
        }
        .padding(.vertical, CU.Space.m)
    }

    /// The system switch, labelled for VoiceOver and with the label hidden on screen (the row carries the words).
    private func switchControl(_ label: String, _ isOn: Binding<Bool>) -> some View {
        Toggle(label, isOn: isOn).labelsHidden().toggleStyle(.switch).tint(CU.accent)
    }

    private func musicFolder(_ s: SessionModel) -> some View {
        let share = state.share
        return card("Music folder over SMB") {
            HStack(spacing: CU.Space.s) {
                CUStatusLabel(share.isReady ? .connected : (share.settings.enabled ? .notUpdating : .notSetUp))
                Text(share.statusLine).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Music folder status. \(share.statusLine)")
            HStack(spacing: CU.Space.m) {
                Toggle("Use the music folder", isOn: Binding(get: { share.settings.enabled }, set: { saveShare(); share.setEnabled($0) }))
                    .toggleStyle(.switch).tint(CU.accent).font(CU.Font.body.weighted(.semibold))
                Button("Connect now") { saveShare(); Task { await share.mountNow() } }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled(!share.settings.enabled || share.status == .mounting)
            }
            CUField(label: "Share address", text: $shareAddress, placeholder: "smb://192.168.1.87/media")
            CUField(label: "Folder as Navidrome sees it", text: $shareServerRoot, placeholder: "/music")
            CUField(label: "Same folder on this Mac", text: $shareLocalRoot, placeholder: "/Volumes/media/library/music")
            HStack(alignment: .bottom, spacing: CU.Space.s) {
                CUField(label: "Share username", text: $shareUser, width: 220)
                CUField(label: "Share password", text: $sharePass, secure: true, width: 220)
                Button(share.username == nil ? "Save login" : "Replace login") {
                    run { try share.saveLogin(username: shareUser, password: sharePass); sharePass = "" }
                }.buttonStyle(CapsuleButtonStyle(small: true))
                if share.username != nil { Button("Remove login") { run { try share.removeLogin() } }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true)) }
                Spacer(minLength: 0)
            }
            note(share.username.map { "Login saved for \($0)." } ?? "No share login saved.")
            Button("Save folder settings") { saveShare() }.buttonStyle(CapsuleButtonStyle(small: true))
            if let e = share.settingsError { CUNotice(kind: .danger, lead: "Folder settings problem.", message: e) }
            note("Optional. The app mounts the share itself, like Finder's Connect to Server, and only reads from it (quick tag reads, coming later). Playback never needs it. The login is kept in the Keychain on this Mac.")
        }
        .onAppear {
            shareAddress = share.settings.address; shareServerRoot = share.settings.serverRoot; shareLocalRoot = share.settings.localRoot
        }
    }

    private func saveShare() { state.share.save(address: shareAddress, serverRoot: shareServerRoot, localRoot: shareLocalRoot) }

    private func connection(_ s: SessionModel) -> some View {
        card("Connection") {
            HStack(spacing: CU.Space.s) {
                CUStatusLabel(s.isGood ? .connected : (s.status == .connecting ? .unknown : .noAnswer))
                Text(s.label).font(CU.Font.body.weighted(.semibold))
                if s.isUnencrypted { unencryptedPill }
            }
            .accessibilityElement(children: .combine)
            Text(s.statusDetail).font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.textSecondary)
            HStack {
                Button(s.canRetry ? "Retry" : "Connect") { Task { await s.connect() } }
                    .buttonStyle(CapsuleButtonStyle(primary: true))
                    .disabled(s.status == .connecting)
            }
        }
    }

    private var unencryptedPill: some View {
        Text("Unencrypted").font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.warning)
            .padding(.horizontal, CU.Space.s).frame(height: 24)
            .background(CU.warningTint, in: Capsule())
    }

    private func profiles(_ s: SessionModel) -> some View {
        card("Profiles") {
            if s.profiles.profiles.isEmpty { Text("No profiles yet.").foregroundStyle(CU.textSecondary) }
            ForEach(s.profiles.profiles) { p in
                let active = s.activeProfile?.id == p.id
                let chosen = s.profiles.overrideID == p.id
                HStack(spacing: 8) {
                    Image(systemName: active ? "checkmark.circle.fill" : "circle").foregroundStyle(active ? CU.success : CU.textSecondary)
                        .accessibilityHidden(true)
                    VStack(alignment: .leading, spacing: 0) {
                        Text(p.name).fontWeight(.semibold)
                        Text("\(p.network.displayName) · \(p.librarianURL.absoluteString) · \(p.navidromeURL.absoluteString)\(p.listenBrainzUsername.isEmpty ? "" : " · ListenBrainz \(p.listenBrainzUsername)")")
                            .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary).lineLimit(1)
                    }
                    Spacer()
                    if p.isUnencrypted { Text("Unencrypted").font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary) }
                    Button(chosen ? "Automatic" : "Use this") {
                        run { try s.setOverride(chosen ? nil : p.id); Task { await s.connect() } }
                    }
                    .buttonStyle(CapsuleButtonStyle(small: true))
                    Button("Remove") { run { try s.removeProfile(id: p.id) } }
                        .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                }
                .accessibilityElement(children: .contain)
            }
            Divider()
            Text("Add a profile").fontWeight(.semibold)
            HStack(alignment: .top, spacing: CU.Space.s) {
                CUField(label: "Name", text: $name, placeholder: "Home")
                CUField(label: "Librarian address", text: $librarianURL, placeholder: "http://100.92.14.7:8080")
                CUField(label: "Navidrome address", text: $navidromeURL, placeholder: "http://100.92.14.7:4533")
                CUField(label: "ListenBrainz username (optional)", text: $lbUser)
            }
            Button("Add profile") {
                run {
                    try s.addProfile(name: name, librarianURL: librarianURL, navidromeURL: navidromeURL, listenBrainzUsername: lbUser)
                    name = ""; librarianURL = ""; navidromeURL = ""; lbUser = ""
                }
            }
            .buttonStyle(CapsuleButtonStyle())
            Text("Plain http is accepted only for home-network addresses, .local names and Tailscale addresses.")
                .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
        }
    }

    private func listenBrainz() -> some View {
        let lb = state.listenBrainz
        return card("ListenBrainz") {
            HStack(spacing: CU.Space.s) {
                CUStatusLabel(lb.isConnected ? .connected : .notSetUp)
                if lb.isConnected {
                    Text("as \(lb.settings?.username ?? "")\(lb.settings?.tokenConfigured == true ? " (token saved)" : "")")
                        .font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.textSecondary)
                }
            }
            HStack(alignment: .bottom, spacing: CU.Space.s) {
                CUField(label: "ListenBrainz username", text: Bindable(lb).username, width: 220)
                CUField(label: "Token", text: Bindable(lb).token, placeholder: lb.settings?.tokenConfigured == true ? "Saved" : "Optional", secure: true, width: 220)
                Button(lb.isConnected ? "Update" : "Connect") { Task { await state.connectListenBrainz() } }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled(!lb.canSave)
                Spacer(minLength: 0)
            }
            if let n = lb.note { CUNotice(kind: .warning, lead: "ListenBrainz.", message: n) }
            Text("The server reads your listens from ListenBrainz to describe your taste. The username is enough for public listens; the token is only for private profiles. Both are kept in the macOS Keychain and sent to the server at every startup; the token is never shown again.")
                .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
        }
        .task { await lb.load(librarian: state.session?.librarian) }
    }

    private func logins(_ s: SessionModel) -> some View {
        card("Logins") {
            login("Navidrome", saved: s.navidromeUsername, user: $naviUser, pass: $naviPass,
                  save: { try s.saveLogin(.navidrome, username: naviUser, password: naviPass); naviPass = "" },
                  remove: { try s.removeLogin(.navidrome) })
            Divider()
            login("Librarian", saved: s.librarianUsername, user: $libUser, pass: $libPass,
                  save: { try s.saveLogin(.librarian, username: libUser, password: libPass); libPass = "" },
                  remove: { try s.removeLogin(.librarian) })
            Text("Stored in the macOS Keychain on this Mac only. Passwords are never shown.")
                .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.textSecondary)
        }
    }

    private func login(_ title: String, saved: String?, user: Binding<String>, pass: Binding<String>,
                       save: @escaping () throws -> Void, remove: @escaping () throws -> Void) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(title).fontWeight(.semibold)
                Text(saved.map { "Saved for \($0)" } ?? "Not saved").foregroundStyle(CU.textSecondary)
                Spacer()
                if saved != nil { Button("Remove") { run(remove) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true)) }
            }
            HStack(alignment: .bottom, spacing: CU.Space.s) {
                CUField(label: "Username", text: user, width: 220)
                CUField(label: "Password", text: pass, secure: true, width: 220)
                Button(saved == nil ? "Save" : "Replace") { run(save) }.buttonStyle(CapsuleButtonStyle(small: true))
                Spacer(minLength: 0)
            }
        }
    }

    private func run(_ body: () throws -> Void) {
        do { try body(); message = nil } catch { message = error.settingsMessage }
    }
}
