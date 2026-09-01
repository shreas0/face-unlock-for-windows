# Security Policy

## Data handling and privacy

- Biometric enrollment artifacts and unlock credentials are stored locally on the machine running FaceUnlock.
- Stored credentials are protected using Windows DPAPI encryption.
- The project does not include telemetry collection.
- Biometric material is not transmitted to external services by default.

## Reporting a vulnerability

Please report security issues by opening a GitHub Issue in this repository and clearly labeling it as a security report.

Include:
- Affected version or commit
- Reproduction steps
- Expected vs actual behavior
- Impact assessment

If you prefer coordinated disclosure details later, maintainers can update this policy with a dedicated private reporting channel.
