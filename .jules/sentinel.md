## 2024-05-24 - [Defense in Depth: Security Headers]
**Vulnerability:** Missing fundamental security headers on HTTP responses.
**Learning:** Even internal sidecar APIs should implement basic security headers (like Content-Security-Policy, Strict-Transport-Security, X-Frame-Options) as a defense-in-depth measure against client-side attacks, especially if the API ever gets exposed or consumed by a frontend application.
**Prevention:** Implement a global middleware in the FastAPI application to automatically attach security headers to all responses.
