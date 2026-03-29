# Security Policy

## Supported versions

Quest Log is a single-branch project. Security fixes are applied to the latest release only.

| Version | Supported |
|---|---|
| Latest (`main`) | Yes |
| Older releases | No |

Always run the latest image from `ghcr.io/johnfawkes/quest-log:latest` or the most recent versioned tag.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues through [GitHub Security Advisories](https://github.com/JohnFawkes/quest-log/security/advisories/new). This creates a private disclosure visible only to the repository owner.

Include as much detail as you can:
- Description of the vulnerability and its potential impact
- Steps to reproduce
- Quest Log version and deployment method (Docker / local Python)
- Any proof-of-concept code or screenshots (redact real credentials)

## Response timeline

| Stage | Target |
|---|---|
| Initial acknowledgement | Within 7 days |
| Triage and severity assessment | Within 14 days |
| Fix released | Dependent on severity and complexity |

Critical vulnerabilities (RCE, authentication bypass, data exposure) will be prioritized.

## Scope

**In scope:**
- Remote code execution
- Authentication bypass
- Privilege escalation (Adventurer → Guild Master)
- Path traversal in file upload or avatar routes
- SQL injection
- Stored XSS in user-visible pages
- Sensitive data exposure via API or route enumeration

**Out of scope:**
- Vulnerabilities requiring physical access to the host
- Vulnerabilities in dependencies (report those upstream; they are tracked by Trivy in CI)
- Self-XSS (attacks requiring the victim to execute the payload themselves)
- Theoretical attacks with no practical exploit path

## Dependency vulnerabilities

The CI pipeline runs [Trivy](https://trivy.dev) on every build, scanning for CRITICAL and HIGH CVEs in OS packages and Python libraries. Results are published to the [Security tab](https://github.com/JohnFawkes/quest-log/security/code-scanning). Python dependency updates are automated via [Renovate](renovate.json).
