import DiscairLibrarian
import SwiftUI

// Settings > Services, the toolbar status button and its popover, and the edit sheet: `docs/redesign.md` section 6, step M9.
// Mockups: `settings-services--healthy`, `--degraded`, `--librarian-unreachable`, `--edit-sheet`, and the popover in `home--degraded`.
// The states and sentences come from `ServicesModel`; this file only draws them.

// MARK: Words and symbols

extension ServicesModel.Tone {
    /// check-circle (success), triangle (warning), x-circle (danger), info-circle (info), minus (unknown or off) (section 3).
    var symbol: String {
        switch self {
        case .success: "checkmark.circle"
        case .warning: "exclamationmark.triangle"
        case .danger: "xmark.circle"
        case .info: "info.circle"
        case .neutral: "minus"
        }
    }
    var color: Color {
        switch self {
        case .success: CU.success
        case .warning: CU.warning
        case .danger: CU.danger
        case .info: CU.info
        case .neutral: CU.textSecondary
        }
    }
}

/// A service's state as an icon and its word, never colour alone.
struct ServiceStateLabel: View {
    let state: ServicesModel.State
    var body: some View {
        HStack(spacing: CU.Space.xs) {
            Image(systemName: state.tone.symbol).font(.system(size: 12)).accessibilityHidden(true)
            Text(state.word)
        }
        .font(.system(size: 12, weight: .semibold)).foregroundStyle(state.tone.color).lineLimit(1)
        .accessibilityElement(children: .ignore).accessibilityLabel(state.word)
    }
}

enum ServiceIcon {
    static func symbol(_ id: String) -> String {
        switch id {
        case "mac": "desktopcomputer"
        case "librarian": "server.rack"
        case "navidrome": "music.note"
        case "slskd": "icloud.and.arrow.down"
        case "lastfm", "listenbrainz", "sonic": "waveform"
        case "discogs": "opticaldisc"
        case "musicbrainz": "point.3.connected.trianglepath.dotted"
        case "smb": "folder"
        default: "questionmark.circle"
        }
    }
}

/// Times as section 3 writes them: "Today, 21:14" within the day, "9 November, 14:02" otherwise.
enum ServicesFormat {
    static func when(_ date: Date, now: Date, calendar: Calendar = .current) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_GB"); f.calendar = calendar; f.timeZone = calendar.timeZone
        f.dateFormat = "HH:mm"
        let time = f.string(from: date)
        if calendar.isDate(date, inSameDayAs: now) { return "Today, \(time)" }
        f.dateFormat = "d MMMM"
        return "\(f.string(from: date)), \(time)"
    }

    static func day(_ date: Date, calendar: Calendar = .current) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_GB"); f.calendar = calendar; f.timeZone = calendar.timeZone
        f.dateFormat = "d MMMM"
        return f.string(from: date)
    }

    /// An address as the diagram writes it: the host alone ("100.92.14.7"), without scheme, port or path.
    static func bareAddress(_ text: String) -> String {
        let withScheme = text.contains("://") ? text : "http://" + text
        if let host = URL(string: withScheme)?.host, !host.isEmpty { return host }
        return text.replacingOccurrences(of: "https://", with: "").replacingOccurrences(of: "http://", with: "").trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    }
}

// MARK: Settings > Services tab

