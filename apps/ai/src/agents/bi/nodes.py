"""
BI Agent Nodes for Sarthi v1.0.

Implements 8 node functions for the LangGraph state machine:
  N1: node_understand_query    — Classify query type, check Qdrant cache
  N2: node_generate_sql        — DSPy TextToSQL with sanitization
  N3: node_execute_sql         — Execute with retry logic (max 2 retries)
  N4: node_decide_visualization — Choose chart type
  N5: node_generate_chart      — Call _run_chart_code() (container exec)
  N6: node_generate_narrative  — DSPy NarrativeWriter
  N7: node_write_bi_memory     — Qdrant + PostgreSQL write
  N8: node_emit_bi_output      — Format Telegram message

All nodes are pure functions: BIState → BIState
"""
import os
import re
import stat
import uuid
import json
import datetime
from decimal import Decimal
import subprocess
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

import dspy
import psycopg2
import requests

from .state import BIState
from .prompts import TextToSQL, NarrativeWriter, PlotlyCodeGen

# ── Environment ───────────────────────────────────────────────────
DATABASE_URL      = os.getenv("DATABASE_URL",
    "postgresql://sarthi:sarthi@localhost:5433/sarthi")
QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:0.6b")
EMBED_MODEL       = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

# ── Chart Container Configuration ─────────────────────────────────
CHART_CONTAINER_NAME = "sarthi-chart-runner"
CHART_IMAGE          = "python:alpine"  # already pulled — do NOT pull again
CHART_DEPS_READY     = "/tmp/.chart_deps_ok"

# ── Database Schema ───────────────────────────────────────────────
DB_SCHEMA = """
transactions(id, tenant_id, raw_event_id, txn_date, description, debit, credit, category, confidence, source, external_id)
  -- debit = money out (expenses), credit = money in (revenue)
  -- txn_date = transaction date column
  -- type values: REVENUE, EXPENSE, REFUND (inferred from debit/credit)

vendor_baselines(id, tenant_id, vendor, avg_30d, avg_90d, transaction_count, updated_at)

finance_snapshots(id, tenant_id, snapshot_date, burn_rate, runway_months)

bi_queries(id, tenant_id, query_text, generated_sql, row_count, chart_path, narrative, qdrant_id, created_at)
"""

# ── DSPy — wired to local Ollama, no external API ────────────────
_dspy_lm = dspy.LM(
    model=f"ollama_chat/{OLLAMA_CHAT_MODEL}",
    api_base="http://localhost:11434",
    api_key="ollama",
    max_tokens=500,
    temperature=0.1,
)
dspy.configure(lm=_dspy_lm)
text_to_sql = dspy.ChainOfThought(TextToSQL)
narrative_writer = dspy.ChainOfThought(NarrativeWriter)
plotly_codegen = dspy.ChainOfThought(PlotlyCodeGen)

# ── Postgres helper ───────────────────────────────────────────────
@contextmanager
def _pg():
    """Context manager for PostgreSQL connection."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


# ── Qdrant embed + search helpers ────────────────────────────────
def _embed(text: str) -> List[float]:
    """Embed using nomic-embed-text via Ollama REST."""
    # Build URL from configured OLLAMA_BASE_URL
    embed_url = OLLAMA_BASE_URL.rstrip('/') + '/api/embeddings'
    r = requests.post(
        embed_url,
        json={"model": EMBED_MODEL, "input": text},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    embeddings = data.get("embeddings") or data.get("embedding")
    if isinstance(embeddings, list) and len(embeddings) > 0 and isinstance(embeddings[0], list):
        return embeddings[0]
    return embeddings if isinstance(embeddings, list) else []


def _qdrant_search(collection: str, vector: List[float],
                   tenant_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Search Qdrant collection with tenant filter."""
    r = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/search",
        json={
            "vector": vector,
            "limit": top_k,
            "score_threshold": 0.55,
            "filter": {
                "must": [{"key": "tenant_id", "match": {"value": tenant_id}}]
            },
            "with_payload": True,
        },
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return r.json().get("result", [])


def _qdrant_upsert(collection: str, point_id: str,
                   vector: List[float], payload: Dict[str, Any]) -> None:
    """Upsert a single point into Qdrant."""
    r = requests.put(
        f"{QDRANT_URL}/collections/{collection}/points",
        json={"points": [{
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id)),
            "vector": vector,
            "payload": payload,
        }]},
        timeout=15,
    )
    r.raise_for_status()


