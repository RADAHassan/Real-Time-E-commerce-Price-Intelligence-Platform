"""
Kafka Producer — Price Intelligence Platform
Reads JSONL demo/scraped data and publishes each product to the
'price.raw' Kafka topic, simulating a real-time scraping stream.

Usage:
    python kafka/producer.py                    # stream all demo data
    python kafka/producer.py --delay 0.05       # throttle to 20 items/s
    python kafka/producer.py --source jumia_ma  # single source only
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
TOPIC = "price.raw"
BROKER = "localhost:9092"


def get_records(source_filter: str | None = None):
    data_dir = ROOT / "data"
    for f in data_dir.rglob("*.jsonl"):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if source_filter and rec.get("source") != source_filter:
                        continue
                    yield rec
                except json.JSONDecodeError:
                    continue


def run(delay: float = 0.0, source_filter: str | None = None,
        bootstrap: str = BROKER):
    try:
        from kafka import KafkaProducer
        from kafka.errors import NoBrokersAvailable
    except ImportError:
        print("kafka-python not installed. Run: pip install kafka-python")
        return

    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
            linger_ms=5,
        )
    except NoBrokersAvailable:
        print(f"[producer] No Kafka broker at {bootstrap}.")
        print("  Start Kafka: docker compose --profile kafka up -d")
        print("  Then rerun:  python kafka/producer.py")
        return

    sent = 0
    errors = 0
    print(f"[producer] Publishing to topic '{TOPIC}' on {bootstrap}")
    if source_filter:
        print(f"[producer] Filter: source={source_filter}")

    try:
        for rec in get_records(source_filter):
            key = rec.get("product_id") or rec.get("title", "")
            try:
                producer.send(TOPIC, key=key, value=rec)
                sent += 1
                if sent % 1000 == 0:
                    producer.flush()
                    print(f"[producer] {sent:,} messages sent …")
                if delay:
                    time.sleep(delay)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"[producer] send error: {e}")
    except KeyboardInterrupt:
        print("\n[producer] Interrupted.")
    finally:
        producer.flush()
        producer.close()
        print(f"[producer] Done — {sent:,} sent, {errors} errors.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay",    type=float, default=0.0,
                    help="Seconds between messages (0 = max speed)")
    ap.add_argument("--source",   default=None,
                    help="Filter by source (e.g. jumia_ma)")
    ap.add_argument("--broker",   default=BROKER,
                    help=f"Kafka broker address (default: {BROKER})")
    args = ap.parse_args()
    run(delay=args.delay, source_filter=args.source, bootstrap=args.broker)