struct CupertinoServices: View {
    let state: AppState
    private var services: ServicesController { state.services }
    private var model: ServicesModel { services.model }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.xl) {
            summary
            diagram
            ForEach(ServicesModel.Group.allCases, id: \.self) { group in
                let rows = model.rows(in: group)
                if !rows.isEmpty { groupSection(group, rows) }
            }
            if let e = services.actionError { CUNotice(kind: .danger, lead: "Could not change the service.", message: e) }
        }
        .task { if !services.hasChecked { await state.refreshServices() } }
        .sheet(isPresented: Binding(get: { services.editing != nil }, set: { if !$0 { services.stopEditing() } })) {
            if let id = services.editing { ServiceEditSheet(state: state, id: id) }
        }
        .alert(disconnectTitle, isPresented: Binding(get: { services.confirmingDisconnect != nil }, set: { if !$0 { services.confirmingDisconnect = nil } })) {
            Button("Cancel", role: .cancel) {}
            if let id = services.confirmingDisconnect {
                Button(ServiceEditSpec.disconnectLabel(id, name: ServicesModel.name(for: id)), role: .destructive) { Task { await state.disconnectService(id) } }
            }
        } message: {
            if let id = services.confirmingDisconnect, let row = model.row(id) { Text(ServiceEditSpec.disconnectDetail(id, powers: row.powers)) }
        }
    }

    private var disconnectTitle: String {
        services.confirmingDisconnect.map { "Disconnect \(ServicesModel.name(for: $0))?" } ?? "Disconnect?"
    }

    // MARK: Summary

    private var summary: some View {
        let s = model.summary
        return HStack(alignment: .top, spacing: CU.Space.m) {
            Image(systemName: services.checking && !services.hasChecked ? "ellipsis.circle" : s.tone.symbol).font(.system(size: 32, weight: .regular))
                .foregroundStyle(s.tone.color).frame(width: 32, height: 32).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(s.title).cuRole(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                Text(s.detail).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).frame(maxWidth: 620, alignment: .leading)
            }
            Spacer(minLength: CU.Space.m)
            HStack(spacing: CU.Space.s) {
                if model.toolbar.kind == .unreachable {
                    Button { Task { await state.refreshServices() } } label: { refreshLabel("Try again") }
                        .buttonStyle(CapsuleButtonStyle(primary: true)).disabled(services.checking)
                    Button("Edit address") { state.settingsTab = .profiles }.buttonStyle(CapsuleButtonStyle())
                } else {
                    Button { Task { await state.refreshServices() } } label: { refreshLabel("Check again") }
                        .buttonStyle(CapsuleButtonStyle()).disabled(services.checking)
                }
            }
        }
    }

    private func refreshLabel(_ title: String) -> some View {
        HStack(spacing: CU.Space.xs) {
            if services.checking { ProgressView().controlSize(.small) } else { Image(systemName: "arrow.clockwise").font(.system(size: 12, weight: .semibold)) }
            Text(title)
        }
    }

    // MARK: Diagram

    private var diagram: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text("How Discair is connected").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                .accessibilityAddTraits(.isHeader)
            ServicesDiagram(model: model)
                .frame(height: 200)
        }
        .padding(CU.Space.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    // MARK: Groups and rows

    private func groupSection(_ group: ServicesModel.Group, _ rows: [ServicesModel.Row]) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text(group.rawValue).cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                .padding(.horizontal, CU.Space.m).accessibilityAddTraits(.isHeader)
            VStack(spacing: 0) {
                ForEach(Array(rows.enumerated()), id: \.element.id) { index, row in
                    ServiceRowView(state: state, row: row)
                    if index < rows.count - 1 { Rectangle().fill(CU.separator).frame(height: 1).padding(.leading, 48) }
                }
            }
            .padding(.horizontal, CU.Space.m).padding(.vertical, CU.Space.xs)
            .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            .environment(\.cuInPanel, true)
        }
    }
}

// MARK: One service row

