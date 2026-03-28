"""
12 unit tests for all 4 integrations.
All run in mock mode — no real Stripe/Plaid credentials needed.
"""
import os, pytest, asyncio

# Force mock mode
os.environ["STRIPE_API_KEY"]      = ""
os.environ["PLAID_ACCESS_TOKEN"]  = ""
os.environ["SLACK_WEBHOOK_URL"]   = ""
os.environ["TELEGRAM_API_BASE"]   = "http://localhost:8085"
os.environ["TELEGRAM_BOT_TOKEN"]  = "123:TOKEN"
os.environ["TELEGRAM_CHAT_ID"]    = "42"
os.environ["DATABASE_URL"]        = \
    "postgresql://sarthi:sarthi@localhost:5433/sarthi"

TENANT = "test-tenant-integration"


# ── Stripe ────────────────────────────────────────────────────────

def test_stripe_mock_mode_enabled():
    from src.integrations.stripe import MOCK_MODE
    assert MOCK_MODE is True

def test_stripe_mock_returns_valid_shape():
    from src.integrations.stripe import get_mrr_snapshot
    snap = get_mrr_snapshot(TENANT)
    assert snap["mrr_cents"]          > 0
    assert snap["arr_cents"]          == snap["mrr_cents"] * 12
    assert snap["active_customers"]   > 0
    assert snap["new_customers"]      >= 0
    assert snap["churned_customers"]  >= 0
    assert snap["source"]             == "stripe_mock"
    assert "fetched_at" in snap

def test_stripe_mock_arr_is_12x_mrr():
    from src.integrations.stripe import get_mrr_snapshot
    snap = get_mrr_snapshot(TENANT)
    assert snap["arr_cents"] == snap["mrr_cents"] * 12


# ── Plaid ─────────────────────────────────────────────────────────

def test_plaid_mock_mode_enabled():
    from src.integrations.plaid import MOCK_MODE
    assert MOCK_MODE is True

def test_plaid_mock_returns_valid_shape():
    from src.integrations.plaid import get_bank_snapshot
    snap = get_bank_snapshot(TENANT)
    assert snap["balance_cents"]  > 0
    assert snap["burn_30d_cents"] > 0
    assert snap["source"]         == "bank_mock"
    assert "fetched_at" in snap

def test_plaid_runway_computable_from_snapshot():
    from src.integrations.plaid import get_bank_snapshot
    snap = get_bank_snapshot(TENANT)
    # Runway = balance / monthly burn
    runway = snap["balance_cents"] / snap["burn_30d_cents"]
    assert runway > 0
    assert runway < 120   # sanity check — under 10 years


# ── Product DB ────────────────────────────────────────────────────

def test_product_db_mock_returns_valid_shape():
    from src.integrations.product_db import get_product_snapshot
    snap = get_product_snapshot(TENANT)
    assert snap["active_users_30d"] >= 0
    assert "source" in snap


# ── Slack (mock → Telegram fallback) ─────────────────────────────

def test_slack_mock_mode_enabled():
    from src.integrations.slack import USE_SLACK
    assert USE_SLACK is False     # SLACK_WEBHOOK_URL is empty

@pytest.mark.asyncio
async def test_slack_send_returns_ok_shape():
    from src.integrations.slack import send_message
    result = await send_message("Test pulse message 🔴")
    # ok may be False if tg-mock is not running — shape check only
    assert "ok"      in result
    assert "channel" in result
    # Channel will be 'telegram_mock' in pure mock mode, or 'telegram' if creds provided
    assert result["channel"] in ("telegram_mock", "telegram", "slack")

@pytest.mark.asyncio
async def test_slack_send_empty_text_does_not_crash():
    from src.integrations.slack import send_message
    result = await send_message("")
    assert "ok" in result   # must return dict, never raise

@pytest.mark.asyncio
async def test_slack_send_with_full_draft():
    from src.integrations.slack import send_message
    result = await send_message(
        "📊 Investor update ready",
        full_draft="## March 2026\n\n**MRR:** ₹8,500\n**Burn:** ₹32,000",
    )
    assert "ok"      in result
    assert "channel" in result


# ── Additional Coverage ─────────────────────────────────────────

def test_stripe_mock_data_has_reasonable_values():
    """Verify mock MRR data is within realistic bounds."""
    from src.integrations.stripe import get_mrr_snapshot, _MOCK_MRR_DATA
    snap = get_mrr_snapshot(TENANT)
    # MRR should be between ₹100 and ₹10,00,000
    assert 10000 <= snap["mrr_cents"] <= 100000000
    # Active customers should be positive
    assert snap["active_customers"] > 0
    # Churn should not exceed active customers
    assert snap["churned_customers"] < snap["active_customers"]
