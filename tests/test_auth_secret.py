"""Direct-import tests for lazy application-auth secret loading."""
import threading
import unittest
from unittest.mock import Mock

from app.security.auth_secret import AuthSecretProvider


class AuthSecretProviderTests(unittest.TestCase):
    def test_load_is_lazy_and_success_is_cached(self):
        data_dir = Mock(return_value="/persistent-data")
        loader = Mock(return_value="signing-secret")
        provider = AuthSecretProvider(data_dir_getter=data_dir, secret_loader=loader)

        data_dir.assert_not_called()
        loader.assert_not_called()
        self.assertEqual(provider.get(), "signing-secret")
        self.assertEqual(provider.get(), "signing-secret")
        loader.assert_called_once_with("/persistent-data")
        data_dir.assert_called_once_with()

    def test_failed_load_can_be_retried(self):
        data_dir = Mock(return_value="/persistent-data")
        loader = Mock(side_effect=[RuntimeError("temporarily unavailable"), "secret"])
        provider = AuthSecretProvider(data_dir_getter=data_dir, secret_loader=loader)

        with self.assertRaisesRegex(RuntimeError, "temporarily unavailable"):
            provider.get()
        self.assertEqual(provider.get(), "secret")
        self.assertEqual(provider.get(), "secret")
        self.assertEqual(loader.call_count, 2)
        self.assertEqual(data_dir.call_count, 2)

    def test_none_is_not_cached(self):
        loader = Mock(side_effect=[None, "secret"])
        provider = AuthSecretProvider(data_dir_getter=lambda: "/data", secret_loader=loader)
        self.assertIsNone(provider.get())
        self.assertEqual(provider.get(), "secret")
        self.assertEqual(loader.call_count, 2)

    def test_concurrent_first_use_loads_once(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []

        def loader(path):
            calls.append(path)
            entered.set()
            release.wait(timeout=2)
            return "secret"

        provider = AuthSecretProvider(data_dir_getter=lambda: "/data", secret_loader=loader)
        results = []
        first = threading.Thread(target=lambda: results.append(provider.get()))
        second = threading.Thread(target=lambda: results.append(provider.get()))
        first.start()
        self.assertTrue(entered.wait(timeout=2))
        second.start()
        release.set()
        first.join(timeout=2)
        second.join(timeout=2)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(results, ["secret", "secret"])
        self.assertEqual(calls, ["/data"])


if __name__ == "__main__":
    unittest.main()
