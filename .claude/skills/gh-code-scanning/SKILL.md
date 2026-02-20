# GitHub Code Scanning Alert Management

---
name: gh-code-scanning
disable-model-invocation: true
user-invocable: true
---

This skill provides a structured workflow for managing GitHub Code Scanning security alerts using the GitHub CLI (`gh`).

## Commands

- `/gh-code-scanning list` - List all open code scanning alerts
- `/gh-code-scanning detail <alert-number>` - Get detailed information about a specific alert
- `/gh-code-scanning fix <alert-number>` - Start workflow to fix an alert
- `/gh-code-scanning dismiss <alert-number> <reason>` - Dismiss an alert with justification
- `/gh-code-scanning verify <alert-number>` - Verify an alert has been fixed

## Dynamic Context

Before executing any command, gather current repository context:

```bash
# Get current repository
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

# Get current branch
BRANCH=$(git branch --show-current)

# Count open alerts
ALERT_COUNT=$(gh api repos/$REPO/code-scanning/alerts --jq '[.[] | select(.state == "open")] | length')
```

## Workflows

### List Command

**Usage:** `/gh-code-scanning list`

**Workflow:**

1. Fetch all open alerts:
```bash
gh api repos/schwichtgit/ai-resume/code-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, rule: .rule.id, severity: .rule.severity, location: .most_recent_instance.location.path}'
```

2. Format output as a table showing:
   - Alert number
   - Rule ID (e.g., "py/clear-text-logging-sensitive-data")
   - Severity (error, warning, note)
   - File location

3. Include summary count and next steps suggestion

**Example Output:**
```
Open Code Scanning Alerts (3)

#1  py/clear-text-logging-sensitive-data  error    api-service/main.py
#2  py/bind-socket-all-network-interfaces warning  api-service/main.py
#3  py/bind-socket-all-network-interfaces warning  api-service/chat_service.py

Use /gh-code-scanning detail <N> to see full details
Use /gh-code-scanning fix <N> to start fixing an alert
```

### Detail Command

**Usage:** `/gh-code-scanning detail <alert-number>`

**Workflow:**

1. Fetch full alert details:
```bash
gh api repos/schwichtgit/ai-resume/code-scanning/alerts/$ARGUMENTS
```

2. Extract and display:
   - Rule ID and description
   - Severity and security severity level
   - Affected file and line numbers
   - Code snippet from most_recent_instance
   - Recommendation from rule.help

3. Provide suggested next actions:
   - Fix the issue if it's a valid security concern
   - Dismiss if it's a false positive or won't-fix

**Example Output:**
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
to unauthorized users.

Recommendation:
Avoid logging sensitive information directly. Redact or mask credentials, tokens,
and personal data before logging.

Next steps:
- /gh-code-scanning fix 1 - Start fixing this alert
- /gh-code-scanning dismiss 1 <reason> - Dismiss if false positive
```

### Fix Command

**Usage:** `/gh-code-scanning fix <alert-number>`

**Workflow:**

1. Get alert details (same as detail command)

2. Read the affected file:
```bash
# Extract file path from alert JSON
FILE_PATH=$(gh api repos/schwichtgit/ai-resume/code-scanning/alerts/$ARGUMENTS --jq '.most_recent_instance.location.path')
```

3. Use Read tool to view file content with context around the issue

4. Analyze the vulnerability and propose a fix based on:
   - Alert rule description
   - Best practices for the vulnerability type
   - Existing code patterns in the file

5. Ask user to confirm the proposed fix

6. If confirmed, apply the fix using Edit tool

7. Commit the change:
```bash
git add $FILE_PATH
git commit -m "fix: Resolve code scanning alert #$ARGUMENTS - $(rule_id)

Address $(rule_description) in $(file_path).

Security improvement: $(brief_explanation)"
```

8. Push changes and wait for code scanning rescan

9. Provide instructions for verification:
```
Fix committed. Wait 5-10 minutes for code scanning to rescan, then:
/gh-code-scanning verify $ARGUMENTS
```

**Important Notes:**
- Always show the proposed change before applying
- Include security context in commit message
- Link to alert in commit message when possible
- Test the change if possible before committing

### Dismiss Command

**Usage:** `/gh-code-scanning dismiss <alert-number> <reason>`

**Valid Reasons:**
- `false-positive` - Alert is not a real issue
- `wont-fix` - Valid issue but won't be fixed
- `used-in-tests` - Only used in test code

**Workflow:**

1. Validate the reason is one of the accepted values

2. Get alert details to show user what they're dismissing:
```bash
gh api repos/schwichtgit/ai-resume/code-scanning/alerts/$ARGUMENTS
```

3. Display alert summary and ask for confirmation

4. If confirmed, dismiss the alert:
```bash
gh api --method PATCH repos/schwichtgit/ai-resume/code-scanning/alerts/$ARGUMENTS \
  -f state='dismissed' \
  -f dismissed_reason='$REASON' \
  -f dismissed_comment='$COMMENT'
```

5. Document the dismissal:
   - Add entry to docs/SECURITY.md under "Dismissed Alerts"
   - Include alert number, rule ID, reason, and rationale
   - Commit documentation update

6. Confirm dismissal:
```
Alert #$ARGUMENTS dismissed as $REASON

Documentation updated in docs/SECURITY.md
```

**Example:**
```bash
/gh-code-scanning dismiss 2 wont-fix