# ── Chart Container Execution ────────────────────────────────────
def _ensure_chart_container() -> bool:
    """
    Start sarthi-chart-runner using python:alpine if not already running.
    Installs plotly + kaleido ONCE, marks flag file.
    Uses existing image — no docker pull.

    Returns:
        True if container is ready, False otherwise
    """
    try:
        # Check if already running
        r = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}",
             CHART_CONTAINER_NAME],
            capture_output=True, text=True,
        )
        status = r.stdout.strip()

        if status != "running":
            # Remove stale container if exists
            subprocess.run(
                ["docker", "rm", "-f", CHART_CONTAINER_NAME],
                capture_output=True,
            )
            # Start long-running python:alpine container
            result = subprocess.run([
                "docker", "run", "-d",
                "--name",    CHART_CONTAINER_NAME,
                "-v",        "/tmp:/tmp",           # share /tmp with host
                "--memory",  "256m",                # cap memory
                "--cpus",    "0.5",                 # cap CPU
                CHART_IMAGE,
                "sh", "-c", "tail -f /dev/null",   # keep alive
            ], check=False, capture_output=True)
            
            if result.returncode != 0:
                return False

        # Install deps once (check flag file)
        flag_check = subprocess.run(
            ["docker", "exec", CHART_CONTAINER_NAME,
             "sh", "-c", f"[ -f {CHART_DEPS_READY} ] && echo yes || echo no"],
            capture_output=True, text=True,
        )
        if flag_check.stdout.strip() != "yes":
            install_result = subprocess.run([
                "docker", "exec", CHART_CONTAINER_NAME,
                "pip", "install", "--quiet",
                "plotly", "kaleido", "pandas",
            ], check=False, capture_output=True, timeout=120)
            
            if install_result.returncode != 0:
                return False
                
            subprocess.run([
                "docker", "exec", CHART_CONTAINER_NAME,
                "touch", CHART_DEPS_READY,
            ], check=True, capture_output=True)

        return True
    except Exception:
        return False


def _run_chart_code(code: str, expected_path: str) -> str:
    """
    Execute LLM-generated Plotly code inside python:alpine container.
    Code is written to /tmp, executed in container, PNG read back via /tmp mount.

    Args:
        code: Python code string (may include markdown fences)
        expected_path: Absolute path where PNG should be saved

    Returns:
        expected_path if PNG created, "" otherwise
    """
    try:
        if not _ensure_chart_container():
            return ""
    except Exception:
        return ""   # chart failure must never crash the BI agent

    # Strip markdown code fences if present
    code = re.sub(r"```python|```", "", code).strip()

    # Prepend required imports
    safe_code = (
        "import plotly.express as px\n"
        "import plotly.io as pio\n"
        "import pandas as pd\n"
        "import json\n"
        "pio.kaleido.scope.default_format = 'png'\n"
        "\n"
    ) + code

    tmp_script = f"/tmp/sarthi_chart_{uuid.uuid4().hex[:8]}.py"
    try:
        with open(tmp_script, "w") as f:
            f.write(safe_code)
        os.chmod(tmp_script, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)

        result = subprocess.run(
            ["docker", "exec", CHART_CONTAINER_NAME,
             "python3", tmp_script],
            timeout=30,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ""
        return expected_path if os.path.exists(expected_path) else ""
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmp_script)
        except Exception:
            pass


# ── SQL Sanitization ─────────────────────────────────────────────
def sanitize_sql(sql: str) -> Optional[str]:
    """
    Sanitize SQL to prevent injection attacks.

    Rules:
    - Only SELECT statements allowed
    - No semicolons (prevent statement chaining)
    - No dangerous keywords: INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE
    - Must include tenant_id filter

    Args:
        sql: Raw SQL string from LLM

    Returns:
        Sanitized SQL if valid, None otherwise
    """
    if not sql or not isinstance(sql, str):
        return None

    # Strip whitespace and code fences
    sql = sql.strip()
    sql = re.sub(r"```sql|```", "", sql).strip()

    # Convert to uppercase for checking
    sql_upper = sql.upper()

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return None

    # No semicolons (prevent statement chaining)
    if ";" in sql:
        return None

    # Block dangerous keywords
    dangerous = {"INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"}
    for keyword in dangerous:
        # Match whole word only
        if re.search(rf"\b{keyword}\b", sql_upper):
            return None

    # Must include tenant_id filter (case-insensitive)
    if "TENANT_ID" not in sql_upper:
        return None

    return sql


# ─────────────────────────────────────────────────────────────────
# NODE FUNCTIONS
# Each takes BIState, returns updated BIState dict.
# ─────────────────────────────────────────────────────────────────

