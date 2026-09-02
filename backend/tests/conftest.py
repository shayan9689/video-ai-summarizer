"""
pytest configuration — mark slow integration tests.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: full pipeline integration (needs ffmpeg + models)")
