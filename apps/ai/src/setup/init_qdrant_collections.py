"""
Creates the 3 MVP Qdrant collections for the Pulse pivot.
Safe to re-run — skips if collection already exists.

Run:
  cd apps/ai && uv run python src/setup/init_qdrant_collections.py
"""
import os, sys, requests

QDRANT = os.getenv("QDRANT_URL", "http://localhost:6333")
DIM    = 768    # nomic-embed-text dimension

COLLECTIONS = [
    {
        "name":        "pulse_memory",
        "description": "Daily business state snapshots "
                       "(MRR, burn, runway). PulseAgent reads/writes.",
        "payload_indexes": [
            {"field": "tenant_id",     "schema": "keyword"},
            {"field": "snapshot_date", "schema": "keyword"},
            {"field": "mrr_cents",     "schema": "integer"},
        ],
    },
    {
        "name":        "anomaly_memory",
        "description": "Episodic anomaly history — the competitive moat. "
                       "AnomalyAgent reads before explaining every spike.",
        "payload_indexes": [
            {"field": "tenant_id",   "schema": "keyword"},
            {"field": "metric_name", "schema": "keyword"},
            {"field": "action",      "schema": "keyword"},
        ],
    },
    {
        "name":        "investor_memory",
        "description": "Past investor update context + wins/blockers. "
                       "InvestorAgent reads to reference prior periods.",
        "payload_indexes": [
            {"field": "tenant_id",    "schema": "keyword"},
            {"field": "period_start", "schema": "keyword"},
            {"field": "status",       "schema": "keyword"},
        ],
    },
]


def create_collection(col: dict) -> bool:
    name = col["name"]

    # Check if already exists
    r = requests.get(f"{QDRANT}/collections/{name}", timeout=5)
    if r.status_code == 200:
        info = r.json()["result"]
        vec_count = info.get("vectors_count", 0)
        print(f"  ✓ {name} already exists "
              f"({vec_count} vectors) — skipping")
        return True

    # Create collection
    resp = requests.put(
        f"{QDRANT}/collections/{name}",
        json={
            "vectors": {
                "size":     DIM,
                "distance": "Cosine",
            },
            "optimizers_config": {
                "default_segment_number": 2,
            },
            "replication_factor": 1,
        },
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        print(f"  ✗ {name} creation failed: {resp.text[:100]}")
        return False

    print(f"  ✓ {name} created ({DIM}d Cosine)")

    # Create payload indexes for fast filtered search
    for idx in col.get("payload_indexes", []):
        ir = requests.put(
            f"{QDRANT}/collections/{name}/index",
            json={
                "field_name":   idx["field"],
                "field_schema": idx["schema"],
            },
            timeout=10,
        )
        if ir.status_code in (200, 201):
            print(f"    ✓ index: {idx['field']} ({idx['schema']})")
        else:
            print(f"    ✗ index {idx['field']} failed: {ir.text[:60]}")

    return True


def verify_all():
    print("\n--- Verifying collections ---")
    all_ok = True
    for col in COLLECTIONS:
        name = col["name"]
        r = requests.get(f"{QDRANT}/collections/{name}", timeout=5)
        if r.status_code == 200:
            dim = r.json()["result"]["config"]["params"]["vectors"]["size"]
            assert dim == DIM, f"{name}: expected dim {DIM}, got {dim}"
            print(f"  ✓ {name} — {dim}d verified")
        else:
            print(f"  ✗ {name} MISSING")
            all_ok = False
    return all_ok


if __name__ == "__main__":
    print(f"Qdrant: {QDRANT}")
    print(f"Embed dim: {DIM}")
    print()

    # Health check
    try:
        hc = requests.get(f"{QDRANT}/healthz", timeout=3)
        hc.raise_for_status()
        print("✓ Qdrant healthy\n")
    except Exception as e:
        print(f"✗ Qdrant not reachable: {e}")
        sys.exit(1)

    for col in COLLECTIONS:
        create_collection(col)

    print()
    ok = verify_all()
    if ok:
        print("\n✅ All Qdrant collections ready")
    else:
        print("\n✗ Some collections missing — check Qdrant logs")
        sys.exit(1)
