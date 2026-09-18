"""Save Qobuz web-player authentication for streamrip's existing token mode.

The browser-login approach is described in nathom/streamrip PR #955.
No password, token, browser profile, or network trace is printed or exported.
"""
import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

import tomlkit

PROJECT = Path(__file__).resolve().parent
CONFIG = PROJECT / "streamrip.toml"
LOGIN_URL = "https://play.qobuz.com/login"


def extract_credentials(url, status, payload, post_data=None):
    """Accept credentials only from Qobuz's successful login response."""
    endpoint = urlsplit(url)
    if (endpoint.scheme != "https" or endpoint.hostname != "www.qobuz.com"
            or endpoint.path.rstrip("/") != "/api.json/0.2/user/login"
            or status != 200 or not isinstance(payload, dict)):
        return None
    # Match the partner-token response used by upstream's browser login fix.
    if post_data:
        try:
            request_data = json.loads(post_data)
        except (ValueError, TypeError):
            request_data = {key: values[0] for key, values in parse_qs(post_data).items()}
        if not isinstance(request_data, dict) or request_data.get("extra") != "partner":
            return None
    user = payload.get("user")
    if not isinstance(user, dict):
        return None
    user_id = user.get("id")
    token = payload.get("user_auth_token")
    if (isinstance(user_id, bool) or not isinstance(user_id, (int, str))
            or not str(user_id).isdigit() or int(user_id) <= 0
            or not isinstance(token, str) or not token.strip()):
        return None
    return str(user_id), token.strip()


def save_credentials(config_path, user_id, token):
    if not user_id.isdigit() or int(user_id) <= 0 or not token.strip():
        raise ValueError("A numeric Qobuz user ID and a non-empty token are required.")
    # Read at save time to preserve other settings edited during browser login.
    config = tomlkit.parse(config_path.read_text(encoding="utf-8-sig"))
    qobuz = config["qobuz"]
    qobuz["use_auth_token"] = True
    qobuz["email_or_userid"] = user_id
    qobuz["password_or_token"] = token.strip()
    private_dir = config_path.parent / ".runtime" / "qobuz"
    private_dir.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=private_dir,
                                         suffix=".toml", delete=False) as temp:
            temp_path = Path(temp.name)
            temp.write(tomlkit.dumps(config))
        os.replace(temp_path, config_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def browser_credentials(timeout=600):
    from playwright.sync_api import sync_playwright

    captured = []

    def on_response(response):
        endpoint = urlsplit(response.url)
        if (endpoint.scheme != "https" or endpoint.hostname != "www.qobuz.com"
                or endpoint.path.rstrip("/") != "/api.json/0.2/user/login"
                or response.status != 200):
            return
        try:
            credentials = extract_credentials(response.url, response.status, response.json(), response.request.post_data)
        except Exception:
            return
        if credentials is not None:
            captured[:] = [credentials]

    with sync_playwright() as playwright:
        browser = None
        for channel in ("msedge", "chrome"):
            try:
                browser = playwright.chromium.launch(channel=channel, headless=False)
                break
            except Exception:
                continue
        if browser is None:
            raise RuntimeError("Edge or Chrome could not be opened. Try --manual instead.")
        try:
            context = browser.new_context()
            context.on("response", on_response)
            page = context.new_page()
            print("Sign in to Qobuz in the new browser window. It closes after login is captured.")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            deadline = time.monotonic() + timeout
            while not captured and time.monotonic() < deadline:
                if not browser.is_connected() or page.is_closed():
                    break
                page.wait_for_timeout(250)
            if not captured:
                raise RuntimeError("No successful Qobuz login was captured. Retry or use --manual.")
            return captured[0]
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="Log in to Qobuz for this project's streamrip configuration.")
    parser.add_argument("--manual", action="store_true", help="Enter your numeric user ID and web-player token manually.")
    args = parser.parse_args()
    if not CONFIG.is_file():
        print("streamrip.toml is missing. Restore the project configuration first.")
        return 1
    try:
        if args.manual:
            user_id = input("Qobuz numeric user ID: ").strip()
            token = getpass("Qobuz user_auth_token (hidden): ").strip()
        else:
            user_id, token = browser_credentials()
        save_credentials(CONFIG, user_id, token)
    except KeyboardInterrupt:
        print("Login cancelled. Configuration was not changed.")
        return 1
    except Exception as error:
        # Raw browser/network exceptions can contain authentication URLs.
        if type(error) in (RuntimeError, ValueError):
            print(str(error))
        else:
            print(f"Login could not finish ({type(error).__name__}). Retry or use --manual; see SETUP.md.")
        return 1
    print("Qobuz user ID and token saved to streamrip.toml. Your password was not saved.")
    print("Restart your streamrip command or the Hires Bot app to use the new login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
