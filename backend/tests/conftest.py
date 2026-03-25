import os
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file before any tests run
# This is crucial so that the real API keys are available for integration tests
# proving the deterministic nature of the new scorers
load_dotenv()

@pytest.fixture
def openai_api_key():
    """Returns the OPENAI_API_KEY from the environment or skips the test."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY is not set in the environment.")
    return key
