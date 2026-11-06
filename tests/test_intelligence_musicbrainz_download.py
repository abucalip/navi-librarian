import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from intelligence.musicbrainz import download

DATA = bytes(range(256)) * 40


class FakeResponse:
    def __init__(self, body, status=200, headers=None, fail_after=None):
        self._body, self.status, self.headers, self._fail_after = body, status, headers or {}, fail_after
        self._pos = 0
        self.closed = False

    def read(self, n=-1):
        if self._fail_after is not None and self._pos >= self._fail_after:
            raise OSError("connection reset")
        end = len(self._body) if n < 0 else self._pos + n
        if self._fail_after is not None:
            end = min(end, self._fail_after)
        chunk = self._body[self._pos:end]
        self._pos += len(chunk)
        return chunk

    def close(self):
        self.closed = True


def server(data=DATA, honour_range=True, fail_first_after=None):
    calls = []

    def opener(url, headers):
        calls.append(headers)
        rng = headers.get("Range")
        fail = fail_first_after if len(calls) == 1 else None
        if rng and honour_range:
            start = int(rng.split("=")[1].rstrip("-"))
            if start >= len(data):
                return FakeResponse(b"", 416)
            return FakeResponse(data[start:], 206, {"Content-Range": f"bytes {start}-{len(data)-1}/{len(data)}"})
        return FakeResponse(data, 200, {"Content-Length": str(len(data))}, fail_after=fail)

    opener.calls = calls
    return opener


SHA = hashlib.sha256(DATA).hexdigest()


class ChecksumParseTests(unittest.TestCase):
    def test_parses_text_and_binary_markers(self):
        text = f"{SHA}  mbdump.tar.bz2\n{'a'*64} *other.tar.bz2\nbad line\n"
        self.assertEqual(download.parse_sha256sums(text), {"mbdump.tar.bz2": SHA, "other.tar.bz2": "a" * 64})


class DownloadFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "mbdump.tar.bz2"
        self.addCleanup(self.tmp.cleanup)

    def test_fresh_download_verifies_and_renames(self):
        download.download_file("u", self.dest, SHA, server(), reserve_bytes=0)
        self.assertEqual(self.dest.read_bytes(), DATA)
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_resumes_from_partial_file_with_range(self):
        self.dest.with_name(self.dest.name + ".part").write_bytes(DATA[:1000])
        opener = server()
        download.download_file("u", self.dest, SHA, opener, reserve_bytes=0)
        self.assertEqual(opener.calls, [{"Range": "bytes=1000-"}])
        self.assertEqual(self.dest.read_bytes(), DATA)

    def test_connection_drop_is_retried_and_resumed(self):
        opener = server(fail_first_after=500)
        download.download_file("u", self.dest, SHA, opener, reserve_bytes=0)
        self.assertEqual(opener.calls[1], {"Range": "bytes=500-"})
        self.assertEqual(self.dest.read_bytes(), DATA)

    def test_server_ignoring_range_restarts_from_zero(self):
        self.dest.with_name(self.dest.name + ".part").write_bytes(b"junk-prefix")
        download.download_file("u", self.dest, SHA, server(honour_range=False), reserve_bytes=0)
        self.assertEqual(self.dest.read_bytes(), DATA)

    def test_complete_part_file_is_verified_without_refetch(self):
        self.dest.with_name(self.dest.name + ".part").write_bytes(DATA)
        download.download_file("u", self.dest, SHA, server(), reserve_bytes=0)
        self.assertEqual(self.dest.read_bytes(), DATA)

    def test_checksum_mismatch_removes_partial_and_raises(self):
        with self.assertRaises(download.DownloadError):
            download.download_file("u", self.dest, "0" * 64, server(), reserve_bytes=0)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_existing_good_file_is_kept_without_a_request(self):
        self.dest.write_bytes(DATA)
        opener = server()
        download.download_file("u", self.dest, SHA, opener, reserve_bytes=0)
        self.assertEqual(opener.calls, [])

    def test_existing_file_with_wrong_checksum_is_never_overwritten(self):
        self.dest.write_bytes(b"other")
        with self.assertRaises(download.DownloadError):
            download.download_file("u", self.dest, SHA, server(), reserve_bytes=0)
        self.assertEqual(self.dest.read_bytes(), b"other")

    def test_refuses_when_disk_is_short_before_writing(self):
        usage = mock.Mock(free=len(DATA) + 10)
        with mock.patch("shutil.disk_usage", return_value=usage):
            with self.assertRaises(download.DownloadError) as ctx:
                download.download_file("u", self.dest, SHA, server(), reserve_bytes=1000)
        self.assertIn("free disk", str(ctx.exception))
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_gives_up_after_max_attempts(self):
        def opener(url, headers):
            raise OSError("down")
        with self.assertRaises(download.DownloadError):
            download.download_file("u", self.dest, SHA, opener, reserve_bytes=0, max_attempts=2)

    def test_unexpected_status_is_an_error(self):
        with self.assertRaises(download.DownloadError):
            download.download_file("u", self.dest, SHA, lambda u, h: FakeResponse(b"", 503), reserve_bytes=0)

    def test_progress_callback_reports_bytes(self):
        seen = []
        download.download_file("u", self.dest, SHA, server(), reserve_bytes=0,
                               on_progress=lambda got, total: seen.append((got, total)))
        self.assertEqual(seen[-1], (len(DATA), len(DATA)))


class ExportTests(unittest.TestCase):
    def _opener(self, sums_text, latest="20261104-002222\n"):
        files = {"LATEST": latest.encode(), "SHA256SUMS": sums_text.encode()}

        def opener(url, headers):
            name = url.rsplit("/", 1)[1]
            body = files.get(name, DATA)
            return FakeResponse(body, 200, {"Content-Length": str(len(body))})
        return opener

    def test_latest_export_rejects_path_like_values(self):
        with self.assertRaises(download.DownloadError):
            download.latest_export(self._opener("", latest="../etc\n"))

    def test_downloads_core_and_cover_art(self):
        sums = f"{SHA}  mbdump.tar.bz2\n{SHA}  mbdump-cover-art-archive.tar.bz2\n"
        with tempfile.TemporaryDirectory() as tmp:
            paths = download.download_export(tmp, opener=self._opener(sums), reserve_bytes=0)
            self.assertEqual(set(paths), {download.CORE_ARCHIVE, download.COVER_ART_ARCHIVE})
            self.assertTrue(all(p.read_bytes() == DATA for p in paths.values()))

    def test_missing_checksum_entry_is_an_error_before_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(download.DownloadError):
                download.download_export(tmp, opener=self._opener(f"{SHA}  mbdump.tar.bz2\n"), reserve_bytes=0)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
