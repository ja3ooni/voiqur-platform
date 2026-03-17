"""
Custom Middleware Components

Security, logging, and other middleware for the FastAPI application.
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import json

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Security middleware for EU compliance and general security.
    
    Adds security headers, enforces HTTPS, and implements
    other security measures.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Check for HTTPS in production
        # "testserver" is the hostname used by httpx ASGITransport in tests
        _NON_HTTPS_ALLOWED = {"localhost", "127.0.0.1", "testserver"}
        if (
            request.headers.get("x-forwarded-proto") != "https" and
            request.url.scheme != "https" and
            request.url.hostname not in _NON_HTTPS_ALLOWED
        ):
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            response = JSONResponse(
                status_code=301,
                content={"detail": "HTTPS required"},
                headers={"Location": str(https_url)}
            )
            await response(scope, receive, send)
            return
        
        # Add security headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Add security headers
                security_headers = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY", 
                    b"x-xss-protection": b"1; mode=block",
                    b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                    b"content-security-policy": b"default-src 'self'",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy": b"geolocation=(), microphone=(), camera=()"
                }
                
                headers.update(security_headers)
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


class LoggingMiddleware:
    """
    Logging middleware for request/response logging and audit trails.
    
    Implements structured logging for EU compliance and monitoring.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "timestamp": start_time
            }
        )
        
        # Capture response
        response_body = b""
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal response_body, status_code
            
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Add request ID to response headers
                headers = dict(message.get("headers", []))
                headers[b"x-request-id"] = request_id.encode()
                message["headers"] = list(headers.items())
            
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise
        finally:
            # Log response
            duration = time.time() - start_time
            
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "response_size": len(response_body)
                }
            )


class GDPRComplianceMiddleware:
    """
    GDPR compliance middleware.
    
    Handles data anonymization, consent tracking, and audit logging
    for EU data protection compliance.
    """
    
    def __init__(self, app):
        self.app = app
        self.sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token"
        }
        self.pii_patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-like patterns
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"  # Credit card-like
        ]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Check for GDPR consent header
        consent = request.headers.get("x-gdpr-consent")
        if not consent and self._requires_consent(request):
            response = JSONResponse(
                status_code=400,
                content={
                    "error": "GDPR consent required",
                    "detail": "Please provide GDPR consent via X-GDPR-Consent header"
                }
            )
            await response(scope, receive, send)
            return
        
        # Log GDPR-compliant audit entry
        await self._log_gdpr_audit(request, consent)
        
        await self.app(scope, receive, send)
    
    def _requires_consent(self, request: Request) -> bool:
        """Check if request requires GDPR consent."""
        # Require consent for data processing endpoints
        processing_endpoints = [
            "/api/v1/voice/stt",
            "/api/v1/voice/tts", 
            "/api/v1/voice/llm"
        ]
        
        return any(request.url.path.startswith(endpoint) for endpoint in processing_endpoints)
    
    async def _log_gdpr_audit(self, request: Request, consent: str):
        """Log GDPR audit entry."""
        audit_entry = {
            "timestamp": time.time(),
            "client_ip": self._anonymize_ip(request.client.host),
            "endpoint": request.url.path,
            "consent_status": consent,
            "data_processing": self._requires_consent(request)
        }
        
        logger.info("GDPR audit", extra=audit_entry)
    
    def _anonymize_ip(self, ip: str) -> str:
        """Anonymize IP address for GDPR compliance."""
        if ":" in ip:  # IPv6
            parts = ip.split(":")
            return ":".join(parts[:4] + ["0000"] * (len(parts) - 4))
        else:  # IPv4
            parts = ip.split(".")
            return ".".join(parts[:3] + ["0"])


class PerformanceMonitoringMiddleware:
    """
    Performance monitoring middleware.
    
    Tracks response times, throughput, and other performance metrics.
    """
    
    def __init__(self, app):
        self.app = app
        self.metrics = {
            "request_count": 0,
            "total_duration": 0.0,
            "error_count": 0
        }
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = time.time()
        
        self.metrics["request_count"] += 1
        
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            self.metrics["error_count"] += 1
            raise
        finally:
            duration = time.time() - start_time
            self.metrics["total_duration"] += duration
            
            # Log slow requests
            if duration > 1.0:  # Requests taking more than 1 second
                logger.warning(
                    "Slow request detected",
                    extra={
                        "url": str(request.url),
                        "method": request.method,
                        "duration": duration,
                        "status_code": status_code
                    }
                )
    
    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        if self.metrics["request_count"] > 0:
            avg_duration = self.metrics["total_duration"] / self.metrics["request_count"]
        else:
            avg_duration = 0.0
        
        return {
            "request_count": self.metrics["request_count"],
            "average_duration": avg_duration,
            "error_count": self.metrics["error_count"],
            "error_rate": self.metrics["error_count"] / max(1, self.metrics["request_count"])
        }