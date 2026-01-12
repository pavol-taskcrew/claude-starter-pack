"""OAuth 2.0 authentication for Google Docs CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import CLIENT_SECRETS_FILE, SCOPES, TOKEN_FILE, ensure_dirs


class AuthError(Exception):
    """Authentication error."""

    pass


def get_credentials() -> Optional[Credentials]:
    """Get valid credentials, refreshing if necessary."""
    ensure_dirs()

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
        except Exception:
            creds = None

    return creds


def login() -> Credentials:
    """Perform OAuth 2.0 login flow."""
    ensure_dirs()

    if not CLIENT_SECRETS_FILE.exists():
        raise AuthError(
            f"credentials.json not found at {CLIENT_SECRETS_FILE}\n"
            "Please download OAuth credentials from Google Cloud Console:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create/select a project and enable Google Docs & Drive APIs\n"
            "3. Create OAuth 2.0 credentials (Desktop app)\n"
            "4. Download and save as: credentials.json in credentials/"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)

    try:
        creds = flow.run_local_server(port=0)
    except Exception as e:
        raise AuthError(f"Failed to complete OAuth flow: {e}")

    _save_credentials(creds)
    return creds


def logout() -> bool:
    """Remove stored credentials."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        return True
    return False


def is_authenticated() -> bool:
    """Check if user is authenticated with valid credentials."""
    creds = get_credentials()
    return creds is not None and creds.valid


def require_auth() -> Credentials:
    """Get credentials or raise error if not authenticated."""
    creds = get_credentials()
    if not creds or not creds.valid:
        raise AuthError(
            "Not authenticated. Please run: gdocs auth login"
        )
    return creds


def _save_credentials(creds: Credentials) -> None:
    """Save credentials to token file."""
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
