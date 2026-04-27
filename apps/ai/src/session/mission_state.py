"""Mission State management for Sarthi V3.0 Session Layer.

This module provides the MissionState dataclass and methods to read/write
mission state data from the database.

PRD Reference: Sections 508-532

Architecture:
- Finance: runway_days, burn_alert, burn_severity
- BI: mrr_trend, churn_rate
- Ops: churn_risk_users, top_feature_ask, error_spike
- Cross: active_alerts, founder_focus
"""

import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://sarthi:sarthi@localhost:5432/sarthi")


@dataclass
class MissionState:
    """Mission State dataclass containing all domain metrics.

    This represents the current state of the tenant across all domains
    and is used by the relevance gate to determine agent responsiveness.
    """

    # Identity
    tenant_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Finance Domain
    runway_days: Optional[int] = None
    burn_alert: Optional[bool] = None
    burn_severity: Optional[str] = None  # low, medium, high, critical

    # BI Domain
    mrr_trend: Optional[str] = None  # growing, stable, declining
    churn_rate: Optional[float] = None  # percentage

    # Ops Domain
    churn_risk_users: Optional[List[str]] = field(default_factory=list)
    top_feature_ask: Optional[str] = None
    error_spike: Optional[bool] = None

    # Cross-functional
    active_alerts: Optional[List[str]] = field(default_factory=list)
    founder_focus: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for DB storage."""
        data = asdict(self)
        # Convert datetime to ISO string
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        # Convert lists to JSON strings
        data["churn_risk_users"] = (
            ",".join(self.churn_risk_users) if self.churn_risk_users else None
        )
        data["active_alerts"] = (
            ",".join(self.active_alerts) if self.active_alerts else None
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "MissionState":
        """Create MissionState from database row."""
        if data.get("timestamp") and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Parse comma-separated lists
        if data.get("churn_risk_users") and isinstance(data["churn_risk_users"], str):
            data["churn_risk_users"] = (
                data["churn_risk_users"].split(",") if data["churn_risk_users"] else []
            )
        else:
            data.setdefault("churn_risk_users", [])

        if data.get("active_alerts") and isinstance(data["active_alerts"], str):
            data["active_alerts"] = (
                data["active_alerts"].split(",") if data["active_alerts"] else []
            )
        else:
            data.setdefault("active_alerts", [])

        return cls(**{k: v for k, v in data.items() if k != "id"})


def _get_db_connection():
    """Get a database connection with graceful fallback."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Using fallback mode.")
        return None


def get_mission_state(tenant_id: str) -> Optional[MissionState]:
    """Retrieve the most recent mission state for a tenant.

    Args:
        tenant_id: The tenant identifier

    Returns:
        MissionState object if found, None otherwise
    """
    conn = _get_db_connection()
    if conn is None:
        logger.warning(f"[FALLBACK] Returning empty mission state for tenant {tenant_id}")
        return _get_fallback_state(tenant_id)

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, tenant_id, timestamp,
                   runway_days, burn_alert, burn_severity,
                   mrr_trend, churn_rate,
                   churn_risk_users, top_feature_ask, error_spike,
                   active_alerts, founder_focus
            FROM mission_states
            WHERE tenant_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """

        cursor.execute(query, (tenant_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            logger.debug(f"Retrieved mission state for tenant {tenant_id}")
            return MissionState.from_dict(dict(row))

        logger.debug(f"No mission state found for tenant {tenant_id}")
        return None

    except Exception as e:
        logger.error(f"Error fetching mission state for tenant {tenant_id}: {e}")
        return _get_fallback_state(tenant_id)


def save_mission_state(state: MissionState) -> bool:
    """Save mission state to the database.

    Args:
        state: MissionState object to save

    Returns:
        True if saved successfully, False otherwise
    """
    conn = _get_db_connection()
    if conn is None:
        logger.warning(f"[FALLBACK] Cannot save mission state - database unavailable")
        return False

    try:
        cursor = conn.cursor()

        query = """
            INSERT INTO mission_states (
                tenant_id, timestamp,
                runway_days, burn_alert, burn_severity,
                mrr_trend, churn_rate,
                churn_risk_users, top_feature_ask, error_spike,
                active_alerts, founder_focus
            ) VALUES (
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s
            )
        """

        data = state.to_dict()
        cursor.execute(
            query,
            (
                data["tenant_id"],
                data["timestamp"],
                data["runway_days"],
                data["burn_alert"],
                data["burn_severity"],
                data["mrr_trend"],
                data["churn_rate"],
                data["churn_risk_users"],
                data["top_feature_ask"],
                data["error_spike"],
                data["active_alerts"],
                data["founder_focus"],
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Saved mission state for tenant {state.tenant_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving mission state for tenant {state.tenant_id}: {e}")
        return False


def _get_fallback_state(tenant_id: str) -> MissionState:
    """Get a fallback mission state when database is unavailable.

    Args:
        tenant_id: The tenant identifier

    Returns:
        MissionState with default/empty values
    """
    return MissionState(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        runway_days=None,
        burn_alert=False,
        burn_severity=None,
        mrr_trend=None,
        churn_rate=None,
        churn_risk_users=[],
        top_feature_ask=None,
        error_spike=False,
        active_alerts=[],
        founder_focus=None,
    )