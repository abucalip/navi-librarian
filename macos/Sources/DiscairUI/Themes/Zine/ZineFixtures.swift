import Foundation

/// Sample copy that only the Zine mockup carries (stories, bios, running order, artist index).
enum ZineFixtures {
    static let leadStory: (headline: String, p1: String, p2: String) = (
        "A double album that you have never owned.",
        " You play Talk Talk and Boards of Canada every week, and Librarian ranks this record as the strongest gap behind them: long, patient, rhythm-first.",
        "Two discs, a Damo Suzuki vocal that sounds like a transmission, and drums that carry the whole second half. Classic status is why it is in the paper."
    )
    static let classifieds = ["The Colour of Spring", "The Party's Over", "Zombie"]

    static let albumLede = "The last record before the band went quiet."
    static let albumBody1 = " Recorded over a year of nights in a dim studio, mixed more by what was left out than what stayed in."
    static let albumBody2 = "Six pieces, no singles. Best heard in one sitting, which is why it is gapless here."
    static let albumPull = "\u{201C}Silence as an instrument, room sound as the lead.\u{201D}"

    static let lyrics = [
        "A slow tide under the floorboards", "the lamp keeps counting what we left", "one long note, then the room agrees",
        "nobody here is in a hurry", "the water finds its level", "and the level finds us",
    ]

    /// Running order: (title, album index, time). The playing row is index 1.
    static let runningOrder: [(title: String, album: Int, time: String)] = [
        ("Myrrhman", 0, "3:12"), ("After the Flood", 2, "9:41"), ("Glory Box", 3, "5:44"), ("Cloudbusting", 4, "6:52"),
        ("Maria También", 5, "4:47"), ("So What", 6, "8:46"), ("Such a Shame", 13, "4:49"), ("I Believe in You", 1, "3:12"),
    ]
    static let playingIndex = 1

    static let artistIndex: [(String, Int)] = [
        ("Talk Talk", 3), ("Tangerine Dream", 2), ("Television", 1), ("Tindersticks", 4), ("Tony Allen", 3), ("Tortoise", 5),
        ("Toots & the Maytals", 2), ("Tom Waits", 9), ("Tricky", 3), ("Trentemøller", 2), ("T. Rex", 4), ("Throbbing Gristle", 1),
        ("The Tallest Man on Earth", 2), ("The The", 2), ("Thievery Corporation", 3), ("Tom Tom Club", 1), ("Tame Impala", 4),
        ("Tinariwen", 3), ("Todd Rundgren", 6), ("Tori Amos", 5), ("Toro y Moi", 3), ("Tune-Yards", 2), ("Talking Heads", 8),
        ("Tangerine", 1), ("Tori", 2), ("Tortoise II", 1), ("Trio", 2), ("Tuxedomoon", 3), ("Twin Shadow", 2), ("Tycho", 4),
        ("Tyondai Braxton", 1),
    ]

    static let coverLines = ["Life's What You Make It", "Such a Shame", "Myrrhman"]
    static let backIssues = [12, 13, 11, 1, 0]
    static let alsoInThisIssue = ["Mark Hollis", "Bark Psychosis", "David Sylvian", "Japan"]
    static let artistBio = "Bio: the band that left synth-pop behind and kept leaving."
}
