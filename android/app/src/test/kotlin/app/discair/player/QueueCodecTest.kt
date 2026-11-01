package app.discair.player

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class QueueCodecTest {
    private fun song(i: Int) = QueueItem("s$i", "T$i", "A", "Al", "al1", "c$i", 180)
    private val saved = QueueState().replace((1..4).map(::song), 2).state
        .withPosition(51_000).withRepeat(RepeatMode.All).withVolume(0.5f)

    @Test fun roundTripRestoresQueueIndexAndPosition() {
        val back = QueueCodec.decode(QueueCodec.encode(saved))
        assertEquals(saved.items, back.items); assertEquals(2, back.index); assertEquals(51_000, back.positionMs)
        assertEquals(RepeatMode.All, back.repeat); assertEquals(0.5f, back.volume, 0f)
    }

    @Test fun shuffleIsRestoredStartingAtTheCurrentSong() {
        val back = QueueCodec.decode(QueueCodec.encode(saved.withShuffle(true)))
        assertTrue(back.shuffle); assertEquals(2, back.shuffleOrder.first()); assertEquals(4, back.shuffleOrder.size)
    }

    @Test fun corruptOrOldDataGivesAnEmptyQueue() {
        for (text in listOf(null, "", "  ", "{", "not json", "[]", "{\"v\":99}", "{\"v\":1,\"items\":\"x\"}", "{\"v\":1,\"index\":\"a\"}")) {
            assertTrue("<$text>", QueueCodec.decode(text).isEmpty)
        }
    }

    @Test fun hostileValuesAreClamped() {
        val text = """{"v":1,"items":[{"songId":"ok1","title":"t","artist":"a","album":"b"},{"songId":"bad/id","title":"t","artist":"a","album":"b"}],
            "index":99,"positionMs":-5,"repeat":"Bogus","volume":9.0}"""
        val q = QueueCodec.decode(text)
        assertEquals(listOf("ok1"), q.items.map { it.songId }); assertEquals(0, q.index)
        assertEquals(0, q.positionMs); assertEquals(RepeatMode.Off, q.repeat); assertEquals(1f, q.volume, 0f)
    }

    @Test fun oversizedQueueIsCut() {
        val items = (1..600).joinToString(",") { """{"songId":"s$it","title":"t","artist":"a","album":"b"}""" }
        assertEquals(MAX_QUEUE, QueueCodec.decode("""{"v":1,"items":[$items]}""").items.size)
    }

    @Test fun fileStorageWritesReadsAndClears() {
        val dir = kotlin.io.path.createTempDirectory().toFile()
        val storage = FileQueueStorage(File(dir, "q.json"))
        assertEquals(null, storage.read())
        storage.write("one"); storage.write("two")
        assertEquals("two", storage.read())
        storage.clear(); assertEquals(null, storage.read())
        dir.deleteRecursively()
    }
}
