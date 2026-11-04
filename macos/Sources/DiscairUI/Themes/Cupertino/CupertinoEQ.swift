import DiscairAudio
import SwiftUI

/// Equalizer: a switch, a preset menu, ten bands with minus and plus buttons (no gesture is the only way), pre-gain and
/// Reset. No mockup exists; it follows Cupertino's rules. Contract: `ANDROID_EQ_CONTRACT.md` sections 5 and 7.
struct CupertinoEQ: View {
    let state: AppState
    @State private var confirmReset = false
    private var p: PlayerModel { state.player }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Equalizer").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                card {
                    HStack {
                        Toggle("Equalizer", isOn: Binding(get: { p.eq.enabled }, set: { v in p.updateEQ { $0.enabled = v } }))
                            .toggleStyle(.switch).tint(.green).fontWeight(.semibold)
                        Spacer()
                        Text(p.eq.enabled ? "On: \(p.eq.presetLabel)" : "Off. Settings are kept.").foregroundStyle(CU.muted)
                    }
                    HStack(spacing: 8) {
                        Text("Preset").fontWeight(.semibold)
                        Menu(p.eq.presetLabel) {
                            ForEach(eqPresets) { pr in Button(pr.label) { p.updateEQ { $0.choose(preset: pr.id) } } }
                            Divider()
                            Button("Custom") { p.updateEQ { $0.choose(preset: EQSettings.customID) } }
                        }
                        .fixedSize()
                        Spacer()
                        Button("Reset") { confirmReset = true }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                    }
                }
                card {
                    HStack(alignment: .top, spacing: 6) {
                        ForEach(0..<10, id: \.self) { i in band(i) }
                    }
                    .opacity(p.eq.enabled ? 1 : 0.5)
                }
                card {
                    HStack {
                        Toggle("Automatic pre-gain", isOn: Binding(get: { p.eq.preGainAuto }, set: { v in p.updateEQ { $0.preGainAuto = v } }))
                            .toggleStyle(.switch).tint(.green)
                        Spacer()
                        Text(String(format: "%+.1f dB", p.eq.preGainDB)).monospacedDigit().foregroundStyle(CU.muted)
                    }
                    if !p.eq.preGainAuto {
                        HStack(spacing: 10) {
                            Button("−") { p.updateEQ { $0.preGainManual = max(-eqMaxGainDB, $0.preGainManual - eqStepDB) } }
                                .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Lower pre-gain")
                            Button("+") { p.updateEQ { $0.preGainManual = min(0, $0.preGainManual + eqStepDB) } }
                                .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Raise pre-gain")
                        }
                    }
                    Text("Pre-gain lowers the signal before the bands so a boost does not clip. Automatic uses the largest boost.")
                        .font(.system(size: 12)).foregroundStyle(CU.muted)
                }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .confirmationDialog("Reset the equalizer?", isPresented: $confirmReset, titleVisibility: .visible) {
            Button("Reset to Flat", role: .destructive) { p.updateEQ { $0.reset() } }
            Button("Cancel", role: .cancel) {}
        } message: { Text("This sets every band to 0 dB and clears your Custom curve.") }
    }

    private func card<C: View>(@ViewBuilder _ c: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 12) { c() }
            .padding(18).frame(maxWidth: .infinity, alignment: .leading)
            .background(CU.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private func band(_ i: Int) -> some View {
        let g = p.eq.gains[i]
        let hz = eqBandHz[i] >= 1000 ? "\(eqBandHz[i] / 1000) kHz" : "\(eqBandHz[i]) Hz"
        return VStack(spacing: 6) {
            Text(String(format: "%+.1f", g)).font(.system(size: 12, weight: .semibold)).monospacedDigit()
            Button("+") { p.updateEQ { $0.nudge(band: i, steps: 1) } }
                .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Raise \(hz)")
            ZStack(alignment: .top) {
                Capsule().fill(CU.fill).frame(width: 6, height: 120)
                let h = max(g == 0 ? 0 : 2, 60 * abs(g) / eqMaxGainDB)      // the middle (0 dB) is at 60 pt
                Capsule().fill(CU.accent).frame(width: 6, height: h).offset(y: g >= 0 ? 60 - h : 60)
                Rectangle().fill(CU.muted).frame(width: 12, height: 1.5).offset(y: 59)
            }
            .frame(height: 120)
            .eqBandDrag(trackHeight: 120) { db in p.updateEQ { $0.set(band: i, db: db) } }
            .accessibilityHidden(true)
            Button("−") { p.updateEQ { $0.nudge(band: i, steps: -1) } }
                .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Lower \(hz)")
            Text(hz).font(.system(size: 11)).foregroundStyle(CU.muted).lineLimit(1)
        }
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(hz), \(String(format: "%+.1f", g)) decibels")
    }
}
