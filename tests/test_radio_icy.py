import unittest

from integrations.radio.icy import IcyParser, split_artist_title, stream_title


def block(text: str) -> bytes:
    raw = text.encode()
    padded = raw + b"\x00" * (-len(raw) % 16)
    return bytes([len(padded) // 16]) + padded


class IcyParserTests(unittest.TestCase):
    def stream(self, metaint=8):
        return (b"A" * metaint + block("StreamTitle='Pink Floyd - Time';") +
                b"B" * metaint + b"\x00" + b"C" * metaint + block("StreamTitle='Queen - Radio Ga Ga';"))

    def collect(self, chunks, metaint=8):
        parser = IcyParser(metaint)
        audio, titles = b"", []
        for chunk in chunks:
            for kind, data in parser.feed(chunk):
                if kind == "audio":
                    audio += data
                else:
                    titles.append(stream_title(data))
        return audio, titles

    def test_whole_stream(self):
        audio, titles = self.collect([self.stream()])
        self.assertEqual(audio, b"A" * 8 + b"B" * 8 + b"C" * 8)
        self.assertEqual(titles, ["Pink Floyd - Time", "Queen - Radio Ga Ga"])

    def test_every_chunk_size_gives_the_same_result(self):
        data = self.stream()
        expected = self.collect([data])
        for size in range(1, len(data) + 1):
            chunks = [data[i:i + size] for i in range(0, len(data), size)]
            self.assertEqual(self.collect(chunks), expected, size)

    def test_rejects_non_positive_metaint(self):
        with self.assertRaises(ValueError):
            IcyParser(0)


class TitleTests(unittest.TestCase):
    def test_stream_title_with_apostrophe_and_latin1(self):
        self.assertEqual(stream_title(b"StreamTitle='Guns N' Roses - Don't Cry';StreamUrl='';\x00"),
                         "Guns N' Roses - Don't Cry")
        self.assertEqual(stream_title("StreamTitle='Caf\xe9 - Ol\xe9';".encode("latin-1")), "Caf\xe9 - Ol\xe9")

    def test_block_without_title(self):
        self.assertIsNone(stream_title(b"StreamUrl='x';"))

    def test_split(self):
        self.assertEqual(split_artist_title("AC/DC - Back In Black"), ("AC/DC", "Back In Black"))
        self.assertEqual(split_artist_title("Artist - Song - Live"), ("Artist", "Song - Live"))
        self.assertEqual(split_artist_title("Jingle"), (None, "Jingle"))
        self.assertEqual(split_artist_title("Wham-O"), (None, "Wham-O"))


if __name__ == "__main__":
    unittest.main()