def node_understand_query(state: BIState) -> Dict:
    """
    N1: Classify query type and check Qdrant cache.

    Classification:
    - query_type: ADHOC | SCHEDULED | TRIGGERED
    - query_category: trend | breakdown | comparison | aggregation

    Checks Qdrant bi_memory for cached answers to similar queries.

    Args:
        state: Current BIState

    Returns:
        Updated BIState with query_type, query_category, past_queries
    """
    query = state.get("query", "").lower()
    tenant_id = state["tenant_id"]

    # Classify query type (default to ADHOC)
    query_type = "ADHOC"
    if "daily" in query or "weekly" in query or "monthly" in query:
        query_type = "SCHEDULED"
    elif "alert" in query or "anomaly" in query or "spike" in query:
        query_type = "TRIGGERED"

    # Classify query category
    query_category = "aggregation"
    if any(w in query for w in ["trend", "over time", "change", "growth"]):
        query_category = "trend"
    elif any(w in query for w in ["breakdown", "by", "per", "distribution"]):
        query_category = "breakdown"
    elif any(w in query for w in ["compare", "vs", "versus", "difference"]):
        query_category = "comparison"

    # Check Qdrant cache for similar past queries
    past_queries = []
    try:
        vector = _embed(query)
        results = _qdrant_search("bi_memory", vector, tenant_id, top_k=3)
        past_queries = [
            r["payload"]
            for r in results
            if r.get("payload") and r["payload"].get("query_text")
        ]
    except Exception:
        pass  # Cache miss is OK

    return {
        **state,
        "query_type": query_type,
        "query_category": query_category,
        "past_queries": past_queries,
        "data_sources": ["transactions", "vendor_baselines", "finance_snapshots"],
    }


