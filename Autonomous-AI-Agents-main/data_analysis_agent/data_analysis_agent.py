import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
from langchain_ollama import ChatOllama

from data_analysis_agent.sql_guard import validate_sql


def _sqlite_path_from_uri(db_uri: str):
    if not db_uri.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URIs are supported.")

    path = unquote(db_uri.removeprefix("sqlite:///"))
    return str(Path(path))


def _quote_identifier(identifier: str):
    return '"' + identifier.replace('"', '""') + '"'


def _load_schema_details(db_path: str):
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        schema_details = []
        for (table_name,) in tables:
            columns = conn.execute(
                f"PRAGMA table_info({_quote_identifier(table_name)})"
            ).fetchall()
            schema_details.append(
                {
                    "table": table_name,
                    "columns": [
                        {"name": column[1], "type": column[2] or ""}
                        for column in columns
                    ],
                }
            )

    return schema_details


def _format_schema(schema_details):
    schema_lines = []
    for table in schema_details:
        column_text = ", ".join(
            f"{column['name']} {column['type']}".strip()
            for column in table["columns"]
        )
        schema_lines.append(f"- {table['table']}({column_text})")

    return "\n".join(schema_lines)


def _clean_sql(content: str):
    content = content.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", content, flags=re.I | re.S)
    if fenced:
        content = fenced.group(1).strip()

    content = content.strip().strip("`").rstrip(";").strip()
    match = re.search(r"\bselect\b.*", content, flags=re.I | re.S)
    if match:
        content = match.group(0).strip().strip("`").rstrip(";").strip()
    return content


def _format_result(title: str, dataframe: pd.DataFrame, visualization_type: str):
    if dataframe.empty:
        return f"{title}\n\nNo data was found.\n\nVisualization type: {visualization_type}"

    return (
        f"{title}\n\n"
        f"{dataframe.to_markdown(index=False)}\n\n"
        f"Visualization type: {visualization_type}"
    )


def _visualization_type(question: str):
    question_l = question.lower()
    if "pie" in question_l:
        return "Pie"
    if "scatter" in question_l:
        return "Scatter"
    if "line" in question_l:
        return "Line"
    return "Bar"


def _schema_tokens(schema_details):
    tokens = set()
    for table in schema_details:
        names = [table["table"]] + [column["name"] for column in table["columns"]]
        for name in names:
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", name.lower()):
                tokens.add(token)
                if token.endswith("s") and len(token) > 3:
                    tokens.add(token[:-1])
    return tokens


def _is_question_related(question: str, schema_details):
    question_l = question.lower()
    if _fast_sql_for_question(question, _format_schema(schema_details)):
        return True

    off_topic_terms = {
        "weather", "prime", "minister", "president", "news", "joke", "poem",
        "story", "recipe", "movie", "cricket", "football", "stock", "bitcoin",
        "capital", "translate", "email", "resume",
    }
    question_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9]+", question_l))
    if question_tokens & off_topic_terms:
        return False

    useful_analysis_terms = {
        "total", "sum", "average", "avg", "count", "top", "bottom", "list",
        "show", "compare", "trend", "by", "per", "sales", "revenue",
    }
    schema_terms = _schema_tokens(schema_details)
    if question_tokens & schema_terms:
        return True

    return bool((question_tokens & useful_analysis_terms) and (question_tokens & schema_terms))


def _fast_sql_for_question(question: str, schema: str):
    question_l = question.lower()
    schema_l = schema.lower()

    has_chinook_sales_tables = all(
        name in schema_l for name in ("customers", "invoices")
    )
    asks_sales_by_country = (
        "sales" in question_l
        and "country" in question_l
        and has_chinook_sales_tables
    )

    if asks_sales_by_country:
        return """
        SELECT customers.Country AS country,
               ROUND(SUM(invoices.Total), 2) AS total_sales
        FROM invoices
        JOIN customers ON customers.CustomerId = invoices.CustomerId
        GROUP BY customers.Country
        ORDER BY total_sales DESC
        LIMIT 20
        """

    return ""


