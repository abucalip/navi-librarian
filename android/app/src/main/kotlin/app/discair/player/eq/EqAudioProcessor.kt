package app.discair.player.eq

import androidx.annotation.OptIn
import androidx.media3.common.C
import androidx.media3.common.audio.AudioProcessor
import androidx.media3.common.audio.BaseAudioProcessor
import androidx.media3.common.util.UnstableApi
import java.nio.ByteBuffer

/**
 * Media3 adapter around [EqEngine]. Handles 16-bit and float PCM with 1 to 8 channels; any other format is left
 * inactive, so ExoPlayer passes it through untouched (ANDROID_EQ_CONTRACT.md 4). Output keeps the input encoding.
 * A fault inside the engine switches this processor to plain copy for the rest of the stream; it never throws
 * into the player (contract 8).
 */
@OptIn(UnstableApi::class)
class EqAudioProcessor : BaseAudioProcessor() {
    @Volatile private var pending: EqConfig = EqConfig()
    @Volatile private var configVersion = 0
    private var appliedVersion = -1
    private var engine: EqEngine? = null
    private var faulted = false
    private var scratch = FloatArray(0)

    /** True when the last configure accepted the format, so the EQ can be applied to the current song. */
    @Volatile var applies: Boolean = false
        private set

    /** True when a fault made the processor copy audio unchanged. */
    @Volatile var hasFaulted: Boolean = false
        private set

    fun setConfig(config: EqConfig) {
        pending = config.sanitized()
        configVersion++
    }

    override fun onConfigure(inputAudioFormat: AudioProcessor.AudioFormat): AudioProcessor.AudioFormat {
        val ok = inputAudioFormat.channelCount in 1..8 &&
            (inputAudioFormat.encoding == C.ENCODING_PCM_16BIT || inputAudioFormat.encoding == C.ENCODING_PCM_FLOAT)
        applies = ok
        return if (ok) inputAudioFormat else AudioProcessor.AudioFormat.NOT_SET
    }

    override fun onFlush() {
        engine = null
        appliedVersion = -1
        faulted = false
        hasFaulted = false
    }

    override fun onReset() {
        engine = null
        applies = false
    }

    override fun queueInput(inputBuffer: ByteBuffer) {
        val start = inputBuffer.position()
        val size = inputBuffer.remaining()
        if (size == 0) return
        val out = replaceOutputBuffer(size)
        if (faulted) { out.put(inputBuffer); out.flip(); return }
        try {
            val fmt = inputAudioFormat
            val eng = engine ?: EqEngine(fmt.sampleRate, fmt.channelCount).also { engine = it; appliedVersion = -1 }
            if (appliedVersion != configVersion) { appliedVersion = configVersion; eng.setConfig(pending) }
            if (eng.isBypassing) { out.put(inputBuffer); out.flip(); return }
            val bytesPer = if (fmt.encoding == C.ENCODING_PCM_FLOAT) 4 else 2
            val frameBytes = bytesPer * fmt.channelCount
            val frames = size / frameBytes
            val samples = frames * fmt.channelCount
            if (scratch.size < samples) scratch = FloatArray(samples)
            val pos = inputBuffer.position()
            if (bytesPer == 4) for (i in 0 until samples) scratch[i] = inputBuffer.getFloat(pos + i * 4)
            else for (i in 0 until samples) scratch[i] = inputBuffer.getShort(pos + i * 2) / 32768f
            eng.process(scratch, frames)
            if (bytesPer == 4) for (i in 0 until samples) out.putFloat(scratch[i])
            else for (i in 0 until samples) {
                out.putShort(Math.round(scratch[i] * 32768f).coerceIn(-32768, 32767).toShort())
            }
            inputBuffer.position(pos + samples * bytesPer)
            // A trailing partial frame (not expected from a decoder) is copied unchanged.
            if (inputBuffer.hasRemaining()) out.put(inputBuffer)
            out.flip()
        } catch (e: Exception) {
            faulted = true; hasFaulted = true
            out.clear()
            inputBuffer.position(start)
            out.put(inputBuffer)
            out.flip()
        }
    }
}
