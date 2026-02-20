# Common CodeQL Alert Types and Remediation

This reference guide covers the most common code scanning alerts and provides remediation guidance for each.

## Python Security Alerts

### Clear-text Logging of Sensitive Information

**Rule ID:** `py/clear-text-logging-sensitive-data`

**Severity:** Error (6.5 - Medium)

**Description:**
Logging sensitive data in clear text can expose credentials, tokens, personal information, or other confidential data to unauthorized users who have access to log files.

**Common Triggers:**
```python
# Logging request headers (may contain auth tokens)
logger.info(f"Request: {request.headers}")

# Logging passwords or API keys
logger.debug(f"Connecting with password: {password}")

# Logging full user objects (may contain PII)
logger.info(f"User data: {user}")

# Logging environment variables (may contain secrets)
logger.info(f"Config: {os.environ}")
```

**Remediation:**

1. **Redaction Function:**
```python
SENSITIVE_FIELDS = {
    "authorization", "cookie", "password", "token",
    "api_key", "secret", "credit_card", "ssn"
}

def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields from data before logging."""
    redacted = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted

# Use in logging
logger.info(f"Request: {redact_sensitive(dict(request.headers))}")
```

2. **Structured Logging with Filters:**
```python
import logging

class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from logs."""

    def filter(self, record):
        # Redact patterns like token=xxx, password=xxx
        if hasattr(record, 'msg'):
            record.msg = re.sub(
                r'(token|password|api_key)=[^\s]+',
                r'\1=***REDACTED***',
                str(record.msg)
            )
        return True

# Apply filter to logger
logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())
```

3. **Avoid Logging Sensitive Data Entirely:**
```python
# Instead of logging everything
logger.info(f"User {user.id} logged in")  # Log ID only

# Instead of logging tokens
logger.info(f"Auth header present: {bool(request.headers.get('authorization'))}")
```

**Best Practices:**
- Never log passwords, tokens, API keys, or PII
- Use structured logging with field-level control
- Implement automatic redaction at the logging layer
- Review log outputs regularly for sensitive data leaks
- Use separate logging levels for debug (more detail) vs. production (minimal)

---

### Insecure Randomness

**Rule ID:** `py/insecure-randomness`

**Severity:** Warning (7.8 - High for cryptographic uses)

**Description:**
Using non-cryptographically secure random number generators (like `random.random()` or `random.randint()`) for security-sensitive operations can make the system predictable and vulnerable to attacks.

**Common Triggers:**
```python
import random

# Generating session tokens
session_id = ''.join(random.choices(string.ascii_letters, k=32))

# Creating password reset tokens
reset_token = random.randint(100000, 999999)

# Generating API keys
api_key = f"key_{random.randrange(1000000000)}"

# Creating CSRF tokens
csrf_token = str(random.random())
```

**Why It's Insecure:**
Python's `random` module uses the Mersenne Twister PRNG, which is:
- Predictable if attacker observes several outputs
- Not suitable for cryptographic purposes
- Can be seeded and reproduced

**Remediation:**

1. **Use `secrets` Module (Python 3.6+):**
```python
import secrets
import string

# Generate secure random tokens
session_id = secrets.token_urlsafe(32)  # URL-safe base64 token

# Generate hex tokens
reset_token = secrets.token_hex(16)  # 32-character hex string

# Generate secure random numbers
secure_random = secrets.randbelow(1000000)  # 0 to 999999

# Generate random strings
alphabet = string.ascii_letters + string.digits
api_key = ''.join(secrets.choice(alphabet) for _ in range(32))

# Generate CSRF tokens
csrf_token = secrets.token_urlsafe(32)
```

2. **Use `os.urandom()` for Bytes:**
```python
import os
import base64

# Generate random bytes
random_bytes = os.urandom(32)

# Convert to base64 for storage
token = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
```

3. **Use `uuid.uuid4()` for UUIDs:**
```python
import uuid

# Generate random UUID (uses cryptographically secure RNG)
unique_id = uuid.uuid4()
session_id = str(unique_id)
```

