from unittest.mock import MagicMock

import pytest
import requests

from api.api_call import call_them


def test_call_them_success(mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status": "ok"}'
    mock_response.json.return_value = {"status": "ok"}

    mock_send = mocker.patch("api.api_call.send_request", return_value=mock_response)

    result = call_them("https://example.com", "get")

    assert result == mock_response
    mock_send.assert_called_once_with(url="https://example.com", method="GET")
    mock_response.raise_for_status.assert_called_once()


def test_call_them_retry_then_success(mocker):
    mock_response = MagicMock()

    mock_sleep = mocker.patch("api.api_call.sleep")

    mock_send = mocker.patch(
        "api.api_call.send_request",
        side_effect=[
            requests.exceptions.ConnectTimeout("Timeout 1"),
            requests.exceptions.ConnectTimeout("Timeout 2"),
            mock_response,
        ],
    )

    result = call_them("https://example.com", "post", data={"key": "val"})

    assert result == mock_response
    assert mock_send.call_count == 3
    assert mock_sleep.call_count == 2


def test_call_them_max_retries_exceeded(mocker):
    mocker.patch("api.api_call.sleep")

    mocker.patch(
        "api.api_call.send_request",
        side_effect=requests.exceptions.ConnectTimeout("Timeout"),
    )

    with pytest.raises(requests.exceptions.ConnectTimeout):
        call_them("https://example.com", "get")


def test_call_them_with_custom_non_requests_response(mocker):
    class CustomResponse:
        def __init__(self):
            self.text = "custom_data"

        def json(self):
            return {"data": "custom"}

        def raise_for_status(self):
            pass

    custom_resp = CustomResponse()
    mocker.patch("api.api_call.send_request", return_value=custom_resp)

    result = call_them("https://example.com", "get")

    assert result == custom_resp
    assert result.text == "custom_data"
    assert result.json() == {"data": "custom"}


def test_call_them_logs_exception_on_max_retries(mocker):
    mocker.patch("api.api_call.sleep")
    mocker.patch(
        "api.api_call.send_request",
        side_effect=requests.exceptions.ConnectTimeout("Timeout Error"),
    )

    mock_logger = mocker.patch("api.api_call.logger")

    with pytest.raises(requests.exceptions.ConnectTimeout):
        call_them("https://example.com", "get")

    # Επιβεβαιώνουμε ότι καλέστηκε η μέθοδος exception
    mock_logger.exception.assert_called_once()
    assert "Max retries exceeded" in mock_logger.exception.call_args[0][0]
