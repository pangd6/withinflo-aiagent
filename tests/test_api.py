"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_mongodb():
    """Create a mock for the MongoDB instance."""
    with patch('src.api.app.mongodb') as mock:
        mock.connect = MagicMock()
        mock.close = MagicMock()
        mock.create_job = MagicMock(return_value="test_job_id")
        mock.get_job = MagicMock(return_value={
            "_id": "test_job_id",
            "status": "pending",
            "urls": ["https://example.com"],
            "created_at": "2023-01-01T00:00:00",
            "auth_config": None,
            "rate_limit": 10
        })
        mock.get_qa_docs_by_job = MagicMock(return_value=[
            {
                "_id": "test_doc_id",
                "source_url": "https://example.com",
                "page_title": "Example Page",
                "analysis_timestamp": "2023-01-01T00:00:00",
                "identified_elements": [],
                "generated_test_cases": []
            }
        ])
        mock.get_qa_documentation = MagicMock(return_value={
            "_id": "test_doc_id",
            "job_id": "test_job_id",
            "source_url": "https://example.com",
            "page_title": "Example Page",
            "analysis_timestamp": "2023-01-01T00:00:00",
            "identified_elements": [],
            "generated_test_cases": []
        })
        yield mock


@pytest.fixture
def mock_redis():
    """Create a mock for the Redis client."""
    with patch('src.api.app.redis_client') as mock:
        mock.connect = MagicMock()
        mock.close = MagicMock()
        yield mock


@pytest.fixture
def mock_celery():
    """Create a mock for the Celery tasks."""
    with patch('src.api.app.process_job') as mock:
        mock.delay = MagicMock()
        yield mock


def test_health_check(client, mock_mongodb, mock_redis):
    """Test the health check endpoint."""
    # Setup mocks
    mock_mongodb.client.admin.command = MagicMock(return_value=True)
    mock_redis.client.ping = MagicMock(return_value=True)
    
    # Call endpoint
    response = client.get("/health")
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "dependencies" in response.json()
    assert "mongodb" in response.json()["dependencies"]
    assert "redis" in response.json()["dependencies"]


def test_create_job(client, mock_mongodb, mock_redis, mock_celery):
    """Test creating a new job."""
    # Call endpoint
    response = client.post(
        "/jobs",
        json={
            "urls": ["https://example.com"],
            "auth_config": None,
            "rate_limit_requests_per_minute": 10
        }
    )
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["job_id"] == "test_job_id"
    assert response.json()["status"] == "pending"
    
    # Verify mocks called
    mock_mongodb.create_job.assert_called_once()
    mock_celery.delay.assert_called_once_with("test_job_id")


def test_get_job_status(client, mock_mongodb, mock_redis):
    """Test getting job status."""
    # Call endpoint
    response = client.get("/jobs/test_job_id")
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["job_id"] == "test_job_id"
    assert response.json()["status"] == "pending"
    
    # Verify mocks called
    mock_mongodb.get_job.assert_called_once_with("test_job_id")


def test_get_job_results(client, mock_mongodb, mock_redis):
    """Test getting job results."""
    # Call endpoint
    response = client.get("/jobs/test_job_id/results")
    
    # Verify response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["doc_id"] == "test_doc_id"
    assert response.json()[0]["url"] == "https://example.com"
    
    # Verify mocks called
    mock_mongodb.get_job.assert_called_once_with("test_job_id")
    mock_mongodb.get_qa_docs_by_job.assert_called_once_with("test_job_id")


def test_get_json_doc(client, mock_mongodb, mock_redis):
    """Test getting JSON documentation."""
    # Call endpoint
    response = client.get("/docs/test_doc_id/json")
    
    # Verify response
    assert response.status_code == 200
    assert "source_url" in response.json()
    assert response.json()["source_url"] == "https://example.com"
    
    # Verify mocks called
    mock_mongodb.get_qa_documentation.assert_called_once_with("test_doc_id") 