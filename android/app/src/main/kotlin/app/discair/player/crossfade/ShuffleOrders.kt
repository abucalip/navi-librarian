package app.discair.player.crossfade

/**
 * The playback order of a shuffled queue, read from a player, so the second player can be given the same order
 * (contract 13, rule 4). [first] is the first index in play order; [next] gives the one after a given index or a
 * negative number at the end. Returns null if the walk does not visit every index exactly once (then the caller
 * leaves the order alone rather than apply a wrong one).
 */
object ShuffleOrders {
    fun walk(count: Int, first: Int, next: (Int) -> Int): IntArray? {
        if (count <= 0) return IntArray(0)
        val order = IntArray(count)
        val seen = BooleanArray(count)
        var i = first
        for (n in 0 until count) {
            if (i !in 0 until count || seen[i]) return null
            seen[i] = true
            order[n] = i
            i = if (n == count - 1) -1 else next(i)
        }
        return order
    }
}
