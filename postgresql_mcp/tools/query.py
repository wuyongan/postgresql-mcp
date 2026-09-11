"""SQL Query Execution Tool"""

import json
import logging

from .. import db
from ..common.formatting import rows_to_dicts, truncate_rows
from ..common.response import error_result, ok_result
from ..config import config

logger = logging.getLogger(__name__)


async def execute_query(sql, limit=None):
    """Execute SQL query, supports SELECT/INSERT/UPDATE/DELETE."""
    if not sql or not sql.strip():
        return error_result("SQL parameter is empty")

    max_size = getattr(config.server, "max_query_size", 100000)
    if len(sql) > max_size:
        return error_result(f"SQL query too long (max {max_size:,} characters)")

    default_limit = getattr(config.server, "result_limit", 1000)
    if limit is None:
        limit = default_limit

    try:
        async with db.db_pool.connection() as conn:
            rows = await conn.fetch(sql)
            if not rows:
                return ok_result({"status": "ok", "message": "Query returned no results", "rows": [], "count": 0})
            plain_rows = rows_to_dicts(rows)
            columns = list(rows[0].keys())
            display, count, truncated = truncate_rows(plain_rows, limit)
            return ok_result(
                {
                    "status": "ok",
                    "columns": columns,
                    "rows": display,
                    "count": count,
                    "truncated": truncated,
                }
            )
    except Exception as e:
        logger.error("Query execution failed: %s", e)
        return error_result(str(e))


# Bug 1: SQL Identifier quoting helpers


def _is_sql_keyword(token):
    """Check if a token is a SQL keyword."""
    kw = {
        "select",
        "from",
        "where",
        "join",
        "inner",
        "left",
        "right",
        "outer",
        "on",
        "and",
        "or",
        "not",
        "in",
        "between",
        "like",
        "order",
        "by",
        "group",
        "having",
        "limit",
        "offset",
        "as",
        "union",
        "all",
        "distinct",
        "case",
        "when",
        "then",
        "else",
        "end",
        "null",
        "true",
        "false",
        "is",
        "asc",
        "desc",
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "insert",
        "update",
        "delete",
        "create",
        "drop",
        "alter",
        "table",
        "index",
        "view",
        "set",
        "values",
        "into",
        "primary",
        "key",
        "foreign",
        "references",
        "constraint",
        "check",
        "unique",
        "explain",
        "analyze",
        "for",
        "share",
        "no",
        "lock",
    }
    return token.lower() in kw


def _needs_quoting(token):
    """Check if an identifier needs double-quoting."""
    try:
        token.encode("ascii")
        parts = token.split(".")
        for part in parts:
            if not part or not (part[0].isalpha() or part[0] == "_"):
                return True
            for c in part:
                if c != "_" and (not c.isalnum()):
                    return True
        return False
    except UnicodeEncodeError:
        return True


def _quote_identifiers(sql):
    """Add double-quotes around unquoted identifiers that need quoting."""
    text = sql.strip()
    result = []
    i = 0
    n = len(text)
    sq = chr(39)  # single quote
    dq = chr(34)  # double quote
    bt = chr(96)  # backtick
    while i < n:
        ch = text[i]
        # 1. Preserve string literals
        if ch == sq:
            result.append(ch)
            i += 1
            while i < n:
                if text[i] == sq and i + 1 < n and text[i + 1] == sq:
                    result.append(sq * 2)
                    i += 2
                else:
                    result.append(text[i])
                    i += 1
                if text[i - 1] == sq:
                    break
            continue
        # 2. Preserve already-quoted identifiers
        if ch in (dq, bt):
            result.append(ch)
            i += 1
            while i < n and text[i] != ch:
                if text[i] == ch:
                    i += 1
                result.append(text[i])
                i += 1
            if i < n:
                result.append(text[i])
                i += 1
            continue
        # 3. Build identifier token
        if ch.isalpha() or ch == sq:
            buf = [ch]
            i += 1
            while i < n:
                c = text[i]
                if c.isalnum() or c == sq:
                    buf.append(c)
                    i += 1
                elif c == chr(46):
                    if i + 1 < n and (text[i + 1].isalnum() or text[i + 1] == sq):
                        buf.append(c)
                        i += 1
                    else:
                        break
                elif not c.isspace():
                    if i + 1 < n and (text[i + 1].isalnum() or text[i + 1] in chr(39) + chr(36)):
                        buf.append(c)
                        i += 1
                    else:
                        break
                else:
                    break
            token = "".join(buf)
            if _is_sql_keyword(token):
                result.append(token)
            elif _needs_quoting(token):
                result.append(dq + token + dq)
            else:
                result.append(token)
            continue
        # 4. Everything else
        result.append(ch)
        i += 1
    return "".join(result)


def _flatten_nodes(plan):
    """Recursively flatten nested plan nodes."""
    nodes = [plan]
    for child in plan.get("Plans", []):
        nodes.extend(_flatten_nodes(child))
    return nodes


