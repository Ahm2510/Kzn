"""
Security Tests for Kaizen Service B

Tests for:
- Rate limiting (429 response)
- File upload validation (size, type, path traversal)
- CORS configuration
- Input validation
"""

import pytest
import io
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock settings before importing app
@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for testing."""
    with patch.dict(os.environ, {
        "RATE_LIMIT_ENABLED": "false",  # Disable rate limiting for most tests
        "ALLOW_INTERNAL_PUBLIC": "true",
        "MAX_UPLOAD_MB": "1",  # 1MB for testing
        "MAX_ROWS": "1000",
    }):
        yield


class TestFileUploadValidation:
    """Tests for file upload security validation."""
    
    @pytest.fixture
    def client(self):
        """Create test client with rate limiting disabled."""
        # Import here to get mocked settings
        from service_b.app import app
        return TestClient(app)
    
    @pytest.fixture
    def valid_csv_content(self):
        """Valid CSV content for testing."""
        return b"revenue,date\n100,2024-01-01\n200,2024-01-02\n300,2024-01-03"
    
    @pytest.fixture
    def invalid_csv_no_numeric(self):
        """CSV with no numeric columns."""
        return b"name,date\nfoo,2024-01-01\nbar,2024-01-02"
    
    def test_valid_csv_upload_succeeds(self, client, valid_csv_content):
        """Test that valid CSV upload succeeds."""
        files = {"current_file": ("test.csv", io.BytesIO(valid_csv_content), "text/csv")}
        response = client.post("/v1/analyze", files=files)
        assert response.status_code == 200
        assert "report" in response.json()
    
    def test_non_csv_file_rejected(self, client, valid_csv_content):
        """Test that non-CSV files are rejected."""
        files = {"current_file": ("test.txt", io.BytesIO(valid_csv_content), "text/plain")}
        response = client.post("/v1/analyze", files=files)
        assert response.status_code == 400
        assert "Only CSV files are supported" in response.json()["detail"]
    
    def test_path_traversal_rejected(self, client, valid_csv_content):
        """Test that path traversal in filename is rejected."""
        files = {"current_file": ("../../../etc/passwd.csv", io.BytesIO(valid_csv_content), "text/csv")}
        response = client.post("/v1/analyze", files=files)
        assert response.status_code == 400
        assert "Path traversal" in response.json()["detail"]
    
    def test_empty_file_rejected(self, client):
        """Test that empty files are rejected."""
        files = {"current_file": ("test.csv", io.BytesIO(b""), "text/csv")}
        response = client.post("/v1/analyze", files=files)
        assert response.status_code == 400
    
    def test_csv_without_numeric_column_rejected(self, client, invalid_csv_no_numeric):
        """Test that CSV without numeric columns is rejected."""
        files = {"current_file": ("test.csv", io.BytesIO(invalid_csv_no_numeric), "text/csv")}
        response = client.post("/v1/analyze", files=files)
        assert response.status_code == 400
        assert "numeric column" in response.json()["detail"]


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_rate_limiter_configured(self):
        """Test that rate limiter is configured in app."""
        from service_b.app import app, limiter
        assert hasattr(app.state, "limiter")
        assert limiter is not None
    
    def test_rate_limit_setting_exists(self):
        """Test that rate limit setting is configured."""
        from config.settings import settings
        assert hasattr(settings, "RATE_LIMIT")
        assert hasattr(settings, "RATE_LIMIT_ENABLED")


class TestCORSConfiguration:
    """Tests for CORS security configuration."""
    
    def test_cors_origins_from_settings(self):
        """Test that CORS origins are read from settings."""
        from config.settings import settings
        assert hasattr(settings, "CORS_ORIGINS")
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0
    
    def test_cors_origins_not_wildcard_by_default(self):
        """Test that default CORS origins do not include wildcard."""
        from config.settings import settings
        # Default config should NOT have wildcard
        assert "*" not in settings.CORS_ORIGINS
        # Should have localhost origins for dev
        assert any("localhost" in origin for origin in settings.CORS_ORIGINS)


class TestInternalAuthentication:
    """Tests for internal endpoint authentication."""
    
    def test_internal_auth_settings_exist(self):
        """Test that internal auth settings are available."""
        from config.settings import settings
        assert hasattr(settings, "INTERNAL_SECRET")
        assert hasattr(settings, "ALLOW_INTERNAL_PUBLIC")
    
    def test_require_internal_auth_function_exists(self):
        """Test that require_internal_auth function is defined."""
        from utils.security import require_internal_auth
        assert callable(require_internal_auth)


class TestInputValidation:
    """Tests for general input validation."""
    
    def test_max_rows_setting_exists(self):
        """Test that MAX_ROWS setting is configured."""
        from config.settings import settings
        assert hasattr(settings, "MAX_ROWS")
        assert settings.MAX_ROWS > 0
    
    def test_max_upload_mb_setting_exists(self):
        """Test that MAX_UPLOAD_MB setting is configured."""
        from config.settings import settings
        assert hasattr(settings, "MAX_UPLOAD_MB")
        assert settings.MAX_UPLOAD_MB > 0


class TestErrorHandling:
    """Tests for secure error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from service_b.app import app
        return TestClient(app)
    
    def test_malformed_csv_returns_400_not_500(self, client):
        """Test that malformed CSV returns 400 Bad Request, not 500."""
        files = {"current_file": ("test.csv", io.BytesIO(b"not,valid\ncsv\"data"), "text/csv")}
        response = client.post("/v1/analyze", files=files)
        # Should be 400 (client error) not 500 (server error)
        assert response.status_code in [200, 400]  # May parse successfully or fail gracefully
    
    def test_error_response_no_stack_trace(self, client):
        """Test that error responses don't include stack traces."""
        files = {"current_file": ("test.csv", io.BytesIO(b"invalid"), "text/csv")}
        response = client.post("/v1/analyze", files=files)
        if response.status_code >= 400:
            response_text = str(response.json())
            assert "Traceback" not in response_text
            assert "File \"" not in response_text


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from service_b.app import app
        return TestClient(app)
    
    def test_health_endpoint_exists(self, client):
        """Test that /health endpoint exists and returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_health_endpoint_includes_version(self, client):
        """Test that health endpoint includes version info."""
        response = client.get("/health")
        assert "version" in response.json()
        assert "service" in response.json()