def suggest_questions_for_schema(schema_details, limit: int = 10):
    suggestions = []

    for table in schema_details:
        table_name = table["table"]
        columns = table["columns"]
        numeric_columns = [
            column["name"] for column in columns
            if any(kind in column["type"].lower() for kind in ("int", "real", "num", "dec", "float", "double"))
        ]
        text_columns = [
            column["name"] for column in columns
            if any(kind in column["type"].lower() for kind in ("char", "text", "date", "time"))
        ]

        if numeric_columns:
            suggestions.append(f"What is the total {numeric_columns[0]} in {table_name}?")
            suggestions.append(f"Show the top 10 {table_name} by {numeric_columns[0]}.")

        if text_columns:
            suggestions.append(f"List records from {table_name} by {text_columns[0]}.")
            suggestions.append(f"Count {table_name} grouped by {text_columns[0]}.")

        if numeric_columns and text_columns:
            suggestions.append(
                f"Show {numeric_columns[0]} by {text_columns[0]} from {table_name}. Visualization type: Bar."
            )

    chinook_schema = _format_schema(schema_details).lower()
    if "customers" in chinook_schema and "invoices" in chinook_schema:
        suggestions = [
            "Total sales of each country. Visualization type: Bar.",
            "Top 10 customers by total sales. Visualization type: Bar.",
            "Monthly sales trend. Visualization type: Line.",
            "Total sales by billing city. Visualization type: Bar.",
            "Top 10 albums by number of tracks. Visualization type: Bar.",
            "Top 10 artists by number of tracks. Visualization type: Bar.",
            "Sales by music genre. Visualization type: Bar.",
            "Average invoice value by country. Visualization type: Bar.",
            "Number of customers by country. Visualization type: Bar.",
            "Top 10 tracks by quantity sold. Visualization type: Bar.",
        ] + suggestions

    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)
        if len(unique_suggestions) == limit:
            break

    return unique_suggestions


class SQLAnalysisAgent:
    def __init__(self, db_uri: str):
        self.db_path = _sqlite_path_from_uri(db_uri)
        self.schema_details = _load_schema_details(self.db_path)
        self.schema = _format_schema(self.schema_details)
        self.suggestions = suggest_questions_for_schema(self.schema_details)
        self.llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            temperature=0,
            num_predict=int(os.getenv("OLLAMA_NUM_PREDICT", "120")),
        )

    def _generate_sql(self, question: str, previous_error: str = ""):
        retry_text = ""
        if previous_error:
            retry_text = f"\nPrevious SQL failed with this error:\n{previous_error}\nReturn a corrected SQL query."

        prompt = f"""
You generate SQLite SELECT queries for data analysis.

Database schema:
{self.schema}

User question:
{question}
{retry_text}

Rules:
- Return one SQLite SELECT query only.
- Do not explain.
- Do not use markdown.
- Do not modify the database.
- Use only tables and columns listed in the schema.
- Keep the result useful for charting, with a text label column and at least one numeric value column when possible.
- Limit large result sets to 20 rows unless the user asks otherwise.
"""
        response = self.llm.invoke(prompt)
        return _clean_sql(response.content)

    def _run_sql(self, sql: str):
        validate_sql(sql)
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(sql, conn)

    def invoke(self, inputs):
        question = inputs["input"]
        visualization_type = _visualization_type(question)

        if not _is_question_related(question, self.schema_details):
            return {
                "output": (
                    "Question Outside Dataset\n\n"
                    "This question does not appear to be related to the selected dataset. "
                    "Please ask about the available tables, columns, or business metrics in this database."
                )
            }

        sql = _fast_sql_for_question(question, self.schema) or self._generate_sql(question)
        try:
            dataframe = self._run_sql(sql)
        except Exception as first_error:
            sql = self._generate_sql(question, str(first_error))
            dataframe = self._run_sql(sql)

        title = question.strip().rstrip("?").title()
        output = _format_result(title, dataframe, visualization_type)
        return {"output": output}


def create_analysis_agent(db_uri: str):
    return SQLAnalysisAgent(db_uri)
