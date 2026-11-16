"""Keep tests off the host's real provider gate: no data-directory file, no real waiting."""
import pytest

from integrations import provider_gate


@pytest.fixture(autouse=True)
def private_provider_gate(tmp_path, monkeypatch):
    gate = provider_gate.ProviderGate(
        tmp_path / provider_gate.GATE_FILE, sleep=lambda seconds: None, intervals={})
    monkeypatch.setattr(provider_gate, "shared_gate", lambda: gate)
    yield gate
    gate.close()