def node_generate_sql(state: BIState) -> Dict:
    """
    N2: Generate SQL using DSPy TextToSQL.

    Uses the DB_SCHEMA and tenant_id to generate a SELECT query.
    Sanitizes output to prevent SQL injection.

    Args:
        state: Current BIState

    Returns:
        Updated BIState with generated_sql or error
    """
    query = state["query"]
    tenant_id = state["tenant_id"]

    # Extract time hint from query
    time_hint = "last 30 days"
    if "last week" in query.lower():
        time_hint = "last 7 days"
    elif "last month" in query.lower():
        time_hint = "last 30 days"
    elif "last quarter" in query.lower():
        time_hint = "last 90 days"
    elif "last year" in query.lower():
        time_hint = "last 365 days"

    # Get sample row for context
    sample_row = ""
    try:
        with _pg() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, txn_date, description, debit, credit, category
                    FROM transactions
                    WHERE tenant_id = %s
                    LIMIT 1
                """, (tenant_id,))
                row = cur.fetchone()
                if row:
                    sample_row = (
                        f"id={row[0]}, txn_date={row[1]}, "
                        f"description='{row[2]}', debit={row[3]}, "
                        f"credit={row[4]}, category={row[5]}"
                    )
    except Exception:
        pass

    try:
        result = text_to_sql(
            question=query,
            schema=DB_SCHEMA,
            tenant_id=tenant_id,
            time_hint=time_hint,
            sample_row=sample_row,
        )
        raw_sql = result.sql.strip()
        sanitized = sanitize_sql(raw_sql)

        if sanitized is None:
            return {
                **state,
                "error": f"SQL sanitization failed: {raw_sql[:100]}",
                "generated_sql": "",
            }

        return {
            **state,
            "generated_sql": sanitized,
            "error": "",
        }
    except Exception as e:
        return {
            **state,
            "error": f"SQL generation failed: {str(e)}",
            "generated_sql": "",
        }


def node_execute_sql(state: BIState) -> Dict:
    """
    N3: Execute SQL with retry logic (max 2 retries).

    Retries on transient errors (connection issues, timeouts).
    Does not retry on SQL syntax errors.

    Args:
        state: Current BIState

    Returns:
        Updated BIState with sql_result dict or error
    """
    sql = state.get("generated_sql", "")
    if not sql:
        return {
            **state,
            "error": "No SQL to execute",
            "sql_result": {"rows": [], "columns": [], "count": 0},
        }

    tenant_id = state["tenant_id"]
    retry_count = state.get("retry_count", 0)
    max_retries = 2

    try:
        with _pg() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                row_count = cur.rowcount if cur.rowcount >= 0 else len(rows)

                # Convert to list of dicts with JSON-serializable values
                rows_as_dicts = []
                for row in rows:
                    row_dict = {}
                    for col, val in zip(columns, row):
                        if val is None:
                            row_dict[col] = None
                        elif isinstance(val, Decimal):
                            row_dict[col] = float(val)
                        elif isinstance(val, (datetime.date, datetime.datetime)):
                            row_dict[col] = val.isoformat()
                        elif isinstance(val, bytes):
                            row_dict[col] = val.decode('utf-8', errors='replace')
                        elif isinstance(val, (list, dict)):
                            row_dict[col] = val
                        else:
                            row_dict[col] = val
                    rows_as_dicts.append(row_dict)

                return {
                    **state,
                    "sql_result": {
                        "rows": rows_as_dicts,
                        "columns": columns,
                        "count": row_count,
                    },
                    "error": "",
                    "retry_count": 0,  # Reset on success
                    "retryable": False,
                }
    except psycopg2.Error as e:
        # Check if retryable error
        error_str = str(e).lower()
        is_retryable = any(x in error_str for x in ["connection", "timeout", "deadlock"])

        if is_retryable and retry_count < max_retries:
            return {
                **state,
                "error": f"Retryable error (attempt {retry_count + 1}/{max_retries}): {str(e)}",
                "retry_count": retry_count + 1,
                "retryable": True,
            }

        return {
            **state,
            "error": f"SQL execution failed: {str(e)}",
            "sql_result": {"rows": [], "columns": [], "count": 0},
            "retryable": False,
        }
    except Exception as e:
        return {
            **state,
            "error": f"Unexpected error: {str(e)}",
            "sql_result": {"rows": [], "columns": [], "count": 0},
            "retryable": False,
        }


def node_decide_visualization(state: BIState) -> Dict:
    """
    N4: Choose chart type based on query category and data.

    Rules:
    - trend + time series data → line
    - breakdown + categorical data → bar
    - comparison → bar
    - aggregation with single value → none
    - empty results → none

    Args:
        state: Current BIState

    Returns:
        Updated BIState with chart_type
    """
    sql_result = state.get("sql_result", {})
    rows = sql_result.get("rows", [])
    columns = sql_result.get("columns", [])
    query_category = state.get("query_category", "aggregation")

    # Empty results → no chart
    if not rows or not columns:
        return {**state, "chart_type": "none"}

    # Single value aggregation → no chart
    if len(rows) == 1 and len(columns) <= 2:
        return {**state, "chart_type": "none"}

    # Trend queries → line chart
    if query_category == "trend":
        # Check if we have a date/time column
        date_cols = [c for c in columns if "date" in c.lower() or "time" in c.lower()]
        if date_cols:
            return {**state, "chart_type": "line"}

    # Breakdown or comparison → bar chart
    if query_category in ("breakdown", "comparison"):
        return {**state, "chart_type": "bar"}

    # Default: no chart
    return {**state, "chart_type": "none"}


def node_generate_chart(state: BIState) -> Dict:
    """
    N5: Generate chart using container execution.

    Calls _run_chart_code() to execute Plotly code in python:alpine container.
    Chart saved to /tmp/charts/{uuid}.png

    Args:
        state: Current BIState

    Returns:
        Updated BIState with chart_path (or "" if no chart)
    """
    chart_type = state.get("chart_type", "none")
    if chart_type == "none":
        return {**state, "chart_path": ""}

    sql_result = state.get("sql_result", {})
    rows = sql_result.get("rows", [])
    columns = sql_result.get("columns", [])

    if not rows or not columns:
        return {**state, "chart_path": ""}

    # Determine x and y columns
    x_col = columns[0]
    y_col = columns[1] if len(columns) > 1 else columns[0]

    # Find date column for x-axis if present
    for col in columns:
        if "date" in col.lower() or "time" in col.lower():
            x_col = col
            break

    # Find numeric column for y-axis
    for col in columns:
        if col != x_col:
            # Check if column contains numeric data
            sample_val = rows[0].get(col)
            if isinstance(sample_val, (int, float)):
                y_col = col
                break

    # Prepare data for LLM
    data_json = json.dumps(rows[:10])  # Limit to 10 rows for context
    title = state["query"][:60]
    chart_path = f"/tmp/charts/{uuid.uuid4().hex[:8]}.png"

    # Ensure charts directory exists
    os.makedirs("/tmp/charts", exist_ok=True)

    try:
        result = plotly_codegen(
            chart_type=chart_type,
            data_json=data_json,
            x_col=x_col,
            y_col=y_col,
            title=title,
            chart_path=chart_path,
        )
        code = result.code.strip()

        # Execute in container
        actual_path = _run_chart_code(code, chart_path)

        return {
            **state,
            "chart_path": actual_path,
        }
    except Exception:
        return {**state, "chart_path": ""}


def node_generate_narrative(state: BIState) -> Dict:
    """
    N6: Generate narrative using DSPy NarrativeWriter.

    Writes 2-4 sentence plain English explanation with specific numbers
    and actionable recommendation.

    Args:
        state: Current BIState

    Returns:
        Updated BIState with narrative
    """
    query = state["query"]
    sql_result = state.get("sql_result", {})
    rows = sql_result.get("rows", [])
    row_count = sql_result.get("count", 0)

    # Handle empty results
    if not rows:
        return {
            **state,
            "narrative": f"No data found for: {query}. Try adjusting the time range or check if transactions exist for this period.",
        }

    # Get past answer if available
    past_queries = state.get("past_queries", [])
    past_answer = "First time asked"
    if past_queries:
        past_answer = past_queries[0].get("narrative", "First time asked")

    try:
        result = narrative_writer(
            question=query,
            sql_result=json.dumps(rows[:10]),
            row_count=row_count,
            past_answer=past_answer,
        )
        narrative = result.narrative.strip()
        return {**state, "narrative": narrative}
    except Exception as e:
        # Fallback: simple summary
        return {
            **state,
            "narrative": f"Query returned {row_count} rows. First result: {json.dumps(rows[0]) if rows else 'none'}",
        }


def node_write_bi_memory(state: BIState) -> Dict:
    """
    N7: Write query + results to Qdrant bi_memory and PostgreSQL.

    Stores:
    - Qdrant: Query embedding + payload for semantic search
    - PostgreSQL: Full query record in bi_queries table

    Args:
        state: Current BIState

    Returns:
        Updated BIState (unchanged on write failure)
    """
    tenant_id = state["tenant_id"]
    query = state["query"]
    generated_sql = state.get("generated_sql", "")
    sql_result = state.get("sql_result", {})
    row_count = sql_result.get("count", 0)
    chart_path = state.get("chart_path", "")
    narrative = state.get("narrative", "")

    # Create content for embedding
    content = f"Query: {query} | SQL: {generated_sql} | Result: {narrative}"

    try:
        # Embed and upsert to Qdrant
        vector = _embed(content)
        point_id = f"{tenant_id}-bi-{uuid.uuid4().hex[:8]}"
        _qdrant_upsert(
            collection="bi_memory",
            point_id=point_id,
            vector=vector,
            payload={
                "tenant_id": tenant_id,
                "query_text": query,
                "generated_sql": generated_sql,
                "narrative": narrative,
                "row_count": row_count,
                "memory_type": "bi_query",
            },
        )

        # Write to PostgreSQL bi_queries table
        qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id))
        with _pg() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bi_queries
                    (tenant_id, query_text, generated_sql, row_count, chart_path, narrative, qdrant_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (tenant_id, query, generated_sql, row_count, chart_path, narrative, qdrant_id))
                conn.commit()

    except Exception:
        pass  # Memory write failure must not stop workflow

    return state


def node_emit_bi_output(state: BIState) -> Dict:
    """
    N8: Format output_message for Telegram.

    Format:
    - Query summary
    - Narrative (2-4 sentences)
    - Key numbers from result
    - Chart attachment path (if any)

    Args:
        state: Current BIState

    Returns:
        Updated BIState with output_message
    """
    query = state["query"]
    narrative = state.get("narrative", "")
    sql_result = state.get("sql_result", {})
    rows = sql_result.get("rows", [])
    chart_path = state.get("chart_path", "")
    error = state.get("error", "")

    # Handle errors
    if error:
        msg = f"❌ *Query Error*\n\n{error[:500]}"
        return {**state, "output_message": msg}

    # Handle empty results
    if not rows:
        msg = f"📊 *BI Query*\n\n*Q:* {query}\n\nNo data found."
        return {**state, "output_message": msg}

    # Build message with key metrics
    msg = f"📊 *BI Query*\n\n*Q:* {query}\n\n{narrative}\n\n"

    # Add top 3 rows as summary
    if rows:
        msg += "*Key Results:*\n"
        for i, row in enumerate(rows[:3], 1):
            # Format row as key=value pairs
            row_str = " | ".join(f"{k}={v}" for k, v in list(row.items())[:3])
            msg += f"{i}. {row_str}\n"

    # Add chart indicator
    if chart_path:
        msg += f"\n📈 Chart: {chart_path}"

    return {**state, "output_message": msg}
