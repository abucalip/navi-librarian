import DiscairCore
import SwiftUI

/// Settings: connection, profiles and the two logins. No mockup exists for this screen; it follows Cupertino's
/// rules (bold sans title, opaque white content, grouped cards, red-pink accent). Passwords go to the Keychain
/// and are never shown or read back.
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

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                Text("Settings").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).padding(.top, 4).accessibilityAddTraits(.isHeader)
                if let s = state.session {
                    connection(s)
                    playback
                    musicFolder(s)
                    profiles(s)
                    listenBrainz()
                    logins(s)
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
        Text(text).font(.system(size: 12)).foregroundStyle(CU.textSecondary)
    }

    private var playback: some View {
        let player = state.player
        return card("Playback") {
            Text("Crossfade between songs").font(.system(size: 13, weight: .semibold))
            CUSegmented(PlayerModel.crossfadeChoices.map { (value: $0, label: $0 == 0 ? "Off" : "\($0) s") },
                        selection: Binding(get: { player.crossfadeSeconds }, set: { player.crossfadeSeconds = $0 }),
                        accessibilityName: "Crossfade between songs")
            note("Consecutive tracks of one album always play gapless, so the fade happens between unrelated songs.")
            Text("Streaming quality").font(.system(size: 13, weight: .semibold)).padding(.top, CU.Space.s)
            CUSegmented(PlayerModel.qualityChoices.map { (value: $0, label: $0.map { "\($0)" } ?? "Original") },
                        selection: Binding(get: { player.qualityCap }, set: { player.qualityCap = $0 }),
                        accessibilityName: "Streaming quality")
            note("Original plays the file as it is. A number is the most the server may send (kbps); it converts only files above it. Applies to songs started afterwards.")
            CUSwitchRow(title: "Match the output sample rate", isOn: Binding(get: { player.matchOutputRate }, set: { player.matchOutputRate = $0 }),
                        detail: "Switches your Mac's output device to each song's sample rate when the device offers it, so nothing is resampled. This changes the system output rate; it is put back when you switch this off or quit Discair. A short pause between songs of different rates is normal.")
                .padding(.top, CU.Space.s)
            CUSwitchRow(title: "Scrobble plays", isOn: Binding(get: { player.scrobbling }, set: { player.scrobbling = $0 }),
                        detail: "Reports what you play to Navidrome, which feeds your listening history and so your recommendations. Off sends nothing from this Mac.")
                .padding(.top, CU.Space.s)
            CUSwitchRow(title: "Tell me when a Get finishes", isOn: Binding(get: { state.acquisition.notifiesWhenFinished }, set: { state.acquisition.notifiesWhenFinished = $0 }),
                        detail: "A macOS notification when an album or song you asked for is in your library, or could not be found. macOS asks permission the first time.")
                .padding(.top, CU.Space.s)
            CUSwitchRow(title: "Keep played songs and covers", isOn: Binding(get: { state.cache.isEnabled }, set: { state.cache.isEnabled = $0 }),
                        detail: "Off by default. Songs you play and their covers are kept on this Mac, up to 2 GB, oldest-used removed first, so they play and show without the server.")
                .padding(.top, CU.Space.s)
            HStack(spacing: CU.Space.s) {
                Text(state.cache.readout).font(.system(size: 12)).foregroundStyle(CU.textSecondary)
                Button("Clear") { Task { await state.cache.clear() } }.buttonStyle(CapsuleButtonStyle(small: true))
                    .accessibilityLabel("Clear the saved songs and covers")
            }
            Button("Equalizer · \(state.player.eq.enabled ? state.player.eq.presetLabel : "Off")") { state.screen = .equalizer }
                .buttonStyle(CapsuleButtonStyle(small: true)).padding(.top, CU.Space.s)
        }
        .task { await state.cache.refresh() }
    }

    private func musicFolder(_ s: SessionModel) -> some View {
        let share = state.share
        return card("Music folder over SMB") {
            HStack(spacing: CU.Space.s) {
                CUStatusLabel(share.isReady ? .connected : (share.settings.enabled ? .notUpdating : .notSetUp))
                Text(share.statusLine).font(.system(size: 12)).foregroundStyle(CU.textSecondary)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Music folder status. \(share.statusLine)")
            HStack(spacing: CU.Space.m) {
                Toggle("Use the music folder", isOn: Binding(get: { share.settings.enabled }, set: { saveShare(); share.setEnabled($0) }))
                    .toggleStyle(.switch).tint(CU.accent).font(.system(size: 13, weight: .semibold))
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
                Text(s.label).font(.system(size: 13, weight: .semibold))
                if s.isUnencrypted { unencryptedPill }
            }
            .accessibilityElement(children: .combine)
            Text(s.statusDetail).font(.system(size: 13)).foregroundStyle(CU.textSecondary)
            HStack {
                Button(s.canRetry ? "Retry" : "Connect") { Task { await s.connect() } }
                    .buttonStyle(CapsuleButtonStyle(primary: true))
                    .disabled(s.status == .connecting)
            }
        }
    }

    private var unencryptedPill: some View {
        Text("Unencrypted").font(.system(size: 11, weight: .semibold)).foregroundStyle(CU.warning)
            .padding(.horizontal, CU.Space.s).frame(height: 24)
            .background(CU.warningTint, in: Capsule())
    }

    private func profiles(_ s: SessionModel) -> some View {
        card("Profiles") {
            if s.profiles.profiles.isEmpty { Text("No profiles yet.").foregroundStyle(CU.textSecondary) }
            ForEach(s.profiles.profiles) { p in
                let active = s.activeProfile?.id == p.id
                let chosen = s.profiles.overrideID == p.id
                HStack(spacing: 10) {
                    Image(systemName: active ? "checkmark.circle.fill" : "circle").foregroundStyle(active ? CU.success : CU.textSecondary)
                        .accessibilityHidden(true)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(p.name).fontWeight(.semibold)
                        Text("\(p.network.displayName) · \(p.librarianURL.absoluteString) · \(p.navidromeURL.absoluteString)\(p.listenBrainzUsername.isEmpty ? "" : " · ListenBrainz \(p.listenBrainzUsername)")")
                            .font(.system(size: 11)).foregroundStyle(CU.textSecondary).lineLimit(1)
                    }
                    Spacer()
                    if p.isUnencrypted { Text("Unencrypted").font(.system(size: 11)).foregroundStyle(CU.textSecondary) }
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
                .font(.system(size: 11)).foregroundStyle(CU.textSecondary)
        }
    }

    private func listenBrainz() -> some View {
        let lb = state.listenBrainz
        return card("ListenBrainz") {
            HStack(spacing: CU.Space.s) {
                CUStatusLabel(lb.isConnected ? .connected : .notSetUp)
                if lb.isConnected {
                    Text("as \(lb.settings?.username ?? "")\(lb.settings?.tokenConfigured == true ? " (token saved)" : "")")
                        .font(.system(size: 13)).foregroundStyle(CU.textSecondary)
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
                .font(.system(size: 11)).foregroundStyle(CU.textSecondary)
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
                .font(.system(size: 11)).foregroundStyle(CU.textSecondary)
        }
    }

    private func login(_ title: String, saved: String?, user: Binding<String>, pass: Binding<String>,
                       save: @escaping () throws -> Void, remove: @escaping () throws -> Void) -> some View {
        VStack(alignment: .leading, spacing: 6) {
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
