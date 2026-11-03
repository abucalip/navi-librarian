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
    @State private var naviUser = ""
    @State private var naviPass = ""
    @State private var libUser = ""
    @State private var libPass = ""
    @State private var message: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Settings").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                if let s = state.session {
                    connection(s)
                    profiles(s)
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
                        Text("\(p.network.displayName) · \(p.librarianURL.absoluteString) · \(p.navidromeURL.absoluteString)")
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
            }
            .textFieldStyle(.roundedBorder).autocorrectionDisabled()
            Button("Add profile") {
                run {
                    try s.addProfile(name: name, librarianURL: librarianURL, navidromeURL: navidromeURL)
                    name = ""; librarianURL = ""; navidromeURL = ""
                }
            }
            .buttonStyle(CapsuleButtonStyle(primary: true))
            Text("Plain http is accepted only for home-network addresses, .local names and Tailscale addresses.")
                .font(.system(size: 11)).foregroundStyle(CU.muted)
        }
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