# After confirmation:
Alert #2 dismissed as wont-fix

Reason: Binding to 0.0.0.0 is required for Docker container networking.
The service runs in an isolated container network with firewall rules.

Documentation updated in docs/SECURITY.md
```

### Verify Command

**Usage:** `/gh-code-scanning verify <alert-number>`

**Workflow:**

1. Fetch current state of the alert:
```bash
gh api repos/schwichtgit/ai-resume/code-scanning/alerts/$ARGUMENTS
```

2. Check alert state:
   - If `state == "fixed"` or `state == "closed"`: Success! Alert resolved.
   - If `state == "open"`: Still open, check if recent commits addressed it
   - If `state == "dismissed"`: Show dismissal info

3. For open alerts, check recent scans:
```bash
# Get most recent analysis
gh api repos/schwichtgit/ai-resume/code-scanning/analyses \
  --jq '.[0] | {commit_sha, created_at, results_count}'
```

4. Provide status and next steps:

**If fixed:**
```
✓ Alert #$ARGUMENTS has been resolved!

State: fixed
Fixed in: <commit_sha>
Fixed at: <timestamp>

The code scanning system confirmed the vulnerability has been addressed.
```

**If still open:**
```
Alert #$ARGUMENTS is still open

Last scan: <timestamp> (<commit_sha>)

Possible reasons:
- Fix not yet committed
- Code scanning hasn't rescanned yet (can take 5-10 minutes)
- Fix didn't fully address the issue

Next steps:
- Wait a few minutes and try /gh-code-scanning verify $ARGUMENTS again
- Review the fix with /gh-code-scanning detail $ARGUMENTS
- Check recent commits affected the right file/lines
```

## Best Practices

### Security-First Approach

1. **Prioritize by severity**: Fix `error` level alerts before `warning` or `note`
2. **Understand the vulnerability**: Use detail command before attempting fixes
3. **Test fixes**: Ensure fixes don't break functionality
4. **Document dismissals**: Always provide clear rationale for dismissed alerts

### Workflow Tips

1. **Start broad, then narrow**: Use `list` to see all alerts, then `detail` for specifics
2. **Batch similar fixes**: Fix all instances of the same rule type together
3. **Verify after fixes**: Always use `verify` after a fix to confirm resolution
4. **Keep security docs updated**: Document all dismissals and major fixes

### Common Alert Types

See `reference/alert-types.md` for detailed information on:
- Clear-text logging of sensitive information
- Insecure randomness
- Binding socket to all network interfaces
- And more...

### Working with False Positives

If an alert appears to be a false positive:

1. Use `detail` to understand why it was flagged
2. Consider if there's a way to refactor code to avoid the pattern
3. If truly a false positive, use `dismiss` with clear rationale
4. Document in SECURITY.md why it's safe in this context

## Troubleshooting

### "gh: command not found"

Install GitHub CLI:
```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

Then authenticate:
```bash
gh auth login
```

### "Resource not accessible by integration"

Ensure you have the required permissions:
- `security_events: write` for dismissing alerts
- `security_events: read` for viewing alerts

Check authentication status:
```bash
gh auth status
```

### Alert not updating after fix

Code scanning can take 5-10 minutes to rescan after a push. Wait and retry:
```bash
# Check when last scan ran
gh api repos/schwichtgit/ai-resume/code-scanning/analyses --jq '.[0].created_at'

# If recent, wait a bit longer
# If old, check if Actions are running
gh run list --limit 5
```

### Manual fallback

If the skill fails, you can always use `gh` commands directly:

```bash
# List alerts
gh api repos/schwichtgit/ai-resume/code-scanning/alerts

# Get alert detail
gh api repos/schwichtgit/ai-resume/code-scanning/alerts/1

# Dismiss alert
gh api --method PATCH repos/schwichtgit/ai-resume/code-scanning/alerts/1 \
  -f state='dismissed' \
  -f dismissed_reason='false-positive' \
  -f dismissed_comment='Not actually vulnerable in this context'
```

## Examples

See the `examples/` directory for detailed walkthroughs:
- `fix-example.md` - Complete workflow for fixing a clear-text logging alert
- `dismiss-example.md` - Dismissing a won't-fix alert with documentation

## Reference

- `reference/alert-types.md` - Common CodeQL alert types and remediation guidance
- [GitHub Code Scanning API](https://docs.github.com/en/rest/code-scanning)
- [CodeQL Query Help](https://codeql.github.com/codeql-query-help/)

## Allowed Tools

This skill uses the following tools:
- `Bash(gh *)` - GitHub CLI commands for API access
- `Bash(git *)` - Git commands for commits and branch operations
- `Read` - Reading source files to analyze vulnerabilities
- `Write` - Updating documentation (SECURITY.md)
- `Edit` - Applying security fixes to source files
- `Glob` - Finding related files
- `Grep` - Searching for similar patterns

## Invocation

This skill is **user-invocable only**. It will not be automatically invoked. Always call it explicitly:

```
/gh-code-scanning list
/gh-code-scanning detail 1
/gh-code-scanning fix 1
/gh-code-scanning dismiss 2 wont-fix
/gh-code-scanning verify 1
```

The skill does not invoke the AI model directly. All workflows are deterministic and based on GitHub API responses and code analysis.
