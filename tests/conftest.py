"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path

# Add the src directory to the Python path
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent

# Make the package available for testing
import sys
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Common fixtures can be defined here
@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
    return {
        "version": "1.0",
        "routes": [
            {
                "id": "test_route",
                "from": "test_source",
                "to": ["test_destination"],
                "processors": ["test_processor"]
            }
        ]
    }
