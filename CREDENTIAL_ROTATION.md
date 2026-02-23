Credential Rotation & Security Notice
==================================

The repository previously contained a Google OAuth client secret file that was removed from the git history and the cleaned branch was force-pushed.

Immediate actions you should take now:

- Rotate the Google OAuth client (create new credentials) and update any running services with the new secret.
- Revoke the old client in the Google Cloud Console to prevent misuse.
- Audit any systems that may have used the leaked credential and rotate related keys if needed.

Preventive actions:

- Keep any JSON secrets or credentials out of the repository. Store them in environment variables or a secrets manager.
- Add patterns like `client_secret_*.json` to `.gitignore` (already added).
- Use short-lived credentials and rotate regularly.
- Consider enabling organization-level secret scanning alerts and 2FA for repository access.

If you want, I can also prepare step-by-step rotation commands for Google Cloud or open a PR you can review.
