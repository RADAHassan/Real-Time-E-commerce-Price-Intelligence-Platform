"""
Polls the NiFi API until the instance is ready to accept requests.
Used by the deployment script and Makefile targets before running deploy.py.

Usage:
  python nifi/scripts/wait_for_nifi.py [--url http://localhost:8080] [--timeout 180]
"""

import argparse
import sys
import time

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def wait_for_nifi(url: str, timeout: int = 180, interval: int = 5) -> bool:
    health_url = f"{url.rstrip('/')}/nifi-api/system-diagnostics"
    deadline = time.time() + timeout
    attempt = 0

    print(f"Waiting for NiFi at {url} (timeout={timeout}s)…")
    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(health_url, timeout=5, verify=False)
            if resp.status_code in (200, 401):
                # 401 means NiFi is up but requires auth — that's fine
                print(f"✓ NiFi ready after {attempt} attempt(s)")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except requests.exceptions.Timeout:
            pass

        remaining = int(deadline - time.time())
        print(f"  attempt {attempt} — not ready yet ({remaining}s left)…")
        time.sleep(interval)

    print(f"✗ NiFi did not become ready within {timeout}s", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(description="Wait for NiFi to be ready")
    parser.add_argument("--url", default="http://localhost:8080", help="NiFi base URL")
    parser.add_argument("--timeout", type=int, default=180, help="Max wait in seconds")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    args = parser.parse_args()

    ok = wait_for_nifi(args.url, timeout=args.timeout, interval=args.interval)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
