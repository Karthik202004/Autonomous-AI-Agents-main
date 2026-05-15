import os
import re
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from visualization.company_template import apply_company_template


OUTPUT_DIR = Path("visualization")


def _clean_cell(value: str):
    value = value.strip().strip("|").strip()
    value = value.replace("$", "").replace(",", "")
    if not value:
        return value
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _parse_markdown_table(text: str):
    lines = [line.strip() for line in text.splitlines() if "|" in line]
    for index, line in enumerate(lines[:-1]):
        next_line = lines[index + 1]
        if not re.fullmatch(r"[:\-\|\s]+", next_line):
            continue

        headers = [_clean_cell(cell) for cell in line.strip("|").split("|")]
        rows = []
        for row_line in lines[index + 2:]:
            if not row_line.startswith("|") or "|" not in row_line:
                break
            cells = [_clean_cell(cell) for cell in row_line.strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(cells)

        if rows:
            return pd.DataFrame(rows, columns=headers)
    return None


def _parse_pipe_table(text: str):
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines[:-1]):
        if "|" not in line:
            continue
        next_line = lines[index + 1]
        if not re.fullmatch(r"[-\|\s]+", next_line):
            continue

        headers = [_clean_cell(cell) for cell in line.split("|")]
        rows = []
        for row_line in lines[index + 2:]:
            if "|" not in row_line or re.fullmatch(r"[-\|\s]+", row_line):
                break
            cells = [_clean_cell(cell) for cell in row_line.split("|")]
            if len(cells) == len(headers):
                rows.append(cells)

        if rows:
            return pd.DataFrame(rows, columns=headers)
    return None


def _parse_colon_pairs(text: str):
    rows = []
    for line in text.splitlines():
        match = re.match(r"^\s*([A-Za-z][\w\s.&/-]*?)\s*[-:]\s*\$?([\d,]+(?:\.\d+)?)\s*$", line)
        if match:
            rows.append([match.group(1).strip(), _clean_cell(match.group(2))])

    if rows:
        return pd.DataFrame(rows, columns=["name", "value"])
    return None


def extract_dataframe(analysis_text: str):
    for parser in (_parse_markdown_table, _parse_pipe_table, _parse_colon_pairs):
        dataframe = parser(analysis_text)
        if dataframe is not None and not dataframe.empty:
            return dataframe
    raise ValueError("Could not find tabular data in the analysis result.")


def _chart_type(question: str, analysis_text: str):
    combined = f"{question}\n{analysis_text}".lower()
    if "pie" in combined:
        return "pie"
    if "scatter" in combined:
        return "scatter"
    if "line" in combined:
        return "line"
    return "bar"


def _pick_columns(dataframe: pd.DataFrame):
    numeric_columns = list(dataframe.select_dtypes(include="number").columns)
    if not numeric_columns:
        raise ValueError("No numeric column found for plotting.")

    y_column = numeric_columns[-1]
    x_candidates = [column for column in dataframe.columns if column != y_column]
    x_column = x_candidates[0] if x_candidates else dataframe.index.name or "index"
    return x_column, y_column


def create_plot(analysis_text: str, question: str, output_dir=OUTPUT_DIR):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataframe = extract_dataframe(analysis_text)
    x_column, y_column = _pick_columns(dataframe)
    chart_type = _chart_type(question, analysis_text)

    apply_company_template()
    plt.figure()

    if chart_type == "pie":
        plt.pie(dataframe[y_column], labels=dataframe[x_column], autopct="%1.1f%%")
        plt.title(y_column.replace("_", " ").title())
    elif chart_type == "line":
        sns.lineplot(data=dataframe, x=x_column, y=y_column, marker="o")
        plt.title(f"{y_column} by {x_column}")
        plt.xticks(rotation=35, ha="right")
    elif chart_type == "scatter":
        sns.scatterplot(data=dataframe, x=x_column, y=y_column)
        plt.title(f"{y_column} by {x_column}")
        plt.xticks(rotation=35, ha="right")
    else:
        sns.barplot(data=dataframe, x=x_column, y=y_column)
        plt.title(f"{y_column} by {x_column}")
        plt.xticks(rotation=35, ha="right")

    plt.xlabel(str(x_column).replace("_", " ").title())
    plt.ylabel(str(y_column).replace("_", " ").title())
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"plot_{timestamp}.png"
    plt.savefig(output_path)
    plt.close()
    return str(output_path)