struct ServiceRowView: View {
    let state: AppState
    let row: ServicesModel.Row
    private var services: ServicesController { state.services }
    private var open: Bool { services.expanded.contains(row.id) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button { withAnimation(.easeOut(duration: 0.2)) { services.toggle(row.id) } } label: { header }
                .buttonStyle(.plain)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(row.name). \(row.role). \(row.state.word)")
                .accessibilityValue(open ? "expanded" : "collapsed")
                .accessibilityHint("Shows or hides the details")
                .accessibilityAddTraits(.isButton)
            if open { details.padding(.leading, 48).padding(.bottom, CU.Space.m) }
        }
    }

    private var header: some View {
        HStack(spacing: CU.Space.m) {
            Image(systemName: ServiceIcon.symbol(row.id.rawValue)).font(.system(size: 14)).foregroundStyle(CU.textSecondary)
                .frame(width: 32, height: 32).background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous)).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 0) {
                Text(row.name).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                Text(row.role).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
            }
            .frame(width: 260, alignment: .leading)
            HStack(spacing: CU.Space.xs) {
                ForEach(row.powers, id: \.self) { p in
                    Text(p).font(.system(size: 11, weight: .semibold)).foregroundStyle(CU.textSecondary).lineLimit(1)
                        .padding(.horizontal, CU.Space.s).frame(height: 24).background(CU.bgFillOnPanel, in: Capsule())
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            if row.state == .notSetUp, row.optional, !open {
                // An optional service that is not set up is not a problem: a neutral button, never a warning.
                Button("Set up") { state.editService(row.id); services.expanded.insert(row.id) }.buttonStyle(CapsuleButtonStyle(small: true))
            } else {
                ServiceStateLabel(state: row.state)
            }
            Image(systemName: open ? "chevron.up" : "chevron.down").font(.system(size: 11, weight: .semibold)).foregroundStyle(CU.textSecondary)
                .frame(width: 16).accessibilityHidden(true)
        }
        .frame(minHeight: 56).contentShape(Rectangle())
    }

    // MARK: Expanded

    private var details: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            if let notice = row.notice, row.state.isFailing || (row.state == .notSetUp && !row.optional) {
                CUNotice(kind: row.state.isFailing ? .danger : .warning, lead: noticeLead(notice), message: noticeRest(notice))
            }
            HStack(alignment: .top, spacing: CU.Space.l) {
                column("Status now", rows: statusRows)
                Rectangle().fill(CU.separator).frame(width: 1)
                column("Setup", rows: row.setup.map { ($0.label, $0.value, false) })
            }
            HStack(spacing: CU.Space.s) { ForEach(Array(row.actions.enumerated()), id: \.offset) { _, a in actionButton(a) } }
        }
        .padding(CU.Space.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .accessibilityElement(children: .contain)
    }

    /// The bold lead of a notice is its first sentence: "ListenBrainz did not accept the token."
    private func noticeLead(_ text: String) -> String { String(text.split(separator: ".", maxSplits: 1, omittingEmptySubsequences: true).first.map { $0 + "." } ?? Substring(text)) }
    private func noticeRest(_ text: String) -> String {
        let lead = noticeLead(text)
        return text.hasPrefix(lead) ? String(text.dropFirst(lead.count)).trimmingCharacters(in: .whitespaces) : ""
    }

    /// Answer, since, last good read and when this Mac last checked. A time this Mac has not seen is said so, never left blank.
    private var statusRows: [(String, String, Bool)] {
        let now = services.model.checkedAt
        func when(_ d: Date?, _ missing: String) -> String { d.map { ServicesFormat.when($0, now: now) } ?? missing }
        var out: [(String, String, Bool)] = [("Answer", row.state.word, true)]
        if row.state.isFailing || row.state == .unknown { out.append(("Since", when(row.since, "Not seen yet"), false)) }
        if row.state.isFailing { out.append(("Last good read", when(row.lastGood, "Never seen working"), false)) }
        out.append(("Checked", when(row.checked, "Not checked yet"), false))
        return out
    }

    private func column(_ title: String, rows: [(String, String, Bool)]) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text(title).cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary).accessibilityAddTraits(.isHeader)
            if rows.isEmpty { Text("Nothing to set up here.").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
            ForEach(Array(rows.enumerated()), id: \.offset) { _, r in
                HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
                    Text(r.0).foregroundStyle(CU.textSecondary)
                    Spacer(minLength: CU.Space.s)
                    if r.2 { ServiceStateLabel(state: row.state) } else { Text(r.1).foregroundStyle(CU.text).multilineTextAlignment(.trailing) }
                }
                .font(.system(size: 12))
                .accessibilityElement(children: .combine)
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
    }

    // MARK: Actions

    @ViewBuilder private func actionButton(_ a: ServicesModel.Action) -> some View {
        switch a {
        case .edit: Button("Edit…") { state.editService(row.id) }.buttonStyle(CapsuleButtonStyle())
        case .editAddress: Button("Edit address…") { state.editService(row.id) }.buttonStyle(CapsuleButtonStyle())
        case .setUp: Button("Set up") { state.editService(row.id) }.buttonStyle(CapsuleButtonStyle())
        case .testAgain:
            Button("Test again") { Task { await state.testService(row.id) } }.buttonStyle(CapsuleButtonStyle()).disabled(services.working)
        case .replace(let noun):
            // The one primary of an expanded failing row: the fix, in words.
            Button("Replace \(noun)") { state.editService(row.id) }.buttonStyle(CapsuleButtonStyle(primary: true))
        case .disconnect:
            if ServiceEditSpec.canDisconnect(row.id) {
                Button(ServiceEditSpec.disconnectLabel(row.id, name: row.name)) { services.confirmingDisconnect = row.id }
                    .buttonStyle(CapsuleButtonStyle(outlined: true, destructive: true))
            }
        }
    }
}