**When `random` is OK:**
```python
import random

# Selecting a random greeting message
greeting = random.choice(["Hello", "Hi", "Hey"])

# Shuffling a list for display purposes
random.shuffle(recommendations)

# Generating test data
test_id = random.randint(1, 1000)

# Simulations or games (non-security contexts)
dice_roll = random.randint(1, 6)
```

**Decision Tree:**
```
Is this for security purposes?
├─ Yes → Use `secrets` or `os.urandom()`
│   ├─ Tokens, keys, passwords
│   ├─ Session IDs, CSRF tokens
│   └─ Cryptographic nonces
└─ No → `random` is fine
    ├─ Simulations
    ├─ Games
    ├─ Randomized displays
    └─ Test data generation
```

**Best Practices:**
- Always use `secrets` for tokens, keys, and security-sensitive values
- Use `os.urandom()` when you need random bytes
- Reserve `random` module for non-security purposes only
- Document why `random` is safe if used in test code

---

### Binding Socket to All Network Interfaces

**Rule ID:** `py/bind-socket-all-network-interfaces`

**Severity:** Warning (7.5 - High)

**Description:**
Binding a socket to `0.0.0.0` (all network interfaces) can expose the service to unintended networks and attackers. This is particularly risky in cloud environments with multiple network interfaces.

**Common Triggers:**
```python
# Flask
app.run(host='0.0.0.0', port=5000)

# FastAPI/Uvicorn
uvicorn.run(app, host='0.0.0.0', port=8000)

# Socket programming
sock.bind(('0.0.0.0', 8080))

# Django
# manage.py runserver 0.0.0.0:8000
```

**Security Risks:**
1. **Exposure to Multiple Networks:**
   - Service listens on public, private, and VPN interfaces
   - Attacker on any connected network can reach the service

2. **Cloud Metadata Services:**
   - Some cloud providers have metadata services on specific interfaces
   - Binding to all interfaces may expose unintended access paths

3. **Container Networking:**
   - In some setups, may expose service outside container network

**Remediation:**

1. **Bind to Localhost Only (Development):**
```python
# Development: only accessible from the same machine
uvicorn.run(app, host='127.0.0.1', port=8000)
app.run(host='127.0.0.1', port=5000)
```

2. **Bind to Specific Private IP (Production):**
```python
import os

# Get the specific interface IP from environment
BIND_HOST = os.getenv('BIND_HOST', '127.0.0.1')

uvicorn.run(app, host=BIND_HOST, port=8000)
```

3. **Use Reverse Proxy Architecture:**
```python
# Application binds to localhost
uvicorn.run(app, host='127.0.0.1', port=8000)

# Nginx or Traefik handles external access
# nginx.conf:
# server {
#     listen 80;
#     location / {
#         proxy_pass http://127.0.0.1:8000;
#     }
# }
```

4. **Container-Specific Configuration:**
```python
# For Docker containers, may need 0.0.0.0 but with network isolation
import os

# Use 0.0.0.0 in containers (isolated network)
# Use 127.0.0.1 for direct deployment
IS_CONTAINERIZED = os.getenv('CONTAINER', 'false') == 'true'
BIND_HOST = '0.0.0.0' if IS_CONTAINERIZED else '127.0.0.1'

uvicorn.run(app, host=BIND_HOST, port=8000)
```

**When `0.0.0.0` is Acceptable:**

1. **Behind a Reverse Proxy:**
   - Service runs on isolated Docker network
   - Traefik/Nginx handles external requests
   - Container is not directly exposed to internet

2. **Proper Firewall Rules:**
   - Host firewall blocks direct access
   - Only reverse proxy can reach the service
   - Network segmentation in place

3. **Network Isolation:**
   - Service runs on private network
   - No route to public internet from that interface
   - Documented in security architecture

**Dismissal Template:**
```markdown
Alert dismissed as wont-fix.

Reason: Application runs in Docker container with isolated networking.

Security controls:
- Container on isolated Docker bridge network
- Traefik reverse proxy handles all external requests
- Host firewall prevents direct external access
- Container runs as non-root user
- No privileged access or host networking mode

Architecture: Internet → Traefik (TLS) → Docker Network → Container
```

