"""Pytest configuration and fixtures for DialogChain tests."""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import pytest
import pytest_asyncio
import yaml
from _pytest.monkeypatch import MonkeyPatch

# Add the src directory to the Python path
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

# Make the package available for testing
sys.path.insert(0, str(SRC_DIR))

# Configure asyncio to be less verbose
os.environ["PYTHONASYNCIODEBUG"] = "0"


# Common fixtures
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_environment(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Set up test environment variables and temporary directories."""
    # Set up test directories
    test_config_dir = tmp_path / "config"
    test_data_dir = tmp_path / "data"
    test_config_dir.mkdir()
    test_data_dir.mkdir()

    # Set environment variables
    monkeypatch.setenv("DIALOGCHAIN_CONFIG_DIR", str(test_config_dir))
    monkeypatch.setenv("DIALOGCHAIN_DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("DIALOGCHAIN_DEBUG", "true")

    # Ensure clean environment for each test
    for key in list(os.environ):
        if key.startswith("DIALOGCHAIN_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Return a sample configuration for testing."""
    return {
        "version": "1.0",
        "name": "test_dialog",
        "description": "Test dialog configuration",
        "connectors": {
            "http": {
                "type": "http",
                "base_url": "http://example.com/api",
                "timeout": 30,
            }
        },
        "processors": {
            "greeting": {
                "type": "text",
                "template": "Hello, {name}!",
            }
        },
    }


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""

    class MockResponse:
        def __init__(
            self,
            status: int = 200,
            json_data: Optional[dict] = None,
            text: Optional[str] = None,
        ):
            self.status = status
            self._json = json_data or {}
            self._text = text or ""
            self._raise_for_status = None

        async def json(self) -> dict:
            return self._json

        async def text(self) -> str:
            return self._text

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def raise_for_status(self) -> None:
            if self._raise_for_status:
                raise self._raise_for_status

    return MockResponse


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create and return a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_config_file(tmp_path: Path, sample_config: dict) -> Path:
    """Create a sample config file for testing."""
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """Configure logging for tests."""
    import logging

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Disable noisy loggers
    for logger_name in ["aiohttp", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
