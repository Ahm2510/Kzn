"""
Client for calling service_b /v1/analyze endpoint.
Treats service_b as a black-box external service.
"""
import os
import requests
from typing import Dict, Any, Optional
from django.conf import settings


class ServiceBClient:
    """Thin client wrapper around service_b analyze endpoint."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'SERVICE_B_URL', 'http://localhost:8000')
        self.timeout = getattr(settings, 'SERVICE_B_TIMEOUT', 300)  # 5 minutes for analysis
        self.internal_secret = getattr(settings, 'SERVICE_B_SECRET', '')
    
    def analyze(
        self,
        current_file_path: str,
        baseline_file_path: Optional[str] = None,
        cleaning_options: Optional[Dict[str, Any]] = None,
        metric_schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call service_b /v1/analyze endpoint.
        
        Args:
            current_file_path: Path to the current CSV file
            baseline_file_path: Optional path to baseline CSV file
            cleaning_options: Optional cleaning options dict
            metric_schema: Optional metric schema hint (e.g. 'auto', 'revenue', 'cost', 'custom:<col>')
            
        Returns:
            Response dict with 'report' and 'pdf_path' keys
            
        Raises:
            requests.RequestException: If the HTTP request fails
            ValueError: If service_b returns an error response
        """
        url = f"{self.base_url}/v1/analyze"
        
        # Prepare files and form data
        files = {}
        current_file = None
        baseline_file = None
        
        try:
            # Open files inside try so finally always cleans up
            current_file = open(current_file_path, 'rb')
            files['current_file'] = (os.path.basename(current_file_path), current_file, 'text/csv')
            
            if baseline_file_path:
                baseline_file = open(baseline_file_path, 'rb')
                files['baseline_file'] = (os.path.basename(baseline_file_path), baseline_file, 'text/csv')
            
            # Prepare cleaning options as form data
            # FastAPI endpoint signature: `cleaning: CleaningOptions = CleaningOptions()`
            # Without Form() wrapper, FastAPI may not parse from multipart correctly
            # We send as individual fields; if parsing fails, service_b will use defaults
            data = {}
            if cleaning_options:
                # Frontend sends camelCase keys; Service B expects snake_case.
                # Keep backward compatibility by accepting both.
                key_map = {
                    "dropDuplicates": "drop_duplicates",
                    "drop_duplicates": "drop_duplicates",
                    "dropMissing": "drop_missing",
                    "drop_missing": "drop_missing",
                    "capOutliers": "cap_outliers",
                    "cap_outliers": "cap_outliers",
                    "normalizeColumns": "normalize_columns",
                    "normalize_columns": "normalize_columns",
                }

                normalized_cleaning_options: Dict[str, Any] = {}
                for key, value in cleaning_options.items():
                    mapped_key = key_map.get(key, key)
                    normalized_cleaning_options[mapped_key] = value

                # Send each cleaning option as a separate form field
                # FastAPI might parse these into the CleaningOptions model
                for key, value in normalized_cleaning_options.items():
                    if isinstance(value, bool):
                        data[key] = 'true' if value else 'false'
                    else:
                        data[key] = str(value)
            
            if metric_schema is not None:
                data['metric_schema'] = metric_schema
            
            headers = {}
            if self.internal_secret:
                headers['X-Internal-Secret'] = self.internal_secret
            
            response = requests.post(url, files=files, data=data, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result
        except requests.exceptions.HTTPError as e:
            # Try to extract error detail from response
            try:
                error_detail = e.response.json().get('detail', str(e))
            except Exception:
                error_detail = str(e)
            raise ValueError(f"Service B error: {error_detail}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to connect to service B: {str(e)}")
        finally:
            # Ensure files are closed
            if current_file:
                current_file.close()
            if baseline_file:
                baseline_file.close()


# Singleton instance
_client = None


def get_service_b_client() -> ServiceBClient:
    """Get or create the service_b client instance."""
    global _client
    if _client is None:
        _client = ServiceBClient()
    return _client

