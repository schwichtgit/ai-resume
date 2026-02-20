# Fix Example: Clear-text Logging of Sensitive Information

This example demonstrates the complete workflow for fixing GitHub Code Scanning Alert #1 using the `/gh-code-scanning` skill.

## Initial State

**Alert:** #1 - Clear-text logging of sensitive information
**Rule:** `py/clear-text-logging-sensitive-data`
**Severity:** error
**Location:** `api-service/main.py:45-47`

## Step 1: List Alerts

```bash
/gh-code-scanning list
```

**Output:**
```
Open Code Scanning Alerts (4)

#1  py/clear-text-logging-sensitive-data  error    api-service/main.py
#2  py/bind-socket-all-network-interfaces warning  api-service/main.py
#3  py/bind-socket-all-network-interfaces warning  api-service/chat_service.py
#4  py/insecure-randomness                 warning  ingest/utils.py

Use /gh-code-scanning detail <N> to see full details
```

## Step 2: Get Alert Details

```bash
/gh-code-scanning detail 1
```

**Output:**
```
Alert #1: Clear-text logging of sensitive information

Rule: py/clear-text-logging-sensitive-data
Severity: error
Security Severity: 6.5 (medium)

Location: api-service/main.py:45-47

Code:
    logger.info(f"Request from {request.client.host}: {request.headers}")

Issue:
Sensitive data is written to a log file. This can expose confidential information
to unauthorized users. The request headers may contain sensitive data such as
authorization tokens, session cookies, or API keys.

Recommendation:
Avoid logging sensitive information directly. Redact or mask credentials, tokens,
and personal data before logging. Consider implementing a logging filter to
automatically redact known sensitive header names.

Next steps:
- /gh-code-scanning fix 1 - Start fixing this alert
- /gh-code-scanning dismiss 1 <reason> - Dismiss if false positive
```

## Step 3: Fix the Alert

```bash
/gh-code-scanning fix 1
```

**Workflow:**

1. The skill reads `api-service/main.py` and identifies the problematic code:

```python
# BEFORE (vulnerable)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request from {request.client.host}: {request.headers}")
    response = await call_next(request)
    return response
```

2. The skill proposes a fix:

```python
# AFTER (secure)
# Define sensitive headers to redact
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "proxy-authorization"
}

def redact_sensitive_headers(headers: dict) -> dict:
    """Redact sensitive header values for logging."""
    redacted = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted

@app.middleware("http")
async def log_requests(request: Request, call_next):
    safe_headers = redact_sensitive_headers(dict(request.headers))
    logger.info(f"Request from {request.client.host}: {safe_headers}")
    response = await call_next(request)
    return response
```

3. User confirms the fix

4. The skill applies the changes and commits:

```bash
git add api-service/main.py
git commit -m "fix: Resolve code scanning alert #1 - clear-text logging

Address py/clear-text-logging-sensitive-data in api-service/main.py.

Security improvement: Implement header redaction to prevent logging of
sensitive authentication tokens, cookies, and API keys. The middleware
now filters sensitive headers before logging requests.

Resolves: Code Scanning Alert #1"
```

5. Push and wait for rescan:

```
Fix committed: abc1234

Changes:
- Added redact_sensitive_headers() function
- Updated log_requests middleware to use redaction
- Sensitive headers (authorization, cookie, x-api-key, etc.) now masked

Wait 5-10 minutes for code scanning to rescan, then:
/gh-code-scanning verify 1
```

## Step 4: Verify the Fix

After waiting for code scanning rescan:

```bash
/gh-code-scanning verify 1
```

**Output:**
```
✓ Alert #1 has been resolved!

State: fixed
Fixed in: abc1234567890abcdef1234567890abcdef1234
Fixed at: 2026-02-06T15:30:22Z

The code scanning system confirmed the vulnerability has been addressed.
```

## Key Takeaways

1. **Understand the vulnerability first**: Used `detail` command to fully understand the security risk
2. **Implement proper mitigation**: Rather than removing logging entirely, implemented redaction
3. **Maintain functionality**: Request logging still works, but sensitive data is protected
4. **Clear commit message**: Included alert number, rule ID, and security improvement description
5. **Verify resolution**: Confirmed the fix with code scanning system

## Related Alerts

This pattern can be applied to other logging vulnerabilities:
- Logging passwords in authentication flows
- Logging API responses that may contain PII
- Logging database query results with sensitive data

## Best Practices Applied

1. **Defense in depth**: Redaction function can be reused across the application
2. **Configurable**: Sensitive headers list can be easily extended
3. **Testable**: Redaction function is pure and easy to unit test
4. **Documented**: Commit message explains the security improvement
5. **Minimal change**: Fixed only what was necessary, didn't refactor unrelated code

## Testing the Fix

After applying the fix, test that logging still works but is safe:

```python
# Test redaction function
def test_redact_sensitive_headers():
    headers = {
        "authorization": "Bearer secret-token",
        "content-type": "application/json",
        "cookie": "session=abc123",
        "user-agent": "Mozilla/5.0"
    }

    result = redact_sensitive_headers(headers)

    assert result["authorization"] == "***REDACTED***"
    assert result["cookie"] == "***REDACTED***"
    assert result["content-type"] == "application/json"
    assert result["user-agent"] == "Mozilla/5.0"
```

## PR Reference

If this fix was part of a pull request:

```
Pull Request: #42
Title: Fix code scanning alert: Clear-text logging of sensitive data
Branch: fix/code-scanning-alert-1
Status: Merged

Files changed:
- api-service/main.py (+15, -1)

Tests added:
- test_redact_sensitive_headers()
- test_request_logging_middleware()

Code Scanning Status: ✓ All alerts resolved
```