// MARK: Diagram

/// The real calls, drawn: This Mac to the Librarian and to Navidrome; the Librarian to Navidrome and to five services. A working
/// line is solid grey, a failing one dashed danger with a danger border on its node, a not-set-up or unknown one dashed light grey.
struct ServicesDiagram: View {
    let model: ServicesModel

    private struct Node { let id: String; let title: String; let subtitle: String?; let state: ServicesModel.State?; let frame: CGRect }

    var body: some View {
        GeometryReader { geo in
            let nodes = layout(geo.size)
            let byID = Dictionary(uniqueKeysWithValues: nodes.map { ($0.id, $0) })
            ZStack(alignment: .topLeading) {
                Canvas { ctx, _ in
                    for edge in model.edges {
                        guard let a = byID[edge.from], let b = byID[edge.to] else { continue }
                        var path = Path()
                        if edge.from == "librarian", edge.to == "navidrome" {
                            path.move(to: CGPoint(x: a.frame.midX, y: a.frame.maxY)); path.addLine(to: CGPoint(x: b.frame.midX, y: b.frame.minY))
                        } else {
                            let start = CGPoint(x: a.frame.maxX, y: a.frame.midY), end = CGPoint(x: b.frame.minX, y: b.frame.midY)
                            let dx = (end.x - start.x) * 0.5
                            path.move(to: start)
                            path.addCurve(to: end, control1: CGPoint(x: start.x + dx, y: start.y), control2: CGPoint(x: end.x - dx, y: end.y))
                        }
                        switch edge.style {
                        case .working: ctx.stroke(path, with: .color(CU.chart2), style: StrokeStyle(lineWidth: 1.5))
                        case .failing: ctx.stroke(path, with: .color(CU.danger), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3]))
                        case .dim: ctx.stroke(path, with: .color(CU.chart3), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3]))
                        }
                    }
                }
                .accessibilityHidden(true)
                ForEach(nodes, id: \.id) { n in
                    nodeView(n).frame(width: n.frame.width, height: n.frame.height).position(x: n.frame.midX, y: n.frame.midY)
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilitySummary)
    }

    private var accessibilitySummary: String {
        let parts = ["This Mac", "Librarian", "Navidrome", "slskd", "Last.fm", "ListenBrainz", "Discogs", "MusicBrainz data"].map { name -> String in
            let state = model.rows.first { $0.name == name }?.state
            return state.map { "\(name): \($0.word)" } ?? name
        }
        return "How Discair is connected. This Mac talks to the Librarian and to Navidrome; the Librarian talks to Navidrome, slskd, Last.fm, ListenBrainz, Discogs and MusicBrainz data. " + parts.joined(separator: ". ") + "."
    }

    private func layout(_ size: CGSize) -> [Node] {
        let w = size.width
        let macW: CGFloat = 148, macH: CGFloat = 44
        let midW = min(340, w * 0.40), midH: CGFloat = 48
        let rightW: CGFloat = min(220, w * 0.26), rightH: CGFloat = 32, pitch: CGFloat = 40
        let midX = w * 0.27
        let rightX = w - rightW
        func row(_ id: ServicesModel.ServiceID) -> ServicesModel.Row? { model.row(id) }
        func sub(_ id: ServicesModel.ServiceID) -> String? {
            guard let r = row(id) else { return nil }
            let address = r.setup.first { $0.label == "Address" }.map { ServicesFormat.bareAddress($0.value) }
            return address.map { "\(r.role) · \($0)" } ?? r.role
        }
        var out = [
            Node(id: "mac", title: "This Mac", subtitle: "Discair app", state: .connected, frame: CGRect(x: 0, y: 100 - macH / 2, width: macW, height: macH)),
            Node(id: "librarian", title: "Librarian", subtitle: sub(.librarian), state: row(.librarian)?.state, frame: CGRect(x: midX, y: 28, width: midW, height: midH)),
            Node(id: "navidrome", title: "Navidrome", subtitle: sub(.navidrome), state: row(.navidrome)?.state, frame: CGRect(x: midX, y: 148, width: midW, height: midH)),
        ]
        for (i, id) in [ServicesModel.ServiceID.slskd, .lastfm, .listenbrainz, .discogs, .musicbrainz].enumerated() {
            out.append(Node(id: id.rawValue, title: ServicesModel.name(for: id), subtitle: nil, state: row(id)?.state, frame: CGRect(x: rightX, y: CGFloat(i) * pitch, width: rightW, height: rightH)))
        }
        return out
    }

    private func nodeView(_ n: Node) -> some View {
        let failing = n.state?.isFailing == true
        return HStack(spacing: CU.Space.s) {
            Image(systemName: ServiceIcon.symbol(n.id)).font(.system(size: 13)).foregroundStyle(CU.textSecondary).frame(width: 20)
            VStack(alignment: .leading, spacing: 0) {
                Text(n.title).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                if let s = n.subtitle { Text(s).cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary).lineLimit(1) }
            }
            Spacer(minLength: 0)
            if let state = n.state { Image(systemName: state.tone.symbol).font(.system(size: 13)).foregroundStyle(state.tone.color) }
        }
        .padding(.horizontal, CU.Space.s)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay { RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(failing ? CU.danger : CU.separatorStrong, lineWidth: 1) }
    }
}

