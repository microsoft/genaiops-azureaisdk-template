"""Tests for the tagging functionality in eval_experiments."""
import pytest
from unittest.mock import Mock, patch
from llmops.eval_experiments import extract_run_id, update_run_tags


class TestExtractRunId:
    """Test cases for extract_run_id function."""

    def test_extract_run_id_from_valid_url(self):
        """Test extracting run ID from a valid Azure ML studio URL."""
        url = "https://ml.azure.com/runs/12345678-1234-1234-1234-123456789abc?wsid=/subscriptions/..."
        expected_id = "12345678-1234-1234-1234-123456789abc"
        
        result = extract_run_id(url)
        
        assert result == expected_id

    def test_extract_run_id_from_url_with_multiple_guids(self):
        """Test extracting run ID when URL contains multiple GUIDs."""
        url = "https://ml.azure.com/runs/12345678-1234-1234-1234-123456789abc/details/87654321-4321-4321-4321-cba987654321"
        expected_id = "12345678-1234-1234-1234-123456789abc"
        
        result = extract_run_id(url)
        
        assert result == expected_id

    def test_extract_run_id_from_invalid_url(self):
        """Test extracting run ID from URL without valid GUID."""
        url = "https://example.com/invalid-url"
        
        result = extract_run_id(url)
        
        assert result is None

    def test_extract_run_id_from_empty_string(self):
        """Test extracting run ID from empty string."""
        url = ""
        
        result = extract_run_id(url)
        
        assert result is None


class TestUpdateRunTags:
    """Test cases for update_run_tags function."""

    @patch('llmops.eval_experiments.requests.patch')
    @patch('llmops.eval_experiments.DefaultAzureCredential')
    def test_update_run_tags_success(self, mock_credential_class, mock_patch):
        """Test successful tag update."""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "fake-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        subscription_id = "sub-123"
        resource_group = "rg-test"
        workspace_name = "ws-test"
        workspace_location = "eastus2"
        run_id = "12345678-1234-1234-1234-123456789abc"
        tags = {"model": "gpt-4", "experiment": "test"}

        update_run_tags(
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace_name,
            workspace_location=workspace_location,
            run_id=run_id,
            tags=tags
        )

        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        
        expected_url = (
            f"https://{workspace_location}.api.azureml.ms/history/v1.0"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.MachineLearningServices"
            f"/workspaces/{workspace_name}"
            f"/runs/{run_id}"
        )
        assert call_args[0][0] == expected_url
        
        expected_headers = {
            "Authorization": "Bearer fake-token",
            "Content-Type": "application/json"
        }
        assert call_args[1]["headers"] == expected_headers
        
        expected_payload = {"tags": tags}
        assert call_args[1]["json"] == expected_payload

    @patch('llmops.eval_experiments.requests.patch')
    @patch('llmops.eval_experiments.DefaultAzureCredential')
    def test_update_run_tags_api_failure(self, mock_credential_class, mock_patch):
        """Test handling of API failure."""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "fake-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_patch.return_value = mock_response

        subscription_id = "sub-123"
        resource_group = "rg-test"
        workspace_name = "ws-test"
        workspace_location = "eastus2"
        run_id = "12345678-1234-1234-1234-123456789abc"
        tags = {"model": "gpt-4"}

        update_run_tags(
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace_name,
            workspace_location=workspace_location,
            run_id=run_id,
            tags=tags
        )

        mock_patch.assert_called_once()

    @patch('llmops.eval_experiments.DefaultAzureCredential')
    def test_update_run_tags_with_custom_credential(self, mock_default_credential):
        """Test using custom credential instead of default."""
        custom_credential = Mock()
        mock_token = Mock()
        mock_token.token = "custom-token"
        custom_credential.get_token.return_value = mock_token

        with patch('llmops.eval_experiments.requests.patch') as mock_patch:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_patch.return_value = mock_response

            update_run_tags(
                subscription_id="sub-123",
                resource_group_name="rg-test",
                workspace_name="ws-test",
                workspace_location="eastus2",
                run_id="12345678-1234-1234-1234-123456789abc",
                tags={"test": "value"},
                credential=custom_credential
            )

            mock_default_credential.assert_not_called()
            custom_credential.get_token.assert_called_once_with("https://management.azure.com/.default")


