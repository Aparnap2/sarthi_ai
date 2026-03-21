"""
DSPy Prompts for BI Agent.

Defines signature classes for:
- TextToSQL: Convert NL questions to PostgreSQL SELECT queries
- NarrativeWriter: Write plain English narratives from SQL results
- PlotlyCodeGen: Generate Plotly chart Python scripts

Uses DSPy ChainOfThought for systematic prompt compilation.
"""
import dspy


class TextToSQL(dspy.Signature):
    """
    Convert a natural language business question to a PostgreSQL SELECT query.
    Use ONLY the tables and columns listed in the schema.
    Return a single SELECT statement. No mutations. No subqueries unless needed.
    Always include a tenant_id filter using the provided tenant_id value.
    """
    question:   str = dspy.InputField(
        desc="Natural language business question from a startup founder")
    schema:     str = dspy.InputField(
        desc="PostgreSQL schema: table names and their exact column names")
    tenant_id:  str = dspy.InputField(
        desc="UUID to use in WHERE tenant_id = '<value>' filter")
    time_hint:  str = dspy.InputField(
        desc="Time range extracted from question, e.g. 'last 30 days', 'last month'")
    sample_row: str = dspy.InputField(
        desc="One sample row from transactions table showing real column values")

    sql: str = dspy.OutputField(
        desc=(
            "Valid PostgreSQL SELECT statement only. "
            "Must include WHERE tenant_id = '<tenant_id>'. "
            "Must end with LIMIT 500. "
            "No markdown, no code fences, no explanation — SQL only."
        )
    )


class NarrativeWriter(dspy.Signature):
    """
    Write a plain English business narrative from SQL query results.
    2-4 sentences. Reference specific numbers from the data.
    End with one concrete, actionable recommendation.
    Never use: leverage, synergy, utilize, streamline, paradigm.
    """
    question:     str = dspy.InputField(
        desc="The original question asked by the founder")
    sql_result:   str = dspy.InputField(
        desc="JSON string of query result rows (max 10 rows shown)")
    row_count:    int = dspy.InputField(
        desc="Total number of rows returned")
    past_answer:  str = dspy.InputField(
        desc="Previous answer to the same question, or 'First time asked'")

    narrative: str = dspy.OutputField(
        desc=(
            "2-4 sentence plain English narrative. "
            "Must cite at least one specific number from sql_result. "
            "Must end with one action recommendation. "
            "If no data found, say so clearly."
        )
    )


class PlotlyCodeGen(dspy.Signature):
    """
    Generate a complete, runnable Python script that creates a Plotly chart
    and saves it as a PNG file to the given chart_path.
    Use plotly.express only. No show(). No interactive output.
    """
    chart_type: str = dspy.InputField(
        desc="One of: line, bar, pie")
    data_json:  str = dspy.InputField(
        desc="JSON array of row dicts from SQL result")
    x_col:      str = dspy.InputField(
        desc="Column name to use for x-axis or labels")
    y_col:      str = dspy.InputField(
        desc="Column name to use for y-axis or values")
    title:      str = dspy.InputField(
        desc="Chart title (max 60 chars)")
    chart_path: str = dspy.InputField(
        desc="Absolute file path where PNG must be saved")

    code: str = dspy.OutputField(
        desc=(
            "Complete Python script. "
            "Must import plotly.express as px and pandas as pd. "
            "Must call fig.write_image(chart_path). "
            "No plt, no matplotlib, no show(). "
            "No markdown fences — code only."
        )
    )
