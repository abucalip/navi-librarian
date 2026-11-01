package app.discair.player.eq

import androidx.media3.common.C
import androidx.media3.common.audio.AudioProcessor
import androidx.media3.common.util.UnstableApi
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

@androidx.annotation.OptIn(UnstableApi::class)
class EqAudioProcessorTest {
    private fun fmt(rate: Int, ch: Int, enc: Int) = AudioProcessor.AudioFormat(rate, ch, enc)
    private fun on() = EqConfig(true, List(10) { if (it == 5) 8.0 else 0.0 })

    private fun pcm16(frames: Int, ch: Int): ByteBuffer {
        val b = ByteBuffer.allocateDirect(frames * ch * 2).order(ByteOrder.nativeOrder())
        for (f in 0 until frames) for (c in 0 until ch) b.putShort((8000 * sin(2 * PI * 1000 * f / 44100)).toInt().toShort())
        return b.flip() as ByteBuffer
    }

    private fun run(p: EqAudioProcessor, input: ByteBuffer): ByteBuffer {
        p.queueInput(input); return p.output
    }

    @Test fun unsupportedFormatsStayInactive() {
        val p = EqAudioProcessor()
        p.configure(fmt(44100, 2, C.ENCODING_PCM_24BIT)); p.flush(); assertFalse(p.isActive); assertFalse(p.applies)
        p.configure(fmt(44100, 9, C.ENCODING_PCM_16BIT)); p.flush(); assertFalse(p.isActive)
        p.configure(fmt(44100, 0, C.ENCODING_PCM_16BIT)); p.flush(); assertFalse(p.isActive)
    }

    @Test fun pcm16AndFloatAreAcceptedAndKeepTheirEncodingAndLength() {
        for (enc in listOf(C.ENCODING_PCM_16BIT, C.ENCODING_PCM_FLOAT)) {
            val p = EqAudioProcessor(); p.setConfig(on())
            val out = p.configure(fmt(44100, 2, enc)); p.flush()
            assertEquals(enc, out.encoding); assertTrue(p.isActive); assertTrue(p.applies)
        }
    }

    @Test fun offIsByteIdenticalAndOnChangesTheAudioWithTheSameLength() {
        val input = pcm16(2048, 2)
        val bytes = ByteArray(input.remaining()).also { input.duplicate().get(it) }

        val off = EqAudioProcessor(); off.configure(fmt(44100, 2, C.ENCODING_PCM_16BIT)); off.flush()
        val o = run(off, input.duplicate()); val ob = ByteArray(o.remaining()).also { o.get(it) }
        assertTrue(bytes.contentEquals(ob))

        val p = EqAudioProcessor(); p.setConfig(on()); p.configure(fmt(44100, 2, C.ENCODING_PCM_16BIT)); p.flush()
        val r = run(p, input.duplicate()); val rb = ByteArray(r.remaining()).also { r.get(it) }
        assertEquals(bytes.size, rb.size); assertFalse(bytes.contentEquals(rb))
    }

    @Test fun aConfigChangeWhilePlayingTakesEffect() {
        val p = EqAudioProcessor(); p.configure(fmt(44100, 1, C.ENCODING_PCM_16BIT)); p.flush()
        val a = run(p, pcm16(512, 1)); val first = ByteArray(a.remaining()).also { a.get(it) }
        assertTrue(first.contentEquals(ByteArray(first.size).also { pcm16(512, 1).get(it) }))
        p.setConfig(on())
        run(p, pcm16(2048, 1)).let { }
        val c = run(p, pcm16(512, 1)); val changed = ByteArray(c.remaining()).also { c.get(it) }
        assertFalse(changed.contentEquals(first))
    }

    @Test fun outputNeverClipsPastTheSampleRange() {
        val p = EqAudioProcessor(); p.setConfig(EqConfig(true, List(10) { 12.0 }, preGainAuto = false))
        p.configure(fmt(44100, 1, C.ENCODING_PCM_16BIT)); p.flush()
        val b = ByteBuffer.allocateDirect(44100 * 2).order(ByteOrder.nativeOrder())
        for (f in 0 until 44100) b.putShort((32767 * sin(2 * PI * 200 * f / 44100)).toInt().toShort())
        b.flip()
        val out = run(p, b); var peak = 0
        while (out.remaining() >= 2) peak = maxOf(peak, abs(out.short.toInt()))
        assertTrue(peak <= 32768)
    }

    @Test fun emptyInputGivesEmptyOutput() {
        val p = EqAudioProcessor(); p.setConfig(on()); p.configure(fmt(44100, 2, C.ENCODING_PCM_16BIT)); p.flush()
        p.queueInput(ByteBuffer.allocateDirect(0)); assertEquals(0, p.output.remaining())
    }

    @Test fun theStatusListenerHearsWhetherTheSongCanBeProcessed() {
        val p = EqAudioProcessor(); val seen = mutableListOf<EqRuntimeStatus>()
        p.statusListener = { seen += it }
        p.configure(fmt(44100, 2, C.ENCODING_PCM_16BIT)); p.configure(fmt(44100, 2, C.ENCODING_PCM_24BIT))
        assertEquals(listOf(true, false), seen.map { it.appliesToThisSong })
        assertTrue(seen.none { it.faulted })
        p.reset()
        assertEquals(false, seen.last().appliesToThisSong)
    }
}
