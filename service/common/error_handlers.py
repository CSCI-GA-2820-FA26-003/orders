######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Module: error_handlers
"""
import uuid

from flask import jsonify, request, g
from flask import current_app as app  # Import Flask application
from service.models import DataValidationError
from . import status


def _request_id():
    """Return the request id for the active request, generating one if needed."""
    return getattr(g, "request_id", request.headers.get("X-Request-ID") or str(uuid.uuid4()))


def _error_response(code, error_code, message, status_code, details=None):
    """Build a consistent JSON error payload for the client."""
    request_id = _request_id()
    payload = {
        "status": status_code,
        "error": {
            "code": error_code,
            "message": message,
            "request_id": request_id,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    response = jsonify(payload)
    response.status_code = status_code
    response.headers["X-Request-ID"] = request_id
    return response, status_code


######################################################################
# Error Handlers
######################################################################
@app.errorhandler(DataValidationError)
def request_validation_error(error):
    """Handles Value Errors from bad data"""
    app.logger.warning(str(error))
    details = [{"field": "request", "reason": str(error)}]
    return _error_response(
        "validation_error",
        "validation_error",
        str(error),
        status.HTTP_400_BAD_REQUEST,
        details=details,
    )


@app.errorhandler(status.HTTP_400_BAD_REQUEST)
def bad_request(error):
    """Handles bad requests with 400_BAD_REQUEST"""
    message = str(error)
    app.logger.warning(message)
    return _error_response(
        "validation_error",
        "validation_error",
        message,
        status.HTTP_400_BAD_REQUEST,
        details=[{"field": "request", "reason": message}],
    )


@app.errorhandler(status.HTTP_404_NOT_FOUND)
def not_found(error):
    """Handles resources not found with 404_NOT_FOUND"""
    message = str(error)
    app.logger.warning(message)
    return _error_response(
        "not_found",
        "not_found",
        message,
        status.HTTP_404_NOT_FOUND,
    )


@app.errorhandler(status.HTTP_405_METHOD_NOT_ALLOWED)
def method_not_supported(error):
    """Handles unsupported HTTP methods with 405_METHOD_NOT_SUPPORTED"""
    message = str(error)
    app.logger.warning(message)
    return _error_response(
        "method_not_allowed",
        "method_not_allowed",
        message,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    )


@app.errorhandler(status.HTTP_409_CONFLICT)
def conflict(error):
    """Handles conflicts with 409_CONFLICT"""
    message = str(error)
    app.logger.warning(message)
    return _error_response(
        "conflict",
        "conflict",
        message,
        status.HTTP_409_CONFLICT,
    )


@app.errorhandler(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
def mediatype_not_supported(error):
    """Handles unsupported media requests with 415_UNSUPPORTED_MEDIA_TYPE"""
    message = str(error)
    app.logger.warning(message)
    return _error_response(
        "unsupported_media",
        "unsupported_media",
        message,
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    )


@app.errorhandler(status.HTTP_500_INTERNAL_SERVER_ERROR)
def internal_server_error(error):
    """Handles unexpected server error with 500_SERVER_ERROR"""
    app.logger.exception("Unhandled server error")
    return _error_response(
        "internal_error",
        "internal_error",
        "An unexpected error occurred.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.errorhandler(status.HTTP_503_SERVICE_UNAVAILABLE)
def service_unavailable(error):
    """Handles service unavailable responses with 503_SERVICE_UNAVAILABLE."""
    app.logger.warning(str(error))
    return _error_response(
        "unavailable",
        "unavailable",
        "The service is temporarily unavailable.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.errorhandler(Exception)
def generic_exception_handler(error):
    """Ensure all unhandled exceptions return a safe JSON payload."""
    app.logger.exception("Unhandled exception")
    return _error_response(
        "internal_error",
        "internal_error",
        "An unexpected error occurred.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