**Best Practices:**
- Default to `127.0.0.1` for development
- Use specific IPs for production deployment
- Document network architecture when using `0.0.0.0`
- Implement defense in depth (firewall + reverse proxy)
- Regular security audits of network exposure

---

### SQL Injection

**Rule ID:** `py/sql-injection`

**Severity:** Error (9.8 - Critical)

**Description:**
Constructing SQL queries by concatenating user input can allow attackers to inject malicious SQL code and access, modify, or delete data.

**Common Triggers:**
```python
# Direct string concatenation
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")

# String formatting
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)

# Format method
query = "DELETE FROM posts WHERE id = {}".format(post_id)
cursor.execute(query)
```

**Remediation:**

1. **Use Parameterized Queries:**
```python
# Correct: parameterized query
cursor.execute(
    "SELECT * FROM users WHERE username = ?",
    (username,)
)

# With multiple parameters
cursor.execute(
    "INSERT INTO users (name, email) VALUES (?, ?)",
    (name, email)
)
```

2. **Use ORM (SQLAlchemy, Django ORM):**
```python
# SQLAlchemy
from sqlalchemy import select

stmt = select(User).where(User.username == username)
result = session.execute(stmt)

# Django ORM
User.objects.filter(username=username)
```

3. **Validate Input:**
```python
from pydantic import BaseModel, validator

class UserQuery(BaseModel):
    user_id: int

    @validator('user_id')
    def validate_id(cls, v):
        if v < 0:
            raise ValueError('ID must be positive')
        return v
```

**Best Practices:**
- Always use parameterized queries or ORMs
- Never concatenate user input into SQL strings
- Validate and sanitize all inputs
- Use prepared statements
- Implement least privilege database access

---

## General Security Practices

### Prioritization

1. **Critical (9.0-10.0):** Fix immediately
   - SQL injection
   - Remote code execution
   - Authentication bypasses

2. **High (7.0-8.9):** Fix within sprint
   - Insecure randomness in security contexts
   - Unvalidated redirects
   - XSS vulnerabilities

3. **Medium (4.0-6.9):** Fix within release cycle
   - Clear-text logging
   - Missing encryption
   - Information disclosure

4. **Low (0.1-3.9):** Review and fix as time permits
   - Code quality issues
   - Deprecated functions
   - Style violations

### Testing Fixes

Always test security fixes:
```python
# Test that fix doesn't break functionality
def test_user_lookup_after_fix():
    result = get_user_by_name("john")
    assert result.name == "john"

# Test that vulnerability is closed
def test_sql_injection_prevented():
    malicious_input = "'; DROP TABLE users; --"
    result = get_user_by_name(malicious_input)
    assert result is None  # Should safely return None

# Test edge cases
def test_special_characters_handled():
    result = get_user_by_name("O'Brien")
    assert result is not None
```

### Documentation

Document all security decisions:
```markdown
## Security Decision: Alert #5 Dismissed

**Date:** 2026-02-06
**Alert:** Binding to all interfaces
**Decision:** Dismissed as wont-fix
**Rationale:** Container networking requirement
**Controls:** Reverse proxy, firewall, network isolation
**Review Date:** 2027-02-06
```

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CodeQL Query Help](https://codeql.github.com/codeql-query-help/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [GitHub Code Scanning Documentation](https://docs.github.com/en/code-security/code-scanning)
- [CWE - Common Weakness Enumeration](https://cwe.mitre.org/)

---

## Quick Reference: Python Security Modules

```python
# Cryptographically secure random values
import secrets
token = secrets.token_urlsafe(32)

# Secure random bytes
import os
random_bytes = os.urandom(32)

# Password hashing
from passlib.hash import bcrypt
hashed = bcrypt.hash("password")

# Input validation
from pydantic import BaseModel, validator

# SQL safety
from sqlalchemy import text
stmt = text("SELECT * FROM users WHERE id = :id")
result = conn.execute(stmt, {"id": user_id})
```