def _extract_plan_metrics(plan):
    """Extract key performance metrics from an EXPLAIN plan."""
    top = plan
    rows_list = _flatten_nodes(plan)

    index_types = {"index scan", "bitmap index scan"}
    index_used = any(n.get("Node Type", "") in index_types for n in rows_list)

    parallel = any("Plan Workers" in n and int(n.get("Plan Workers", 0)) > 0 for n in rows_list)

    has_seq_scan = any(n.get("Node Type", "") == "seq scan" for n in rows_list)

    warnings = []
    if has_seq_scan:
        warnings.append("Full table scan detected -- consider adding an index")

    join_types = {"hash join", "merge join", "nested loop join"}
    has_join = any(n.get("Node Type", "") in join_types for n in rows_list)
    if has_join and not index_used:
        warnings.append("Join without index detected -- verify join columns are indexed")

    relations = set()
    for n in rows_list:
        rel = n.get("Relation Name", "")
        sch = n.get("Schema", "")
        if rel:
            key = (sch + "." + rel) if sch else rel
            relations.add(key)

    metrics = {
        "operation": top.get("Node Type", "Unknown"),
        "total_time_ms": top.get("Actual Total Time", 0),
        "startup_time_ms": top.get("Actual Startup Time", 0),
        "rows_estimated": top.get("Plan Rows", None),
        "rows_actual": top.get("Actual Rows", 0),
        "cost_startup": top.get("Startup Cost", None),
        "cost_total": top.get("Total Cost", None),
        "index_used": index_used,
        "parallel": parallel,
        "warnings": warnings,
    }
    if relations:
        metrics["tables"] = list(relations)
    return metrics


def _format_plan_to_markdown(metrics):
    """Convert EXPLAIN plan metrics into a human-readable Markdown report."""
    lines = []
    lines.append("## Query Execution Plan")
    lines.append("")
    lines.append("### Overview")
    lines.append("")
    lines.append("- **Operation**: " + str(metrics["operation"]))
    lines.append("- **Total Time**: " + str(metrics["total_time_ms"]))
    lines.append("- **Startup Time**: " + str(metrics["startup_time_ms"]))
    lines.append("- **Estimated Rows**: " + str(metrics.get("rows_estimated", "N/A")))
    lines.append("- **Actual Rows**: " + str(metrics.get("rows_actual", 0)))
    lines.append("")
    lines.append("### Cost")
    lines.append("")
    lines.append("- **Startup Cost**: " + str(metrics.get("cost_startup", 0)))
    lines.append("- **Total Cost**: " + str(metrics.get("cost_total", 0)))
    lines.append("")
    lines.append("### Index & Parallel")
    lines.append("")
    lines.append("- **Index Used**: " + ("Yes" if metrics["index_used"] else "No"))
    lines.append("- **Parallel Workers**: " + ("Yes" if metrics["parallel"] else "No"))
    lines.append("")
    if metrics.get("warnings"):
        lines.append("### Warnings")
        lines.append("")
        for w in metrics["warnings"]:
            lines.append("- " + w)
        lines.append("")
    return "\n".join(lines)


async def explain_query(sql):
    """Analyze SQL execution plan with EXPLAIN (ANALYZE, VERBOSE, FORMAT JSON)."""
    if not sql or not sql.strip():
        return error_result("SQL parameter is empty")

    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT"):
        return error_result("EXPLAIN only supports SELECT statements")

    try:
        # Bug 1: Auto-quote identifiers
        safe_sql = _quote_identifiers(sql_stripped)

        # Bug 5: Check for LIMIT using simple in check
        has_limit = "LIMIT" in sql_upper
        has_for = "FOR" in sql_upper and ("UPDATE" in sql_upper or "SHARE" in sql_upper)

        async with db.db_pool.connection() as conn:
            query = "EXPLAIN (ANALYZE, VERBOSE, FORMAT JSON) " + safe_sql
            rows = await conn.fetch(query)

        if not rows:
            return ok_result({"status": "ok", "message": "EXPLAIN returned no results", "plan": []})

        row = dict(rows[0])

        # FIX: EXPLAIN (FORMAT JSON) returns "QUERY PLAN" as a JSON string.
        # Need json.loads() to parse it into a dict.
        raw_plan_str = row.get("QUERY PLAN")
        if not raw_plan_str:
            return error_result("No QUERY PLAN column in EXPLAIN output. Available keys: " + str(list(row.keys())))

        try:
            plan_array = json.loads(raw_plan_str)
        except json.JSONDecodeError as e:
            return error_result("Failed to parse EXPLAIN output as JSON: " + str(e))

        # plan_array is a list like [{"Plan": {"Node Type": "Limit", ...}}]
        if not isinstance(plan_array, list) or len(plan_array) == 0:
            return error_result("EXPLAIN returned unexpected structure: expected list")

        # The plan dict is at index 0, under key "Plan"
        first_elem = plan_array[0]
        plan_data = first_elem.get("Plan") if isinstance(first_elem, dict) else None

        if plan_data is None:
            keys_str = str(list(first_elem.keys())) if isinstance(first_elem, dict) else "<not a dict>"
            return error_result("No Plan key in EXPLAIN output after parsing. Top-level keys: " + keys_str)

        exec_time = row.get("Execution Time", 0)

        # Bug 4: Extract performance metrics
        metrics = _extract_plan_metrics(plan_data)

        # Bug 5: Add LIMIT warning if large query
        if not has_limit and not has_for:
            est_rows = metrics.get("rows_estimated")
            if est_rows is not None and est_rows > 10000:
                msg = "Query has no LIMIT clause and estimated " + str(int(est_rows)) + " rows -- consider adding LIMIT"
                metrics["warnings"].append(msg)

        # Bug 3: Format as Markdown
        markdown_report = _format_plan_to_markdown(metrics)

        # Also provide the raw plan as JSON for programmatic access
        return ok_result(
            {
                "markdown_report": markdown_report,
                "metrics": metrics,
                "plan_raw": plan_data,
                "execution_time_ms": exec_time,
            }
        )

    except Exception as e:
        logger.error("EXPLAIN failed: %s", e)
        return error_result(str(e))
