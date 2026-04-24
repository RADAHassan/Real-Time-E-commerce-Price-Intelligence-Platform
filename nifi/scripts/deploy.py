"""
Deploys the price intelligence streaming flow to NiFi via the REST API.

Flow created:
  ListenHTTP (port 9191)
      ↓ success
  JoltTransformJSON  (normalise + add pipeline=nifi-streaming)
      ↓ success
  InvokeHTTP  (POST http://sink:8087/ingest)
      ↓ Response.2xx  → auto-terminate
      ↓ Failure/Retry → LogAttribute
      ↓ No Retry      → LogAttribute

After creation the flow is exported as an XML template to
nifi/templates/price_intelligence_flow.xml for version control.

Usage:
  python nifi/scripts/deploy.py [options]

Options:
  --nifi-url   Base NiFi URL           (default: http://localhost:8080)
  --username   NiFi username           (default: admin)
  --password   NiFi password           (default: adminpassword123)
  --sink-url   Bigtable sink URL       (default: http://sink:8087/ingest)
  --listen-port  ListenHTTP port       (default: 9191)
  --start      Start the flow after creation
  --dry-run    Print actions without calling NiFi API
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
JOLT_SPEC = (BASE_DIR / "jolt_transform.json").read_text()
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

# NiFi processor full class names (NiFi 1.25.0)
_PROC = {
    "ListenHTTP":        "org.apache.nifi.processors.standard.ListenHTTP",
    "JoltTransform":     "org.apache.nifi.processors.standard.JoltTransformJSON",
    "InvokeHTTP":        "org.apache.nifi.processors.standard.InvokeHTTP",
    "LogAttribute":      "org.apache.nifi.processors.standard.LogAttribute",
    "UpdateAttribute":   "org.apache.nifi.processors.attributes.UpdateAttribute",
}

# Processor layout positions (x, y) on the NiFi canvas
_POSITIONS = {
    "ListenHTTP":   (  0,   0),
    "JoltTransform": (  0, 200),
    "InvokeHTTP":   (  0, 400),
    "LogAttribute": (400, 400),
}


# ---------------------------------------------------------------------------
# NiFi REST client
# ---------------------------------------------------------------------------

class NiFiClient:
    def __init__(self, base_url: str, username: str, password: str, dry_run: bool = False):
        self.base = base_url.rstrip("/")
        self.api = f"{self.base}/nifi-api"
        self.dry_run = dry_run
        self._s = requests.Session()
        self._s.verify = False
        if not dry_run:
            self._authenticate(username, password)

    def _authenticate(self, username: str, password: str):
        try:
            resp = self._s.post(
                f"{self.api}/access/token",
                data={"username": username, "password": password},
                timeout=10,
            )
            if resp.status_code == 201:
                self._s.headers["Authorization"] = f"Bearer {resp.text.strip()}"
                logger.info("Authenticated with NiFi")
            else:
                logger.warning("Auth returned %s — continuing without token", resp.status_code)
        except Exception as exc:
            logger.warning("Auth failed: %s — continuing unauthenticated", exc)

    def get(self, path: str) -> dict:
        resp = self._s.get(f"{self.api}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: dict) -> dict:
        if self.dry_run:
            logger.info("[DRY-RUN] POST %s %s", path, json.dumps(body)[:120])
            return {"id": f"dry-run-{path.replace('/', '-')}"}
        resp = self._s.post(f"{self.api}{path}", json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, body: dict) -> dict:
        if self.dry_run:
            logger.info("[DRY-RUN] PUT %s", path)
            return body
        resp = self._s.put(f"{self.api}{path}", json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, path: str) -> str:
        resp = self._s.get(f"{self.api}{path}", timeout=15)
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def root_id(self) -> str:
        return self.get("/process-groups/root")["id"]

    def flow_exists(self, root_id: str, pg_name: str) -> bool:
        data = self.get(f"/process-groups/{root_id}/process-groups")
        return any(
            pg["component"]["name"] == pg_name
            for pg in data.get("processGroups", [])
        )

    def create_process_group(self, parent_id: str, name: str) -> str:
        data = self.post(f"/process-groups/{parent_id}/process-groups", {
            "revision": {"version": 0},
            "component": {"name": name, "position": {"x": 0.0, "y": 0.0}},
        })
        pg_id = data.get("id", "dry-run")
        logger.info("Process group '%s' created (id=%s)", name, pg_id)
        return pg_id

    def add_processor(self, group_id: str, key: str, name: str,
                      properties: dict, auto_terminate: list[str],
                      scheduling: dict | None = None) -> str:
        x, y = _POSITIONS.get(key, (0, 0))
        body: dict = {
            "revision": {"version": 0},
            "component": {
                "type": _PROC[key],
                "name": name,
                "position": {"x": float(x), "y": float(y)},
                "config": {
                    "properties": properties,
                    "autoTerminatedRelationships": auto_terminate,
                    "schedulingPeriod": "0 sec",
                    "schedulingStrategy": "TIMER_DRIVEN",
                    "penaltyDuration": "30 sec",
                    "yieldDuration": "1 sec",
                    "bulletinLevel": "WARN",
                    "runDurationMillis": 0,
                    "concurrentlySchedulableTaskCount": 1,
                },
            },
        }
        if scheduling:
            body["component"]["config"].update(scheduling)
        data = self.post(f"/process-groups/{group_id}/processors", body)
        pid = data.get("id", "dry-run")
        logger.info("  Processor '%s' created (id=%s)", name, pid)
        return pid

    def connect(self, group_id: str, src: str, dst: str, relationships: list[str]) -> str:
        data = self.post(f"/process-groups/{group_id}/connections", {
            "revision": {"version": 0},
            "component": {
                "source": {"id": src, "type": "PROCESSOR", "groupId": group_id},
                "destination": {"id": dst, "type": "PROCESSOR", "groupId": group_id},
                "selectedRelationships": relationships,
                "backPressureObjectThreshold": 10000,
                "backPressureDataSizeThreshold": "1 GB",
                "flowFileExpiration": "0 sec",
            },
        })
        cid = data.get("id", "dry-run")
        logger.info("  Connection %s → %s (%s)", src[:8], dst[:8], ", ".join(relationships))
        return cid

    def start_group(self, group_id: str):
        self.put(f"/flow/process-groups/{group_id}", {"id": group_id, "state": "RUNNING"})
        logger.info("Flow started (group_id=%s)", group_id)

    def export_template_xml(self, group_id: str) -> str:
        if self.dry_run:
            return "<!-- dry-run: no XML generated -->"
        return self.get_text(f"/process-groups/{group_id}/download")


# ---------------------------------------------------------------------------
# Flow creation
# ---------------------------------------------------------------------------

def create_flow(client: NiFiClient, sink_url: str, listen_port: int, start: bool):
    root = client.root_id()
    pg_name = "Price Intelligence"

    if client.flow_exists(root, pg_name):
        logger.warning("Process group '%s' already exists — skipping creation.", pg_name)
        return

    pg_id = client.create_process_group(root, pg_name)

    # 1. ListenHTTP — receives JSON POST from Scrapy NiFiHttpPipeline
    listen_id = client.add_processor(
        pg_id, "ListenHTTP", "Receive Price Data",
        properties={
            "Listening Port": str(listen_port),
            "Base Path": "contentListener",
            "Max Data to Receive per Second": "",
            "Max Unconfirmed FlowFile Size": "25 MB",
            "HTTP Context Map": "",
        },
        auto_terminate=[],
    )

    # 2. JoltTransformJSON — normalise fields, add pipeline metadata
    jolt_id = client.add_processor(
        pg_id, "JoltTransform", "Normalise Price Schema",
        properties={
            "jolt-transform": "jolt-transform-chain",
            "jolt-spec": JOLT_SPEC,
            "jolt-custom-class": "",
            "Transform Cache Size": "1",
        },
        auto_terminate=["failure"],
    )

    # 3. InvokeHTTP — POST to Bigtable sink service
    invoke_id = client.add_processor(
        pg_id, "InvokeHTTP", "Write to Bigtable Sink",
        properties={
            "HTTP Method": "POST",
            "Remote URL": sink_url,
            "Content-Type": "application/json",
            "Connection Timeout": "5 secs",
            "Read Timeout": "15 secs",
            "Attributes to Send": "",
            "Put Response Body In Attribute": "",
            "Add Response Headers to Request": "false",
            "Follow Redirects": "True",
            "Disable Peer Verification": "false",
        },
        # Original = original FlowFile (keep), Response = HTTP response body
        auto_terminate=["Original", "Response"],
    )

    # 4. LogAttribute — log failures from InvokeHTTP
    log_id = client.add_processor(
        pg_id, "LogAttribute", "Log Failed Writes",
        properties={
            "Log Level": "warn",
            "Attributes to Log": ".*",
            "Log Payload": "true",
            "Log FlowFile Properties": "true",
        },
        auto_terminate=["success"],
    )

    # Connections
    client.connect(pg_id, listen_id,  jolt_id,   ["success"])
    client.connect(pg_id, jolt_id,    invoke_id,  ["success"])
    client.connect(pg_id, invoke_id,  log_id,     ["Failure", "No Retry", "Retry"])

    if start:
        time.sleep(1)   # brief pause so NiFi registers all processors
        client.start_group(pg_id)

    # Export as XML template for version control
    xml = client.export_template_xml(pg_id)
    out_path = TEMPLATES_DIR / "price_intelligence_flow.xml"
    out_path.write_text(xml)
    logger.info("Template exported → %s", out_path)

    return pg_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Deploy price intelligence NiFi flow")
    parser.add_argument("--nifi-url",    default="http://localhost:8080")
    parser.add_argument("--username",    default="admin")
    parser.add_argument("--password",    default="adminpassword123")
    parser.add_argument("--sink-url",    default="http://sink:8087/ingest")
    parser.add_argument("--listen-port", type=int, default=9191)
    parser.add_argument("--start",       action="store_true", help="Start flow after creation")
    parser.add_argument("--dry-run",     action="store_true", help="Print actions without API calls")
    args = parser.parse_args()

    client = NiFiClient(args.nifi_url, args.username, args.password, dry_run=args.dry_run)
    create_flow(client, sink_url=args.sink_url, listen_port=args.listen_port, start=args.start)
    print("✓ NiFi flow deployed")


if __name__ == "__main__":
    main()
