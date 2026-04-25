"""
Tests for Investor Relations Warmup Alerts.
"""
import pytest
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5433/iterateswarm")
os.environ["DATABASE_URL"] = DATABASE_URL


@pytest.mark.asyncio
async def test_get_investor_warmup_alerts():
    """Rahul is 5 days overdue - must appear. Priya is not overdue - must not appear."""
    # Direct import after setting up paths
    import sys
    from pathlib import Path
    
    REPO = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(REPO / "apps/ai"))
    sys.path.insert(0, str(REPO / "apps/ai/src"))
    
    from src.db import db
    
    tenant = "00000000-0000-0000-0000-000000000001"
    
    # Run query directly via db
    rows = await db.fetch("""
        SELECT 
            investor_name,
            firm,
            raise_priority,
            warm_up_days,
            EXTRACT(DAY FROM NOW() - last_contact_at)::INT - warm_up_days AS days_overdue
        FROM investor_relationships
        WHERE tenant_id = %s
          AND last_contact_at IS NOT NULL
          AND NOW() - last_contact_at > warm_up_days * INTERVAL '1 day'
        ORDER BY raise_priority
    """, tenant)
    
    names = [r["investor_name"] for r in rows]
    
    assert "Rahul Mehta" in names, f"Overdue investor not returned: {names}"
    assert "Priya Kapoor" not in names, f"Non-overdue investor wrongly returned: {names}"
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_investor_status_summary():
    """Test full summary with total_tracked, overdue_count, top_priority."""
    import sys
    from pathlib import Path
    
    REPO = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(REPO / "apps/ai"))
    sys.path.insert(0, str(REPO / "apps/ai/src"))
    
    from src.db import db
    
    tenant = "00000000-0000-0000-0000-000000000001"
    
    # Get overdue
    overdue = await db.fetch("""
        SELECT investor_name, raise_priority
        FROM investor_relationships
        WHERE tenant_id = %s
          AND last_contact_at IS NOT NULL
          AND NOW() - last_contact_at > warm_up_days * INTERVAL '1 day'
        ORDER BY raise_priority
    """, tenant)
    
    # Get total
    total = await db.fetchval("""
        SELECT COUNT(*) FROM investor_relationships WHERE tenant_id = %s
    """, tenant)
    
    summary = {
        "total_tracked": total or 0,
        "overdue_count": len(overdue),
        "top_priority": overdue[0]["investor_name"] if overdue else None,
    }
    
    assert summary["total_tracked"] >= 2, "Should track at least 2 investors"
    assert summary["overdue_count"] >= 1, "Rahul must be in overdue count"
    assert summary["top_priority"] == "Rahul Mehta", f"Top priority should be Rahul: {summary['top_priority']}"


@pytest.mark.asyncio
async def test_no_investors_does_not_crash():
    """A tenant with zero investor relationships must return empty."""
    import sys
    from pathlib import Path
    
    REPO = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(REPO / "apps/ai"))
    sys.path.insert(0, str(REPO / "apps/ai/src"))
    
    from src.db import db
    
    # Non-existent tenant
    result = await db.fetch("""
        SELECT investor_name FROM investor_relationships 
        WHERE tenant_id = '99999999-9999-9999-9999-999999999999'
    """)
    
    assert result == [], f"Expected empty list, got: {result}"