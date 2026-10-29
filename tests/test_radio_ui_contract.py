import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADIO_JS = (ROOT / "static" / "radio.js").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")


class RadioUiContractTests(unittest.TestCase):
    def test_page_menu_entry_and_script_are_wired(self):
        self.assertIn('<section id="radio" class="page hidden"', INDEX)
        self.assertIn('data-page="radio"', INDEX)
        self.assertLess(INDEX.index("/static/app.js"), INDEX.index("/static/radio.js"))
        self.assertIn("if (name === 'radio') loadRadio();", APP_JS)

    def test_station_and_song_text_is_never_parsed_as_html(self):
        for unsafe in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(unsafe, RADIO_JS)

    def test_controls_reuse_the_apps_get_button_a_switch_and_an_x(self):
        self.assertIn("decorateGetButton(button)", RADIO_JS)
        self.assertIn("setGetButtonState(", RADIO_JS)
        self.assertIn("role', 'switch'", RADIO_JS)
        self.assertIn("icons.svg#x", RADIO_JS)
        self.assertNotIn("Turn on", RADIO_JS)

    def test_every_radio_endpoint_the_page_calls_exists(self):
        routes = (ROOT / "app" / "api" / "radio.py").read_text(encoding="utf-8")
        for path in re.findall(r"'(/api/radio/[a-z/]+)", RADIO_JS):
            self.assertIn(path.rstrip("/").split("/")[3], routes)


if __name__ == "__main__":
    unittest.main()
