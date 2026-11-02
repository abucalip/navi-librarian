"""Library resync after an import: the setting, the hook and the coalesced delayed resync."""
import json
import unittest
from unittest.mock import Mock, patch

from acquisition import import_hooks
from app.api import settings as settings_routes
from discovery.library_resync import LibraryResync
from settings import service


class FakeTimer:
    created = []

    def __init__(self, delay, fn):
        self.delay, self.fn, self.started, self.daemon = delay, fn, False, False
        FakeTimer.created.append(self)

    def start(self):
        self.started = True


class LibraryResyncTests(unittest.TestCase):
    def setUp(self):
        FakeTimer.created = []
        self.resync = Mock()
        self.enabled = True
        self.sut = LibraryResync(enabled=lambda: self.enabled, resync=self.resync, delay=7, timer_factory=FakeTimer)

    def test_import_schedules_one_delayed_resync(self):
        self.sut.on_imported("A", "B")
        self.assertEqual(len(FakeTimer.created), 1)
        timer = FakeTimer.created[0]
        self.assertTrue(timer.started and timer.daemon)
        self.assertEqual(timer.delay, 7)
        self.resync.assert_not_called()
        timer.fn()
        self.resync.assert_called_once_with()

    def test_disabled_schedules_nothing(self):
        self.enabled = False
        self.sut.on_imported("A", "B")
        self.assertEqual(FakeTimer.created, [])

    def test_failing_setting_read_schedules_nothing(self):
        sut = LibraryResync(enabled=Mock(side_effect=RuntimeError), resync=self.resync, timer_factory=FakeTimer)
        sut.on_imported("A", "B")
        self.assertEqual(FakeTimer.created, [])

    def test_imports_close_together_share_one_resync(self):
        self.sut.on_imported("A", "B")
        self.sut.on_imported("C", "D")
        self.assertEqual(len(FakeTimer.created), 1)

    def test_import_after_the_resync_ran_schedules_another(self):
        self.sut.on_imported("A", "B")
        FakeTimer.created[0].fn()
        self.sut.on_imported("C", "D")
        self.assertEqual(len(FakeTimer.created), 2)

    def test_resync_failure_is_swallowed_and_allows_the_next(self):
        self.resync.side_effect = RuntimeError("navidrome down")
        self.sut.on_imported("A", "B")
        FakeTimer.created[0].fn()
        self.sut.on_imported("C", "D")
        self.assertEqual(len(FakeTimer.created), 2)


class ImportHooksTests(unittest.TestCase):
    def setUp(self):
        self._saved = list(import_hooks._listeners)
        import_hooks._listeners.clear()

    def tearDown(self):
        import_hooks._listeners[:] = self._saved

    def test_listeners_are_called_once_each_and_failures_do_not_stop_others(self):
        bad, good = Mock(side_effect=RuntimeError), Mock()
        import_hooks.register(bad)
        import_hooks.register(bad)
        import_hooks.register(good)
        import_hooks.notify_imported("A", "B")
        bad.assert_called_once_with("A", "B")
        good.assert_called_once_with("A", "B")


class SettingTests(unittest.TestCase):
    def test_default_is_on_and_junk_means_on(self):
        self.assertTrue(service.library_resync_enabled_value(lambda: {}))
        self.assertTrue(service.library_resync_enabled_value(lambda: {"library_resync_after_import": "no"}))
        self.assertFalse(service.library_resync_enabled_value(lambda: {"library_resync_after_import": False}))

    def test_set_refuses_non_boolean_without_writing(self):
        write = Mock()
        result = json.loads(service.set_library_resync_settings(write, "yes"))
        self.assertFalse(result["ok"])
        write.assert_not_called()

    def test_set_persists_boolean(self):
        write = Mock()
        result = json.loads(service.set_library_resync_settings(write, False))
        write.assert_called_once_with({"library_resync_after_import": False})
        self.assertEqual(result["library_resync_after_import"], False)


class RouteTests(unittest.TestCase):
    def test_get_and_put(self):
        librarian = Mock()
        librarian._discovery_settings_read.return_value = {}
        self.assertEqual(settings_routes.get_library_resync_settings(librarian), {"library_resync_after_import": True})
        out = settings_routes.set_library_resync_settings({"library_resync_after_import": False}, librarian)
        self.assertTrue(out["ok"])
        librarian._discovery_settings_write.assert_called_once_with({"library_resync_after_import": False})

    def test_put_rejects_non_boolean(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            settings_routes.set_library_resync_settings({"library_resync_after_import": 1}, Mock())
        self.assertEqual(caught.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
