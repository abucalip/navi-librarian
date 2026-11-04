import DiscairCore
import SwiftUI

/// Settings: "Subscriber services". No mockup exists for this page; it uses Zine's parts (headline, boxes with
/// 3 pt borders, mono labels, hard-shadow buttons). Passwords go to the Keychain and are never shown or read back.
struct ZineSettings: View {
    let state: AppState
    @State private var name = ""
    @State private var librarianURL = ""
    @State private var navidromeURL = ""
    @State private var naviUser = ""
    @State private var naviPass = ""
    @State private var libUser = ""
    @State private var libPass = ""
    @State private var message: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Settings").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("Connection · Profiles · Logins").padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            if let s = state.session {
                HStack(alignment: .top, spacing: 22) {
                    VStack(alignment: .leading, spacing: 14) { connection(s); playback; profiles(s) }.frame(maxWidth: .infinity)
                    VStack(alignment: .leading, spacing: 14) { addProfile(s); logins(s) }.frame(maxWidth: .infinity)
                }
                if let message { Mono(message, bold: true).foregroundStyle(Z.red) }
            } else {
                Mono("Settings are available in the running app.")
            }
        }
    }

    private func box<C: View>(_ title: String, fill: Color = Z.white, dashed: Bool = false, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            ZineH2(title, size: 20)
            content()
        }
        .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
        .background(fill).zBorder(3, dashed: dashed)
    }

    private var playback: some View {
        box("Playback") {
            Mono("Crossfade between songs", bold: true)
            HStack(spacing: 8) {
                ForEach(PlayerModel.crossfadeChoices, id: \.self) { n in
                    let on = state.player.crossfadeSeconds == n
                    Button(n == 0 ? "Off" : "\(n) s") { state.player.crossfadeSeconds = n }
                        .buttonStyle(ZineButtonStyle(kind: on ? .yellow : .plain, small: true))
                        .accessibilityAddTraits(on ? .isSelected : [])
                }
            }
            Mono("Consecutive tracks of one album always play gapless, so the fade happens between unrelated songs.", size: 10)
            Mono("Streaming quality", bold: true).padding(.top, 6)
            HStack(spacing: 8) {
                ForEach(PlayerModel.qualityChoices, id: \.self) { q in
                    let on = state.player.qualityCap == q
                    Button(q.map { "\($0)" } ?? "Original") { state.player.qualityCap = q }
                        .buttonStyle(ZineButtonStyle(kind: on ? .yellow : .plain, small: true))
                        .accessibilityLabel(q.map { "\($0) kilobits per second" } ?? "Original quality")
                        .accessibilityAddTraits(on ? .isSelected : [])
                }
            }
            Text("Original plays the file as it is. A number is the most the server may send (kbps); it converts only files above it. Applies to songs started afterwards.").font(Z.serif(13))
            Text("Songs that follow each other on one album always play gapless, with no fade.").font(Z.serif(13))
            Button("Equalizer · \(state.player.eq.enabled ? state.player.eq.presetLabel : "Off")") { state.screen = .equalizer }
                .buttonStyle(ZineButtonStyle(small: true))
        }
    }

    private func connection(_ s: SessionModel) -> some View {
        box("Connection", fill: s.isGood ? Z.white : Z.yellow) {
            HStack(spacing: 8) {
                Mono(s.isGood ? "● Connected" : (s.status == .connecting ? "◌ Connecting" : "■ Not connected"), bold: true)
                if s.isUnencrypted { ZineBadge("Unencrypted") }
            }
            Text(s.label).font(Z.serif(14, bold: true))
            Text(s.statusDetail).font(Z.serif(14))
            Button(s.canRetry ? "Retry" : "Connect") { Task { await s.connect() } }
                .buttonStyle(ZineButtonStyle(kind: .yellow)).disabled(s.status == .connecting)
        }
    }

    private func profiles(_ s: SessionModel) -> some View {
        box("Profiles") {
            if s.profiles.profiles.isEmpty { Mono("No profiles yet") }
            ForEach(s.profiles.profiles) { p in
                let active = s.activeProfile?.id == p.id
                let chosen = s.profiles.overrideID == p.id
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(p.name).font(Z.an(16)).textCase(.uppercase)
                        if active { ZineBadge("Active") }
                        if p.isUnencrypted { ZineBadge("Unencrypted") }
                        Spacer()
                        Button(chosen ? "Automatic" : "Use this") { run { try s.setOverride(chosen ? nil : p.id); Task { await s.connect() } } }
                            .buttonStyle(ZineButtonStyle(small: true))
                        Button("Remove") { run { try s.removeProfile(id: p.id) } }.buttonStyle(ZineButtonStyle(small: true))
                    }
                    Mono("\(p.network.rawValue) · \(p.librarianURL.absoluteString) · \(p.navidromeURL.absoluteString)", size: 10).lineLimit(1)
                }
                .padding(.vertical, 5).overlay(alignment: .bottom) { DottedLine() }
            }
        }
    }

    private func addProfile(_ s: SessionModel) -> some View {
        box("Add a profile", fill: Z.yellow) {
            field("Name (Home)", $name)
            field("Librarian address", $librarianURL)
            field("Navidrome address", $navidromeURL)
            Button("Add profile") {
                run {
                    try s.addProfile(name: name, librarianURL: librarianURL, navidromeURL: navidromeURL)
                    name = ""; librarianURL = ""; navidromeURL = ""
                }
            }
            .buttonStyle(ZineButtonStyle())
            Text("Plain http is accepted only for home-network addresses, .local names and Tailscale addresses.").font(Z.serif(12.5, italic: true))
        }
    }

    private func logins(_ s: SessionModel) -> some View {
        box("Logins", dashed: true) {
            login("Navidrome", saved: s.navidromeUsername, user: $naviUser, pass: $naviPass,
                  save: { try s.saveLogin(.navidrome, username: naviUser, password: naviPass); naviPass = "" },
                  remove: { try s.removeLogin(.navidrome) })
            Rectangle().fill(Z.ink).frame(height: 2)
            login("Librarian", saved: s.librarianUsername, user: $libUser, pass: $libPass,
                  save: { try s.saveLogin(.librarian, username: libUser, password: libPass); libPass = "" },
                  remove: { try s.removeLogin(.librarian) })
            Text("Kept in the macOS Keychain on this Mac only. Passwords are never shown.").font(Z.serif(12.5, italic: true))
        }
    }

    private func login(_ title: String, saved: String?, user: Binding<String>, pass: Binding<String>,
                       save: @escaping () throws -> Void, remove: @escaping () throws -> Void) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title).font(Z.an(16)).textCase(.uppercase)
                Mono(saved.map { "Saved for \($0)" } ?? "Not saved", size: 10)
                Spacer()
                if saved != nil { Button("Remove") { run(remove) }.buttonStyle(ZineButtonStyle(small: true)) }
            }
            field("Username", user)
            SecureField("Password", text: pass).textFieldStyle(.plain).font(Z.mono(12))
                .padding(.horizontal, 8).padding(.vertical, 5).background(Z.white).zBorder(2)
            Button(saved == nil ? "Save" : "Replace") { run(save) }.buttonStyle(ZineButtonStyle(small: true))
        }
    }

    private func field(_ prompt: String, _ text: Binding<String>) -> some View {
        TextField(prompt, text: text).textFieldStyle(.plain).font(Z.mono(12)).autocorrectionDisabled()
            .padding(.horizontal, 8).padding(.vertical, 5).background(Z.white).zBorder(2)
    }

    private func run(_ body: () throws -> Void) {
        do { try body(); message = nil } catch { message = error.settingsMessage }
    }
}
