"""
CLI de debug pour interagir avec le Bigtable local (émulateur).

Usage (depuis la racine du repo, avec le venv activé) :
  python -m bigtable.cli init-schema
  python -m bigtable.cli write-test
  python -m bigtable.cli read-product <product_id>
  python -m bigtable.cli scan-all [--limit 20]
  python -m bigtable.cli drop-schema   # reset pour dev

Variables d'environnement requises (.env) :
  GCP_PROJECT_ID      ex: my-gcp-project
  BIGTABLE_INSTANCE_ID ex: price-intelligence
  BIGTABLE_EMULATOR_HOST=localhost:8086   ← pointe vers le conteneur Docker
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _get_config() -> tuple[str, str]:
    project_id = os.getenv("GCP_PROJECT_ID", "")
    instance_id = os.getenv("BIGTABLE_INSTANCE_ID", "price-intelligence")
    if not project_id:
        logger.error("GCP_PROJECT_ID is not set in .env")
        sys.exit(1)
    return project_id, instance_id


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_init_schema(args):
    """Créer la table 'prices' et ses column families."""
    from bigtable.schema import create_schema

    project_id, instance_id = _get_config()
    create_schema(project_id, instance_id)
    print(f"✓ Schema initialised — project={project_id} instance={instance_id}")


def cmd_drop_schema(args):
    """Supprimer la table 'prices' (reset dev)."""
    from bigtable.schema import drop_schema

    project_id, instance_id = _get_config()
    confirm = input("Supprimer la table 'prices' ? [oui/NON] : ").strip().lower()
    if confirm != "oui":
        print("Annulé.")
        return
    drop_schema(project_id, instance_id)
    print("✓ Table supprimée.")


def cmd_write_test(args):
    """Écrire un enregistrement de test pour valider la connexion."""
    from bigtable.client import BigtableClient

    project_id, instance_id = _get_config()
    client = BigtableClient(project_id, instance_id)

    fake_url = "https://www.jumia.ma/hp-pavilion-15-test.html"
    test_item = {
        "product_id": hashlib.md5(fake_url.encode()).hexdigest(),
        "source": "jumia.ma",
        "url": fake_url,
        "title": "HP Pavilion 15 [TEST]",
        "price": 4299.0,
        "currency": "MAD",
        "rating": 4.0,
        "availability": "In Stock",
        "category": "Ordinateurs Portables",
        "image_url": "https://img.jumia.ma/test.jpg",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    row_key = client.write_price_item(test_item)
    print(f"✓ Test record written")
    print(f"  row_key  : {row_key}")
    print(f"  product_id: {test_item['product_id']}")
    print(f"\n  Vérifier avec : python -m bigtable.cli read-product {test_item['product_id']}")


def cmd_read_product(args):
    """Afficher la dernière observation de prix pour un product_id."""
    from bigtable.client import BigtableClient

    project_id, instance_id = _get_config()
    client = BigtableClient(project_id, instance_id)

    if args.history:
        rows = client.scan_product_history(args.product_id, limit=args.limit)
        print(f"Historique ({len(rows)} observations) pour {args.product_id}:\n")
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, indent=2))
    else:
        row = client.get_latest_price(args.product_id)
        if row is None:
            print(f"Aucun enregistrement pour product_id={args.product_id}")
        else:
            print(json.dumps(row, ensure_ascii=False, indent=2))


def cmd_scan_all(args):
    """Scanner toute la table (debug — limité à --limit lignes)."""
    from bigtable.client import BigtableClient

    project_id, instance_id = _get_config()
    client = BigtableClient(project_id, instance_id)

    rows = client.scan_all(limit=args.limit)
    print(f"{len(rows)} ligne(s) trouvée(s) dans la table 'prices':\n")
    for row in rows:
        price = row.get("price", "?")
        currency = row.get("currency", "")
        title = row.get("title", "?")[:60]
        source = row.get("source", "?")
        print(f"  [{source}] {title} — {price} {currency}")
        print(f"    row_key: {row['row_key']}")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bigtable.cli",
        description="Debug CLI pour le Bigtable local (émulateur).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-schema", help="Créer la table et les column families")
    sub.add_parser("drop-schema", help="Supprimer la table (reset dev)")
    sub.add_parser("write-test", help="Écrire un enregistrement de test")

    p_read = sub.add_parser("read-product", help="Lire les prix d'un produit")
    p_read.add_argument("product_id", help="MD5 du product_id")
    p_read.add_argument("--history", action="store_true", help="Afficher tout l'historique")
    p_read.add_argument("--limit", type=int, default=50, help="Nombre max de lignes (historique)")

    p_scan = sub.add_parser("scan-all", help="Scanner toute la table")
    p_scan.add_argument("--limit", type=int, default=100, help="Nombre max de lignes")

    return parser


COMMANDS = {
    "init-schema": cmd_init_schema,
    "drop-schema": cmd_drop_schema,
    "write-test": cmd_write_test,
    "read-product": cmd_read_product,
    "scan-all": cmd_scan_all,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
