# Corporate Information Security Guidelines

These guidelines establish standard operational security protocols, data protection policies, and incident management standards across all corporate systems.

## Password and Authentication Security
All workforce members must adhere to strict credential safety:
- Passwords must be a minimum of 16 characters in length and include an uppercase letter, lowercase letter, number, and special character.
- Passwords must not match any of the previous 10 passwords used.
- Multi-Factor Authentication (MFA) is strictly mandatory on all accounts and single sign-on (SSO) portals using FIDO2 hardware security keys or authenticator apps (TOTP). SMS-based 2FA is prohibited.
- Workstation screens and cloud console sessions automatically lock after 15 minutes of inactivity. After 5 consecutive failed login attempts, accounts are locked for 30 minutes unless unlocked by IT Support.

## Device and Endpoint Protection
All company-managed endpoints (macOS, Windows, Linux) must comply with device governance:
- Full Disk Encryption (FileVault on macOS, BitLocker with 256-bit AES on Windows) must remain permanently enabled.
- Corporate Endpoint Detection and Response (EDR) software must remain active 24/7. Disabling security agents is a terminable infraction.
- Removable media such as unencrypted USB flash drives and external hard drives are blocked by endpoint policy.
- Lost, stolen, or compromised hardware must be reported to SecOps (security-ops@company.internal) within 1 hour of discovery.

## Remote Work and Wi-Fi Standards
When working remotely or while traveling:
- All connections to company internal resources, production clusters, and staging environments must traverse the corporate Zero-Trust Network Access (ZTNA) or corporate WireGuard VPN tunnel.
- Using untrusted public Wi-Fi networks (hotels, airports, cafes) without active VPN is strictly prohibited.
- Physical privacy filters are mandatory on laptop displays when working in public spaces or transit.
- Employees must never leave unlocked devices unattended in shared workspaces or hotel rooms.

## Data Classification and Retention
Corporate data is classified into 4 tiers: Public, Internal, Confidential, and Restricted.
- Confidential and Restricted data must be encrypted in transit using TLS 1.3 and at rest with AES-256-GCM.
- Customer personal data (PII) and financial records must never be exported to local drives or unapproved third-party cloud tools.
- Transactional and audit logs must be retained for 7 years to satisfy regulatory compliance, after which they are irreversibly destroyed using automated cryptographic erasure.

## Incident Response and Phishing Reporting
Employees represent the first line of defense against cyber threats:
- Any suspicious email or communication must be reported within 30 minutes using the "Report Phishing" button in the corporate email client or by emailing abuse@company.internal.
- If malware, ransomware, or unauthorized data access is suspected, immediately disconnect the device from the network (unplug ethernet, disable Wi-Fi) and call the 24/7 Security Hotline (+1-800-555-0199).
- Severity-1 security incidents require an incident response commander page within 15 minutes and hourly status updates to the executive response committee.
