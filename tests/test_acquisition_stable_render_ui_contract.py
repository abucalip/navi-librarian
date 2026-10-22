"""Source contract: the acquisitions list renders in place and in a stable order.

The live stream resends the whole list every second. Wiping and rebuilding every row made the
artwork flicker, and ordering by last update made active rows swap places. These tests read the
script as source; they never open a browser, so they do not replace the manual checklist.
"""
import unittest
from pathlib import Path


JS = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")


def between(start, end):
    first = JS.index(start)
    return JS[first:JS.index(end, first)]


class AcquisitionStableRenderContractTests(unittest.TestCase):
    def test_rows_are_ordered_by_request_time_not_last_update(self):
        order = between("function orderAcquisitions(", "function acquisitionRowSignature(")
        self.assertIn("Number(b.job.created_at)", order)
        self.assertNotIn("updated_at", order)
        self.assertIn("acquisitionRowKey(a.job).localeCompare(acquisitionRowKey(b.job))", order)
        self.assertIn("const jobs = orderAcquisitions(", between("function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES"))

    def test_render_no_longer_wipes_the_list_before_rebuilding(self):
        render = between("function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertNotIn("target.replaceChildren();", render)
        self.assertIn("existing.dataset.sig === signature", render)
        self.assertIn("orderedRows.push(existing);", render)

    def test_changed_rows_keep_the_artwork_element_they_replace(self):
        render = between("function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("newArt.replaceWith(oldArt);", render)
        self.assertIn("existing.replaceWith(row);", render)

    def test_only_out_of_place_rows_are_moved_and_stale_rows_removed(self):
        render = between("function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("if (target.children[index] !== node) target.insertBefore(", render)
        self.assertIn("for (const stale of existingRows.values()) stale.remove();", render)

    def test_stall_countdown_still_refreshes_the_row_each_second(self):
        signature = between("function acquisitionRowSignature(", "function renderAcquisitions(")
        self.assertIn("stall_detected_at", signature)
        self.assertIn("Math.floor(Date.now() / 1000)", signature)


if __name__ == "__main__":
    unittest.main()