// MARK: Edit sheet

/// Labelled fields, a Test button that reports in a notice, Cancel and Save (section 6.2, item 5). Saving an empty secret keeps
/// the saved one; Test tests what is saved on the server.
struct ServiceEditSheet: View {
    let state: AppState
    let id: ServicesModel.ServiceID
    private var services: ServicesController { state.services }

    var body: some View {
        @Bindable var c = services
        VStack(alignment: .leading, spacing: CU.Space.l) {
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(ServicesModel.name(for: id)).cuRole(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                Text(ServiceEditSpec.summary(id)).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
            }
            VStack(alignment: .leading, spacing: CU.Space.m) {
                ForEach(ServiceEditSpec.fields(id)) { field in
                    CUField(label: field.label, text: Binding(get: { c.draft[field.key] }, set: { c.draft[field.key] = $0 }),
                            placeholder: field.secure && hasSecret ? "••••••••••••••••" : "", help: field.help, secure: field.secure)
                }
            }
            if let n = services.editNotice { CUNotice(kind: n.kind == .success ? .success : .danger, lead: n.lead, message: n.message) }
            HStack(spacing: CU.Space.s) {
                Button("Test") { Task { await state.testFromSheet(id) } }.buttonStyle(CapsuleButtonStyle()).disabled(services.working)
                    .accessibilityHint("Tests what is saved on the server. Save first to try new values.")
                Spacer()
                Button("Cancel") { services.stopEditing() }.buttonStyle(CapsuleButtonStyle()).keyboardShortcut(.cancelAction)
                Button("Save") { Task { await state.saveService(id) } }.buttonStyle(CapsuleButtonStyle(primary: true)).disabled(services.working)
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(CU.Space.l)
        .frame(width: 440)
        .background(CU.content)
        .foregroundStyle(CU.text)
    }

    /// True when the server holds a secret for this service, so the field shows dots and "leave empty to keep it".
    private var hasSecret: Bool {
        let i = services.inputs
        switch id {
        case .navidrome: return i.navidromeSettings?.passwordConfigured == true
        case .slskd: return i.slskdSettings?.apiKeyConfigured == true
        case .lastfm: return i.lastFMSettings?.apiKeyConfigured == true
        case .listenbrainz: return i.listenBrainzSettings?.tokenConfigured == true
        case .discogs: return i.discogsSettings?.tokenConfigured == true
        default: return false
        }
    }
}

// MARK: Toolbar status button and popover

/// Left of Search: an icon and words ("All working", "1 needs attention", "Librarian unreachable", "Checking…"). It opens a popover
/// that lists the services, says what is affected, and offers the fix (primary) and Open Services (section 6.1).
struct CupertinoStatusButton: View {
    let state: AppState
    @State private var open = false
    private var toolbar: ServicesModel.Toolbar { state.services.checking && !state.services.hasChecked ? .init(kind: .checking, text: "Checking…") : state.services.model.toolbar }

    var body: some View {
        Button { open.toggle() } label: {
            HStack(spacing: CU.Space.s) {
                Image(systemName: toolbar.kind == .checking ? "ellipsis.circle" : toolbar.tone.symbol).foregroundStyle(toolbar.tone.color).accessibilityHidden(true)
                Text(toolbar.text).lineLimit(1)
            }
            .font(.system(size: 13, weight: .semibold)).foregroundStyle(CU.text)
            .padding(.horizontal, 14).frame(height: 36).contentShape(Capsule())
            .glassEffect(CU.glass, in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Services: \(toolbar.text)")
        .accessibilityHint("Shows which services work and what is affected")
        .popover(isPresented: $open, arrowEdge: .bottom) {
            CupertinoServicesPopover(state: state) { open = false }
        }
        .task { if !state.services.hasChecked { await state.refreshServices() } }
    }
}

struct CupertinoServicesPopover: View {
    let state: AppState
    let close: () -> Void
    private var model: ServicesModel { state.services.model }

    /// Services worth listing: everything except an optional one that is not set up or switched off.
    private var listed: [ServicesModel.Row] {
        model.rows.filter { !($0.optional && ($0.state == .notSetUp || $0.state == .off)) }
    }

    /// "Playback and Get are not affected." is the tail of the summary's detail; the rest of that sentence is on the row.
    private var affected: String {
        let detail = model.summary.detail
        let parts = detail.components(separatedBy: " · ").first ?? detail
        if let range = parts.range(of: #"[A-Za-z, ]+ (is|are) not affected\."#, options: .regularExpression) { return String(parts[range]).trimmingCharacters(in: .whitespaces) }
        return model.attention.isEmpty ? "Every service you use answered." : ""
    }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(model.summary.title).cuRole(CU.Font.title3).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                if model.toolbar.kind == .unreachable { Text(model.summary.detail).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
                else if !affected.isEmpty { Text(affected).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
            }
            Rectangle().fill(CU.separator).frame(height: 1)
            VStack(alignment: .leading, spacing: CU.Space.s) {
                ForEach(listed) { row in
                    VStack(alignment: .leading, spacing: CU.Space.xs) {
                        HStack(spacing: CU.Space.s) {
                            Image(systemName: ServiceIcon.symbol(row.id.rawValue)).font(.system(size: 13)).foregroundStyle(CU.textSecondary).frame(width: 20).accessibilityHidden(true)
                            Text(row.name).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                            Spacer(minLength: CU.Space.m)
                            ServiceStateLabel(state: row.state)
                        }
                        if let line = impact(row) { Text(line).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).padding(.leading, 28) }
                    }
                    .accessibilityElement(children: .combine)
                }
            }
            Rectangle().fill(CU.separator).frame(height: 1)
            HStack(spacing: CU.Space.s) {
                if let first = model.attention.first {
                    Button(fixTitle(first)) { close(); state.fixService(first.id) }.buttonStyle(CapsuleButtonStyle(primary: true))
                    Button("Open Services") { close(); state.settingsTab = .services; state.screen = .settings }.buttonStyle(CapsuleButtonStyle())
                } else {
                    Button("Open Services") { close(); state.settingsTab = .services; state.screen = .settings }.buttonStyle(CapsuleButtonStyle())
                    Button("Check again") { Task { await state.refreshServices() } }.buttonStyle(CapsuleButtonStyle()).disabled(state.services.checking)
                }
            }
        }
        .padding(CU.Space.m)
        .frame(width: 340)
        .background(CU.content)
        .environment(\.cuInPanel, false)
    }

    private func fixTitle(_ row: ServicesModel.Row) -> String {
        switch row.state {
        case .noAnswer where row.id == .librarian: "Try again"
        default: "Fix \(row.name)"
        }
    }

    /// One sentence on what a failing service affects: the last good data when this Mac has seen the service work, else the notice.
    private func impact(_ row: ServicesModel.Row) -> String? {
        guard row.state.isFailing else { return nil }
        if let good = row.lastGood {
            let powers = row.powers.map { $0.lowercased() }
            let list = powers.count > 1 ? powers.dropLast().joined(separator: ", ") + " and " + powers.last! : (powers.first ?? "")
            return "\(list.prefix(1).uppercased() + list.dropFirst()) \(powers.count > 1 ? "are" : "is") showing the last good data, from \(ServicesFormat.day(good))."
        }
        return row.notice
    }
}
