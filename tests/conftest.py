"""Pytest configuration and shared fixtures for job-hunt tests."""

import os
import sys
import uuid
import tempfile
from pathlib import Path

import pytest

# Ensure src is in path
PROJ = Path(__file__).parent.parent
SRC = PROJ / "src"
sys.path.insert(0, str(SRC))
os.chdir(PROJ)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def temp_config(temp_dir):
    """Create a temporary config file."""
    config_path = temp_dir / f"cfg_{uuid.uuid4().hex[:4]}.toml"
    return config_path


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database."""
    db_path = temp_dir / f"db_{uuid.uuid4().hex[:4]}.db"
    return db_path


@pytest.fixture
def sample_job():
    """Create a sample job for testing."""
    from job_hunt.models.job import Job
    return Job(
        title="Python Dev",
        company="Test Corp",
        city="南宁",
        platform="gxrc",
        salary_min=8000,
        salary_max=12000,
    )


@pytest.fixture
def sample_resume():
    """Create a sample resume for testing."""
    from job_hunt.models.resume import Resume
    return Resume(
        name="Test User",
        education_level="硕士",
        major="环境工程",
        skills="Python,SQL,数据分析",
        desired_city="南宁",
        desired_position="Python开发",
        salary_min=8000,
        salary_max=12000,
    )


@pytest.fixture
def sample_application(sample_job):
    """Create a sample application for testing."""
    from job_hunt.models.application import Application
    app = Application(status="applied")
    app.job_id = sample_job.id or 1
    return app


@pytest.fixture
def configured_db(temp_db, sample_resume):
    """Create a database with sample data."""
    from job_hunt.db.database import Database
    db = Database(str(temp_db))
    db.save_resume(sample_resume)
    return db


@pytest.fixture
def mock_config(temp_config):
    """Create a mock config for testing."""
    from job_hunt.utils.config import Config
    cfg = Config(str(temp_config))
    return cfg


@pytest.fixture
def mock_output():
    """Create a mock output for testing."""
    from job_hunt.utils.output import Output
    return Output(json_mode=True)
