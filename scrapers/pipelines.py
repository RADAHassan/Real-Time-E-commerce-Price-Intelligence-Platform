"""
Four-stage item pipeline:

  ValidationPipeline  (100) — drops items with missing/invalid fields
  JsonOutputPipeline  (200) — appends each item as a JSON line to a .jsonl file
  BigtablePipeline    (250) — writes item to Bigtable emulator / production
                              (no-op until BIGTABLE_PUSH_ENABLED=true in .env)
  NiFiHttpPipeline    (300) — POSTs the item to NiFi's ListenHTTP endpoint
                              (no-op until NIFI_PUSH_ENABLED=true in .env)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

_REQUIRED = ("product_id", "title", "price", "currency", "source", "url", "scraped_at")


# ---------------------------------------------------------------------------
# 1. Validation
# ---------------------------------------------------------------------------


class ValidationPipeline:
    def process_item(self, item, spider):
        for field in _REQUIRED:
            if item.get(field) is None or item.get(field) == "":
                raise DropItem(f"[{spider.name}] Missing '{field}': {dict(item)}")

        price = item.get("price")
        if not isinstance(price, (int, float)):
            raise DropItem(f"[{spider.name}] price must be numeric, got {type(price)}: {price}")
        if price < 0:
            raise DropItem(f"[{spider.name}] Negative price {price} at {item.get('url')}")

        return item


# ---------------------------------------------------------------------------
# 2. JSON line output
# ---------------------------------------------------------------------------


class JsonOutputPipeline:
    """Writes one JSON object per line to data/<spider_name>/<spider_name>_<ts>.jsonl"""

    def __init__(self):
        self._handles: dict[str, object] = {}

    def open_spider(self, spider):
        output_dir = Path("data") / spider.name
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = output_dir / f"{spider.name}_{ts}.jsonl"
        self._handles[spider.name] = path.open("w", encoding="utf-8")
        logger.info("[%s] Writing output → %s", spider.name, path)

    def close_spider(self, spider):
        handle = self._handles.pop(spider.name, None)
        if handle:
            handle.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False, default=str) + "\n"
        self._handles[spider.name].write(line)
        return item


# ---------------------------------------------------------------------------
# 3. Kafka push (activated by KAFKA_PUSH_ENABLED=true in .env)
# ---------------------------------------------------------------------------


class KafkaPipeline:
    """Publishes each validated item to the 'price.raw' Kafka topic.

    Disabled by default — set KAFKA_PUSH_ENABLED=true and
    KAFKA_BOOTSTRAP_SERVERS=localhost:9092 in .env to activate.
    Start Kafka: docker compose --profile kafka up -d
    """

    TOPIC = "price.raw"

    def __init__(self, bootstrap_servers: str, push_enabled: bool):
        self.push_enabled = push_enabled
        self._producer = None
        if push_enabled:
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    acks=1,
                    linger_ms=10,
                )
                logger.info("[Kafka] Producer ready → %s / %s", bootstrap_servers, self.TOPIC)
            except Exception as exc:
                logger.warning("[Kafka] Producer init failed: %s", exc)
                self._producer = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            bootstrap_servers=crawler.settings.get(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            push_enabled=crawler.settings.getbool("KAFKA_PUSH_ENABLED", False),
        )

    def process_item(self, item, spider):
        if not self.push_enabled or self._producer is None:
            return item
        try:
            key = item.get("product_id") or item.get("title", "")
            self._producer.send(self.TOPIC, key=key, value=dict(item))
            logger.debug("[Kafka] sent: %s", key)
        except Exception as exc:
            logger.warning("[Kafka] send failed for %s: %s", item.get("url"), exc)
        return item

    def close_spider(self, spider):
        if self._producer:
            self._producer.flush()
            self._producer.close()


# ---------------------------------------------------------------------------
# 4. NiFi HTTP push (activated in Phase 3)
# ---------------------------------------------------------------------------


class NiFiHttpPipeline:
    """POSTs each item as JSON to NiFi's ListenHTTP processor.

    Disabled by default — set NIFI_PUSH_ENABLED=true in .env to activate.
    Failures are logged as warnings so a NiFi outage never kills the crawl.
    """

    def __init__(self, nifi_url: str, push_enabled: bool):
        self.nifi_url = nifi_url
        self.push_enabled = push_enabled
        self._session = requests.Session()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            nifi_url=crawler.settings.get("NIFI_INGEST_URL", ""),
            push_enabled=crawler.settings.getbool("NIFI_PUSH_ENABLED", False),
        )

    def process_item(self, item, spider):
        if not self.push_enabled or not self.nifi_url:
            return item

        try:
            resp = self._session.post(
                self.nifi_url,
                data=json.dumps(dict(item), ensure_ascii=False, default=str),
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            resp.raise_for_status()
            logger.debug("[%s] NiFi push OK: %s", spider.name, item.get("url"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] NiFi push failed for %s: %s", spider.name, item.get("url"), exc)

        return item

    def close_spider(self, spider):
        self._session.close()


# ---------------------------------------------------------------------------
# 3. Bigtable (activated in Phase 2 — set BIGTABLE_PUSH_ENABLED=true)
# ---------------------------------------------------------------------------


class BigtablePipeline:
    """Writes each validated item to the Bigtable 'prices' table.

    Disabled by default — set BIGTABLE_PUSH_ENABLED=true in .env.
    Requires the emulator to be running (`make up`) or a real Bigtable instance.
    Failures are logged as warnings so a Bigtable outage never kills the crawl.
    """

    def __init__(self, project_id: str, instance_id: str, push_enabled: bool):
        self.push_enabled = push_enabled
        self._client = None
        if push_enabled:
            from bigtable.client import BigtableClient

            self._client = BigtableClient(project_id, instance_id)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            project_id=crawler.settings.get("GCP_PROJECT_ID", ""),
            instance_id=crawler.settings.get("BIGTABLE_INSTANCE_ID", "price-intelligence"),
            push_enabled=crawler.settings.getbool("BIGTABLE_PUSH_ENABLED", False),
        )

    def process_item(self, item, spider):
        if not self.push_enabled or self._client is None:
            return item
        try:
            row_key = self._client.write_price_item(dict(item))
            logger.debug("[%s] Bigtable write OK: %s", spider.name, row_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] Bigtable write failed for %s: %s", spider.name, item.get("url"), exc)
        return item
