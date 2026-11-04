import DiscairAudio
import SwiftUI

/// Equalizer: "The Mixing Desk". No mockup exists; it uses Zine's parts. Each band has plus and minus buttons, so no
/// gesture is the only way. Contract: `ANDROID_EQ_CONTRACT.md` sections 5 and 7.
struct ZineEQ: View {
    let state: AppState
    @State private var confirmReset = false
    private var p: PlayerModel { state.player }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Equalizer").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("The Mixing Desk · \(p.eq.enabled ? "On: \(p.eq.presetLabel)" : "Off")").padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }

            HStack(spacing: 10) {
                Button(p.eq.enabled ? "Equalizer: On" : "Equalizer: Off") { p.updateEQ { $0.enabled.toggle() } }
                    .buttonStyle(ZineButtonStyle(kind: p.eq.enabled ? .yellow : .plain))
                    .accessibilityAddTraits(p.eq.enabled ? .isSelected : [])
                Mono("Preset:", bold: true)
                ForEach(eqPresets) { pr in
                    Button(pr.label) { p.updateEQ { $0.choose(preset: pr.id) } }
                        .buttonStyle(ZineButtonStyle(kind: p.eq.presetID == pr.id ? .yellow : .plain, small: true))
                        .accessibilityAddTraits(p.eq.presetID == pr.id ? .isSelected : [])
                }
                Button("Custom") { p.updateEQ { $0.choose(preset: EQSettings.customID) } }
                    .buttonStyle(ZineButtonStyle(kind: p.eq.presetID == EQSettings.customID ? .yellow : .plain, small: true))
                Spacer()
                Button("Reset") { confirmReset = true }.buttonStyle(ZineButtonStyle(small: true))
            }
            .fixedSize(horizontal: false, vertical: true)

            HStack(alignment: .top, spacing: 0) {
                ForEach(0..<10, id: \.self) { i in
                    band(i)
                    if i < 9 { Rectangle().fill(Z.ink).frame(width: 2) }
                }
            }
            .background(Z.white).zBorder(3).opacity(p.eq.enabled ? 1 : 0.55)

            HStack(spacing: 12) {
                Button(p.eq.preGainAuto ? "Pre-gain: Automatic" : "Pre-gain: Manual") { p.updateEQ { $0.preGainAuto.toggle() } }
                    .buttonStyle(ZineButtonStyle(small: true))
                Mono(String(format: "%+.1f dB", p.eq.preGainDB), bold: true)
                if !p.eq.preGainAuto {
                    Button("−") { p.updateEQ { $0.preGainManual = max(-eqMaxGainDB, $0.preGainManual - eqStepDB) } }
                        .buttonStyle(ZineButtonStyle(small: true)).accessibilityLabel("Lower pre-gain")
                    Button("+") { p.updateEQ { $0.preGainManual = min(0, $0.preGainManual + eqStepDB) } }
                        .buttonStyle(ZineButtonStyle(small: true)).accessibilityLabel("Raise pre-gain")
                }
                Text("Lowers the signal before the bands so a boost does not clip.").font(Z.serif(13))
            }
        }
        .confirmationDialog("Reset the equalizer?", isPresented: $confirmReset, titleVisibility: .visible) {
            Button("Reset to Flat", role: .destructive) { p.updateEQ { $0.reset() } }
            Button("Cancel", role: .cancel) {}
        } message: { Text("This sets every band to 0 dB and clears your Custom curve.") }
    }

    private func band(_ i: Int) -> some View {
        let g = p.eq.gains[i]
        let hz = eqBandHz[i] >= 1000 ? "\(eqBandHz[i] / 1000) kHz" : "\(eqBandHz[i]) Hz"
        return VStack(spacing: 6) {
            Mono(String(format: "%+.1f", g), bold: true)
            ZStack(alignment: .top) {
                Rectangle().fill(Z.paper).frame(width: 14, height: 130).zBorder(2)
                let h = max(g == 0 ? 0 : 2, 63 * abs(g) / eqMaxGainDB)      // the middle (0 dB) is at 65 pt
                Rectangle().fill(Z.yellow).frame(width: 10, height: h).offset(y: g >= 0 ? 65 - h : 65)
                Rectangle().fill(Z.ink).frame(width: 14, height: 2).offset(y: 64)
            }
            .frame(height: 130).accessibilityHidden(true)
            Button("+") { p.updateEQ { $0.nudge(band: i, steps: 1) } }.buttonStyle(ZineButtonStyle(small: true)).accessibilityLabel("Raise \(hz)")
            Button("−") { p.updateEQ { $0.nudge(band: i, steps: -1) } }.buttonStyle(ZineButtonStyle(small: true)).accessibilityLabel("Lower \(hz)")
            Mono(hz, size: 10)
        }
        .padding(.vertical, 10).frame(maxWidth: .infinity)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(hz), \(String(format: "%+.1f", g)) decibels")
    }
}