class TestIntegrationWithResults:
    """Test cases for the integration with evaluation results and tagging."""

    @patch('llmops.eval_experiments.requests.patch')
    @patch('llmops.eval_experiments.DefaultAzureCredential')
    def test_tagging_with_model_in_result(self, mock_credential_class, mock_patch):
        """Test that model information from result is properly added to tags."""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "fake-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        result_with_model = {
            "result": {
                "rows": [
                    {
                        "outputs": {
                            "model": "gpt-4o-mini"
                        }
                    }
                ],
                "studio_url": "https://ml.azure.com/runs/12345678-1234-1234-1234-123456789abc?wsid=..."
            }
        }

        evaluation_tags = {}
        if "outputs" in result_with_model["result"]["rows"][0]:
            outputs = result_with_model["result"]["rows"][0]["outputs"]
            if isinstance(outputs, dict) and "model" in outputs:
                evaluation_tags["model"] = outputs["model"]

        run_id = extract_run_id(result_with_model["result"]["studio_url"])
        
        update_run_tags(
            subscription_id="sub-123",
            resource_group_name="rg-test",
            workspace_name="ws-test",
            workspace_location="eastus2",
            run_id=run_id,
            tags=evaluation_tags
        )

        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        sent_payload = call_args[1]["json"]
        
        assert "tags" in sent_payload
        assert "model" in sent_payload["tags"]
        assert sent_payload["tags"]["model"] == "gpt-4o-mini"

    @patch('llmops.eval_experiments.requests.patch')
    @patch('llmops.eval_experiments.DefaultAzureCredential')
    def test_tagging_without_model_in_result(self, mock_credential_class, mock_patch):
        """Test that tagging works gracefully when no model information is available."""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "fake-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        result_without_model = {
            "result": {
                "rows": [
                    {
                        "outputs": {
                            "score": 0.85,
                            "response": "Some evaluation result"
                        }
                    }
                ],
                "studio_url": "https://ml.azure.com/runs/87654321-4321-4321-4321-cba987654321?wsid=..."
            }
        }

        evaluation_tags = {}
        if "outputs" in result_without_model["result"]["rows"][0]:
            outputs = result_without_model["result"]["rows"][0]["outputs"]
            if isinstance(outputs, dict) and "model" in outputs:
                evaluation_tags["model"] = outputs["model"]

        run_id = extract_run_id(result_without_model["result"]["studio_url"])
        
        update_run_tags(
            subscription_id="sub-123",
            resource_group_name="rg-test", 
            workspace_name="ws-test",
            workspace_location="eastus2",
            run_id=run_id,
            tags=evaluation_tags
        )

        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        sent_payload = call_args[1]["json"]
        
        assert "tags" in sent_payload
        assert sent_payload["tags"] == {}

    @patch('llmops.eval_experiments.requests.patch')
    @patch('llmops.eval_experiments.DefaultAzureCredential')
    def test_tagging_with_model_as_attribute(self, mock_credential_class, mock_patch):
        """Test that model information works when outputs.model is an attribute."""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "fake-token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        mock_outputs = Mock()
        mock_outputs.model = "gpt-3.5-turbo"
        
        result_with_model_attr = {
            "result": {
                "rows": [
                    {
                        "outputs": mock_outputs
                    }
                ],
                "studio_url": "https://ml.azure.com/runs/11111111-2222-3333-4444-555555555555?wsid=..."
            }
        }

        evaluation_tags = {}
        if "outputs" in result_with_model_attr["result"]["rows"][0]:
            outputs = result_with_model_attr["result"]["rows"][0]["outputs"]
            if isinstance(outputs, dict) and "model" in outputs:
                evaluation_tags["model"] = outputs["model"]
            elif hasattr(outputs, 'model'):
                evaluation_tags["model"] = outputs.model

        run_id = extract_run_id(result_with_model_attr["result"]["studio_url"])
        
        update_run_tags(
            subscription_id="sub-123",
            resource_group_name="rg-test",
            workspace_name="ws-test", 
            workspace_location="eastus2",
            run_id=run_id,
            tags=evaluation_tags
        )

        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        sent_payload = call_args[1]["json"]
        
        assert "tags" in sent_payload
        assert "model" in sent_payload["tags"]
        assert sent_payload["tags"]["model"] == "gpt-3.5-turbo"


if __name__ == "__main__":
    pytest.main([__file__])
