"""
Kafka Consumer — Price Intelligence Platform
Consumes from the 'price.raw' topic and writes each record to
data/kafka_stream/stream.jsonl so the dashboard picks it up live.

Usage:
    python kafka/consumer.py                    # run forever
    python kafka/consumer.py --max 5000         # stop after 5000 messages
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT   = Path(__file__).parent.parent
TOPIC  = "price.raw"
BROKER = "localhost:9092"
GROUP  = "price-intelligence-dashboard"
OUT    = ROOT / "data" / "kafka_stream"

_running = True

def _handle_sigint(sig, frame):
    global _running
    print("\n[consumer] Shutting down …")
    _running = False

signal.signal(signal.SIGINT, _handle_sigint)


def run(max_messages: int = 0, bootstrap: str = BROKER):
    try:
        from kafka import KafkaConsumer
        from kafka.errors import NoBrokersAvailable
    except ImportError:
        print("kafka-python not installed. Run: pip install kafka-python")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    out_file = OUT / "stream.jsonl"

    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=bootstrap,
            group_id=GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            consumer_timeout_ms=5000,
        )
    except NoBrokersAvailable:
        print(f"[consumer] No Kafka broker at {bootstrap}.")
        print("  Start Kafka: docker compose --profile kafka up -d")
        return

    print(f"[consumer] Listening on topic '{TOPIC}' (broker: {bootstrap})")
    print(f"[consumer] Writing to {out_file}")

    count = 0
    with open(out_file, "a", encoding="utf-8") as fh:
        for msg in consumer:
            if not _running:
                break
            rec = msg.value
            # Stamp with consumption time if scraped_at missing
            rec.setdefault("scraped_at",
                           datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1

            if count % 500 == 0:
                fh.flush()
                print(f"[consumer] {count:,} messages consumed …")

            if max_messages and count >= max_messages:
                print(f"[consumer] Reached limit of {max_messages}.")
                break

    consumer.close()
    print(f"[consumer] Done — {count:,} records written to {out_file}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max",    type=int, default=0,
                    help="Stop after N messages (0 = unlimited)")
    ap.add_argument("--broker", default=BROKER,
                    help=f"Kafka broker (default: {BROKER})")
    args = ap.parse_args()
    run(max_messages=args.max, bootstrap=args.broker)
