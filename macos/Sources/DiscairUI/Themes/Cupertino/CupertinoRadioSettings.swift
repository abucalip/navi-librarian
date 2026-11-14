import AppKit
import DiscairLibrarian
import SwiftUI
import UniformTypeIdentifiers

/// Settings › Radio (docs/RADIO_PLAYBACK_PROPOSAL.md S2-4 item 3), in the same grouped rows as Playback: the scrobbling switch
/// (disabled with its reason when Last.fm is not set up on the server), the app address read only, and for each station a
/// logo with Change (an open panel, images up to 2 MB) and Reset. The menu bar switches join from S2-5.
struct CupertinoRadioSettings: View {
    let state: AppState

    private var model: RadioSettingsModel { state.radioSettings }
    private var stations: StationsModel { state.stations }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            if case .failed(let message) = model.phase {
                HStack(spacing: CU.Space.s) {
                    CUNotice(kind: .danger, lead: "Radio settings could not be read.", message: message)
                    Button("Try again") { Task { await model.load() } }.buttonStyle(CapsuleButtonStyle(small: true))
                }
            }
            CUPanel {
                row("Scrobble radio songs", detail: model.scrobblingDetail) {
                    Toggle("Scrobble radio songs", isOn: Binding(get: { model.scrobblingOn }, set: { on in Task { await model.setScrobbling(on) } }))
                        .labelsHidden().toggleStyle(.switch).tint(CU.accent).disabled(!model.canSwitchScrobbling)
                }
                Divider()
                row("App address", detail: "Changed on the web Radio page") {
                    Text(model.appAddressText).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                        .lineLimit(1).truncationMode(.middle).textSelection(.enabled)
                        .accessibilityLabel("App address, \(model.appAddressText)")
                }
            }
            CUPanel("Station logos") { stationLogos }
            if let note = model.note { CUNotice(kind: .danger, lead: "Could not save.", message: note) }
        }
        .task {
            await model.load()
            if stations.stations.isEmpty, stations.phase != .loading { await stations.reload() }
        }
    }

    @ViewBuilder private var stationLogos: some View {
        if stations.stations.isEmpty {
            Text(stations.phase == .loading ? "Reading the stations…" : "No stations yet. Add one in Navidrome and it appears here.")
                .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).padding(.vertical, CU.Space.s)
        } else {
            VStack(spacing: 0) {
                ForEach(Array(stations.stations.enumerated()), id: \.element.id) { i, station in
                    if i > 0 { Divider() }
                    HStack(spacing: CU.Space.m) {
                        StationLogo(station: station, size: 34)
                        Text(station.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        let busy = model.busyLogos.contains(station.id)
                        Button("Change…") { chooseImage(for: station) }
                            .buttonStyle(CapsuleButtonStyle(small: true)).disabled(busy)
                            .accessibilityLabel("Change the logo of \(station.name)")
                        Button("Reset") { Task { await model.resetLogo(station: station.id) } }
                            .buttonStyle(CapsuleButtonStyle(small: true, outlined: true)).disabled(busy)
                            .accessibilityLabel("Reset the logo of \(station.name)")
                    }
                    .padding(.vertical, CU.Space.s)
                    .accessibilityElement(children: .contain)
                }
            }
        }
    }

    /// One settings row: words on the left, the control on the trailing edge (the shape of Playback's rows).
    private func row<Control: View>(_ title: String, detail: String, @ViewBuilder control: () -> Control) -> some View {
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

    /// The open panel: one image, up to 2 MB. The size is read before the file is, so a large file is never loaded.
    private func chooseImage(for station: RadioStation) {
        let panel = NSOpenPanel()
        panel.title = "Logo for \(station.name)"
        panel.message = "Choose an image up to 2 MB."
        panel.prompt = "Use Image"
        panel.allowedContentTypes = [.image]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        let size = (try? url.resourceValues(forKeys: [.fileSizeKey]))?.fileSize ?? 0
        if let problem = RadioSettingsModel.problem(withImageOfSize: size) { model.showNote(problem); return }
        guard let data = try? Data(contentsOf: url) else { model.showNote("The image could not be read."); return }
        let type = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        Task { await model.changeLogo(station: station.id, image: data, contentType: type) }
    }
}
