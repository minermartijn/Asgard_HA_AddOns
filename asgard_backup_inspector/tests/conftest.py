import json
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_bytes():
    def _load(name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    return _load


@pytest.fixture
def fixture_data():
    def _load(name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load
