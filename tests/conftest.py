import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))


@pytest.fixture
def root(monkeypatch):
    """Scripts use paths relative to the repo root."""
    monkeypatch.chdir(ROOT)
    return ROOT
