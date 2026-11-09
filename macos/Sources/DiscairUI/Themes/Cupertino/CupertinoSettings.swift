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
            VStack(alignment: .leading, spacing: 18) {
                Text("Settings").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                if let s = state.session {
                    connection(s)
                    playback
                    musicFolder(s)
                    profiles(s)
                    listenBrainz()
                    logins(s)
                    if let message { Text(message).font(.system(size: 12)).foregroundStyle(CU.accent) }
                } else {
                    Text("Settings are available in the running app.").foregroundStyle(CU.muted)
                }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }

    private func card<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title).font(CU.title(17)).accessibilityAddTraits(.isHeader)
            content()
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var playback: some View {
        card("Playback") {
            Text("Crossfade between songs").fontWeight(.semibold)
            HStack(spacing: 8) {
                ForEach(PlayerModel.crossfadeChoices, id: \.self) { n in
                    let on = state.player.crossfadeSeconds == n
                    Button(n == 0 ? "Off" : "\(n) s") { state.player.crossfadeSeconds = n }
                        .buttonStyle(CapsuleButtonStyle(primary: on, small: true))
                        .accessibilityAddTraits(on ? .isSelected : [])
                }
            }
            Text("Consecutive tracks of one album always play gapless, so the fade happens between unrelated songs.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
            Text("Streaming quality").fontWeight(.semibold).padding(.top, 6)
            HStack(spacing: 8) {
                ForEach(PlayerModel.qualityChoices, id: \.self) { q in
                    let on = state.player.qualityCap == q
                    Button(q.map { "\($0)" } ?? "Original") { state.player.qualityCap = q }
                        .buttonStyle(CapsuleButtonStyle(primary: on, small: true))
                        .accessibilityLabel(q.map { "\($0) kilobits per second" } ?? "Original quality")
                        .accessibilityAddTraits(on ? .isSelected : [])
                }
            }
            Text("Original plays the file as it is. A number is the most the server may send (kbps); it converts only files above it. Applies to songs started afterwards.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
            Text("Songs that follow each other on one album always play gapless, with no fade.").font(.system(size: 12)).foregroundStyle(CU.muted)
            Text("Match the output sample rate").fontWeight(.semibold).padding(.top, 6)
            HStack(spacing: 8) {
                ForEach([true, false], id: \.self) { on in
                    Button(on ? "On" : "Off") { state.player.matchOutputRate = on }
                        .buttonStyle(CapsuleButtonStyle(primary: state.player.matchOutputRate == on, small: true))
                        .accessibilityLabel(on ? "Sample rate matching on" : "Sample rate matching off")
                        .accessibilityAddTraits(state.player.matchOutputRate == on ? .isSelected : [])
                }
            }
            Text("Switches your Mac's output device to each song's sample rate when the device offers it, so nothing is resampled. This changes the system output rate; it is put back when you switch this off or quit Discair. A short pause between songs of different rates is normal.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
            Text("Scrobble plays").fontWeight(.semibold).padding(.top, 6)
            HStack(spacing: 8) {
                ForEach([true, false], id: \.self) { on in
                    Button(on ? "On" : "Off") { state.player.scrobbling = on }
                        .buttonStyle(CapsuleButtonStyle(primary: state.player.scrobbling == on, small: true))
                        .accessibilityLabel(on ? "Scrobbling on" : "Scrobbling off")
                        .accessibilityAddTraits(state.player.scrobbling == on ? .isSelected : [])
                }
            }
            Text("Reports what you play to Navidrome, which feeds your listening history and so your recommendations. Off sends nothing from this Mac.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
            Text("Tell me when a Get finishes").fontWeight(.semibold).padding(.top, 6)
            HStack(spacing: 8) {
                ForEach([true, false], id: \.self) { on in
                    Button(on ? "On" : "Off") { state.acquisition.notifiesWhenFinished = on }
                        .buttonStyle(CapsuleButtonStyle(primary: state.acquisition.notifiesWhenFinished == on, small: true))
                        .accessibilityLabel(on ? "Get finished notifications on" : "Get finished notifications off")
                        .accessibilityAddTraits(state.acquisition.notifiesWhenFinished == on ? .isSelected : [])
                }
            }
            Text("A macOS notification when an album or song you asked for is in your library, or could not be found. macOS asks permission the first time.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
            Text("Keep played songs and covers").fontWeight(.semibold).padding(.top, 6)
            HStack(spacing: 8) {
                ForEach([true, false], id: \.self) { on in
                    Button(on ? "On" : "Off") { state.cache.isEnabled = on }
                        .buttonStyle(CapsuleButtonStyle(primary: state.cache.isEnabled == on, small: true))
                        .accessibilityLabel(on ? "Keep a copy of played songs on" : "Keep a copy of played songs off")
                        .accessibilityAddTraits(state.cache.isEnabled == on ? .isSelected : [])
                }
                Text(state.cache.readout).font(.system(size: 12)).foregroundStyle(CU.muted)
                Button("Clear") { Task { await state.cache.clear() } }.buttonStyle(CapsuleButtonStyle(small: true))
                    .accessibilityLabel("Clear the saved songs and covers")
            }
            Text("Off by default. Songs you play and their covers are kept on this Mac, up to 2 GB, oldest-used removed first, so they play and show without the server.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
            Button("Equalizer · \(state.player.eq.enabled ? state.player.eq.presetLabel : "Off")") { state.screen = .equalizer }
                .buttonStyle(CapsuleButtonStyle(small: true))
        }
        .task { await state.cache.refresh() }
    }

    private func musicFolder(_ s: SessionModel) -> some View {
        let share = state.share
        return card("Music folder over SMB") {
            Text(share.statusLine).font(.system(size: 13)).foregroundStyle(share.isReady ? CU.muted : CU.accent)
                .accessibilityLabel("Music folder status. \(share.statusLine)")
            HStack(spacing: 8) {
                ForEach([true, false], id: \.self) { on in
                    Button(on ? "On" : "Off") { saveShare(); share.setEnabled(on) }
                        .buttonStyle(CapsuleButtonStyle(primary: share.settings.enabled == on, small: true))
                        .accessibilityLabel(on ? "Music folder on" : "Music folder off")
                        .accessibilityAddTraits(share.settings.enabled == on ? .isSelected : [])
                }
                Button("Connect now") { saveShare(); Task { await share.mountNow() } }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled(!share.settings.enabled || share.status == .mounting)
            }
            TextField("Share address (smb://192.168.1.87/media)", text: $shareAddress)
            TextField("Folder as Navidrome sees it (/music)", text: $shareServerRoot)
            TextField("Same folder on this Mac (/Volumes/media/library/music)", text: $shareLocalRoot)
            HStack {
                TextField("Share username", text: $shareUser).frame(width: 220)
                SecureField("Share password", text: $sharePass).frame(width: 220)
                Button(share.username == nil ? "Save login" : "Replace login") {
                    run { try share.saveLogin(username: shareUser, password: sharePass); sharePass = "" }
                }.buttonStyle(CapsuleButtonStyle(small: true))
                if share.username != nil { Button("Remove login") { run { try share.removeLogin() } }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true)) }
                Spacer(minLength: 0)
            }
            Text(share.username.map { "Login saved for \($0)." } ?? "No share login saved.").font(.system(size: 12)).foregroundStyle(CU.muted)
            Button("Save folder settings") { saveShare() }.buttonStyle(CapsuleButtonStyle(small: true))
            if let e = share.settingsError { Text(e).font(.system(size: 12)).foregroundStyle(CU.accent) }
            Text("Optional. The app mounts the share itself, like Finder's Connect to Server, and only reads from it (waveforms and quick tag reads, coming later). Playback never needs it. The login is kept in the Keychain on this Mac.")
                .font(.system(size: 12)).foregroundStyle(CU.muted)
        }
        .textFieldStyle(.roundedBorder).autocorrectionDisabled()
        .onAppear {
            shareAddress = share.settings.address; shareServerRoot = share.settings.serverRoot; shareLocalRoot = share.settings.localRoot
        }
    }

    private func saveShare() { state.share.save(address: shareAddress, serverRoot: shareServerRoot, localRoot: shareLocalRoot) }

    private func connection(_ s: SessionModel) -> some View {
        card("Connection") {
            HStack(spacing: 8) {
                Circle().fill(s.isGood ? Color.green : (s.status == .connecting ? Color.orange : CU.accent)).frame(width: 9, height: 9)
                Text(s.label).fontWeight(.semibold)
                if s.isUnencrypted {
                    Text("Unencrypted").font(.system(size: 11, weight: .semibold)).padding(.horizontal, 8)
                        .overlay(Capsule().stroke(CU.muted, lineWidth: 1))
                }
            }
            .accessibilityElement(children: .combine)
            Text(s.statusDetail).foregroundStyle(CU.muted)
            HStack {
                Button(s.canRetry ? "Retry" : "Connect") { Task { await s.connect() } }
                    .buttonStyle(CapsuleButtonStyle(primary: true))
                    .disabled(s.status == .connecting)
            }
        }
    }

    private func profiles(_ s: SessionModel) -> some View {
        card("Profiles") {
            if s.profiles.profiles.isEmpty { Text("No profiles yet.").foregroundStyle(CU.muted) }
            ForEach(s.profiles.profiles) { p in
                let active = s.activeProfile?.id == p.id
                let chosen = s.profiles.overrideID == p.id
                HStack(spacing: 10) {
                    Image(systemName: active ? "checkmark.circle.fill" : "circle").foregroundStyle(active ? CU.accent : CU.muted)
                        .accessibilityHidden(true)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(p.name).fontWeight(.semibold)
                        Text("\(p.network.displayName) · \(p.librarianURL.absoluteString) · \(p.navidromeURL.absoluteString)\(p.listenBrainzUsername.isEmpty ? "" : " · ListenBrainz \(p.listenBrainzUsername)")")
                            .font(.system(size: 11)).foregroundStyle(CU.muted).lineLimit(1)
                    }
                    Spacer()
                    if p.isUnencrypted { Text("Unencrypted").font(.system(size: 11)).foregroundStyle(CU.muted) }
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
            HStack {
                TextField("Name (Home)", text: $name)
                TextField("Librarian address", text: $librarianURL)
                TextField("Navidrome address", text: $navidromeURL)
                TextField("ListenBrainz username (optional)", text: $lbUser)
            }
            .textFieldStyle(.roundedBorder).autocorrectionDisabled()
            Button("Add profile") {
                run {
                    try s.addProfile(name: name, librarianURL: librarianURL, navidromeURL: navidromeURL, listenBrainzUsername: lbUser)
                    name = ""; librarianURL = ""; navidromeURL = ""; lbUser = ""
                }
            }
            .buttonStyle(CapsuleButtonStyle(primary: true))
            Text("Plain http is accepted only for home-network addresses, .local names and Tailscale addresses.")
                .font(.system(size: 11)).foregroundStyle(CU.muted)
        }
    }

    private func listenBrainz() -> some View {
        let lb = state.listenBrainz
        return card("ListenBrainz") {
            Text(lb.isConnected ? "Connected as \(lb.settings?.username ?? "")\(lb.settings?.tokenConfigured == true ? " (token saved)" : "")" : "Not connected")
                .fontWeight(.semibold)
            HStack {
                TextField("ListenBrainz username", text: Bindable(lb).username).frame(width: 220)
                SecureField(lb.settings?.tokenConfigured == true ? "Token (saved)" : "Token (optional)", text: Bindable(lb).token).frame(width: 220)
                Button(lb.isConnected ? "Update" : "Connect") { Task { await state.connectListenBrainz() } }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled(!lb.canSave)
                Spacer(minLength: 0)
            }
            .textFieldStyle(.roundedBorder).autocorrectionDisabled()
            if let note = lb.note { Text(note).font(.system(size: 12)).foregroundStyle(CU.accent) }
            Text("The server reads your listens from ListenBrainz to describe your taste. The username is enough for public listens; the token is only for private profiles. Both are kept in the macOS Keychain and sent to the server at every startup; the token is never shown again.")
                .font(.system(size: 11)).foregroundStyle(CU.muted)
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
                .font(.system(size: 11)).foregroundStyle(CU.muted)
        }
    }

    private func login(_ title: String, saved: String?, user: Binding<String>, pass: Binding<String>,
                       save: @escaping () throws -> Void, remove: @escaping () throws -> Void) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title).fontWeight(.semibold)
                Text(saved.map { "Saved for \($0)" } ?? "Not saved").foregroundStyle(CU.muted)
                Spacer()
                if saved != nil { Button("Remove") { run(remove) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true)) }
            }
            HStack {
                TextField("Username", text: user).frame(width: 220)
                SecureField("Password", text: pass).frame(width: 220)
                Button(saved == nil ? "Save" : "Replace") { run(save) }.buttonStyle(CapsuleButtonStyle(small: true))
                Spacer(minLength: 0)
            }
            .textFieldStyle(.roundedBorder).autocorrectionDisabled()
        }
    }

    private func run(_ body: () throws -> Void) {
        do { try body(); message = nil } catch { message = error.settingsMessage }
    }
}
