from pathlib import Path
import re
import sqlite3

import pandas as pd
import streamlit as st

from database_config import DATABASES, USER_DB_ACCESS
from data_analysis_agent.data_analysis_agent import (
    _load_schema_details,
    _sqlite_path_from_uri,
    suggest_questions_for_schema,
)
from multi_agent import create_multi_agent
from visualization.plot_builder import create_plot


st.set_page_config(
    page_title="Autonomous AI Data Analyst",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)


APP_CSS = """
<style>
    :root {
        --page-bg: #f6f7f4;
        --surface: #ffffff;
        --surface-muted: #f1f5f2;
        --ink: #1f2933;
        --muted: #647067;
        --line: #d9ded8;
        --accent: #0f766e;
        --accent-strong: #0b5f59;
        --gold: #b7791f;
    }

    .stApp {
        background: var(--page-bg);
        color: var(--ink);
    }

    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.25rem;
        max-width: 1220px;
    }

    [data-testid="stSidebar"] {
        background: #202823;
        border-right: 1px solid #323c35;
    }

    [data-testid="stSidebar"] * {
        color: #f7faf8;
    }

    [data-testid="stSidebar"] .stSelectbox label {
        color: #d5ddd7;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #151c18;
        border-color: #455148;
        color: #f7faf8;
    }

    .sidebar-title {
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0.25rem 0 1rem 0;
    }

    .sidebar-note {
        background: #151c18;
        border: 1px solid #455148;
        border-radius: 8px;
        padding: 0.75rem;
        color: #d5ddd7;
        font-size: 0.86rem;
        line-height: 1.35;
    }

    .topbar {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1.2rem;
    }

    .eyebrow {
        color: var(--accent);
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0;
    }

    .app-title {
        font-size: 2.15rem;
        line-height: 1.05;
        font-weight: 760;
        color: var(--ink);
        margin: 0.1rem 0 0 0;
    }

    .header-meta {
        color: var(--muted);
        font-size: 0.92rem;
        text-align: right;
        white-space: nowrap;
    }

    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 0.8rem 0.95rem;
        box-shadow: 0 1px 2px rgba(31, 41, 51, 0.04);
    }

    div[data-testid="stMetric"] label {
        color: var(--muted);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 1.12rem;
    }

    .section-title {
        color: var(--ink);
        font-size: 1.05rem;
        font-weight: 720;
        margin: 0.25rem 0 0.4rem 0;
    }

    .status-box {
        background: #fffaf0;
        border: 1px solid #ead6a8;
        border-left: 4px solid var(--gold);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        color: #5f4515;
    }

    .stButton > button {
        border-radius: 8px;
        border: 1px solid var(--accent-strong);
        background: var(--accent);
        color: #ffffff;
        font-weight: 700;
        min-height: 2.65rem;
    }

    .stButton > button:hover {
        border-color: var(--accent-strong);
        background: var(--accent-strong);
        color: #ffffff;
    }

    .stTextArea textarea {
        border-radius: 8px;
        border-color: var(--line);
        background: var(--surface);
        color: var(--ink);
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: 0 1px 2px rgba(31, 41, 51, 0.04);
    }

    .stDownloadButton > button {
        border-radius: 8px;
        border: 1px solid var(--line);
        background: var(--surface-muted);
        color: var(--ink);
        font-weight: 650;
    }
</style>
"""


def available_databases_for_user(user: str):
    return USER_DB_ACCESS.get(user, [])


def _safe_name(name: str):
    return re.sub(r"[^a-zA-Z0-9_]+", "_", Path(name).stem).strip("_").lower() or "uploaded"


def save_uploaded_dataset(uploaded_file):
    upload_dir = Path("database") / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(uploaded_file.name).suffix.lower()
    safe_stem = _safe_name(uploaded_file.name)

    if suffix in {".db", ".sqlite", ".sqlite3"}:
        db_path = upload_dir / f"{safe_stem}{suffix}"
        db_path.write_bytes(uploaded_file.getvalue())
        return f"sqlite:///{db_path.resolve()}"

    if suffix == ".csv":
        db_path = upload_dir / f"{safe_stem}.sqlite"
        table_name = safe_stem
        dataframe = pd.read_csv(uploaded_file)
        with sqlite3.connect(db_path) as conn:
            dataframe.to_sql(table_name, conn, if_exists="replace", index=False)
        return f"sqlite:///{db_path.resolve()}"

    raise ValueError("Upload a SQLite database or CSV file.")


@st.cache_resource(show_spinner=False)
def get_agent(db_uri: str):
    return create_multi_agent(db_uri)


def get_suggestions(db_uri: str):
    db_path = _sqlite_path_from_uri(db_uri)
    schema_details = _load_schema_details(db_path)
    return suggest_questions_for_schema(schema_details)


def analyze_question(user: str, db_name: str, question: str, db_uri: str, enforce_access=True):
    if enforce_access and db_name not in DATABASES:
        raise ValueError("Unknown database.")

    if enforce_access and db_name not in available_databases_for_user(user):
        raise PermissionError("This user does not have access to the selected database.")

    agent = get_agent(db_uri)
    state = {
        "input": question,
        "analysis_text": "",
        "messages": [],
    }

    result = agent.invoke(state)
    analysis_text = result["analysis_text"]
    if "Question Outside Dataset" in analysis_text:
        return analysis_text, None

    plot_path = create_plot(analysis_text, question)
    return analysis_text, plot_path


def main():
    st.markdown(APP_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="sidebar-title">Autonomous AI Analyst</div>', unsafe_allow_html=True)
        users = list(USER_DB_ACCESS.keys())
        default_user_index = users.index("admin") if "admin" in users else 0
        user = st.selectbox("User", users, index=default_user_index)

        allowed_databases = available_databases_for_user(user)
        uploaded_file = st.file_uploader(
            "Upload dataset",
            type=["db", "sqlite", "sqlite3", "csv"],
        )

        uploaded_db_uri = None
        uploaded_db_name = None
        if uploaded_file is not None:
            try:
                uploaded_db_uri = save_uploaded_dataset(uploaded_file)
                uploaded_db_name = f"uploaded: {_safe_name(uploaded_file.name)}"
                st.success("Dataset uploaded")
            except Exception as exc:
                st.error(str(exc))

        database_options = allowed_databases.copy()
        if uploaded_db_name:
            database_options.insert(0, uploaded_db_name)

        db_name = st.selectbox("Database", database_options)
        active_db_uri = uploaded_db_uri if db_name == uploaded_db_name else DATABASES[db_name]
        enforce_access = db_name != uploaded_db_name

        st.markdown("---")
        st.markdown(
            '<div class="sidebar-note">Model: Ollama<br>Output: analysis table and PNG chart<br>Mode: local workspace</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <div class="eyebrow">Database Intelligence Workspace</div>
                <div class="app-title">Autonomous AI Data Analyst</div>
            </div>
            <div class="header-meta">User: {user}<br>Database: {db_name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("Session User", user)
    metric_col_2.metric("Dataset", db_name)
    metric_col_3.metric("Access", "Authorized")

    suggestions = []
    try:
        suggestions = get_suggestions(active_db_uri)
    except Exception:
        suggestions = []

    if suggestions:
        with st.container(border=True):
            st.markdown('<div class="section-title">Suggested Questions</div>', unsafe_allow_html=True)
            suggestion_cols = st.columns(2)
            for index, suggestion in enumerate(suggestions[:10]):
                with suggestion_cols[index % 2]:
                    if st.button(suggestion, key=f"suggestion_{index}", use_container_width=True):
                        st.session_state["question"] = suggestion

    if "question" not in st.session_state:
        st.session_state["question"] = suggestions[0] if suggestions else "total sales of each country"

    with st.container(border=True):
        st.markdown('<div class="section-title">Query</div>', unsafe_allow_html=True)
        question = st.text_area(
            "Question",
            key="question",
            height=120,
            placeholder="Example: total sales of each country",
            label_visibility="collapsed",
        )
        run = st.button("Analyze", type="primary", use_container_width=True)

    if run:
        if not question.strip():
            st.warning("Enter a question first.")
            return

        status = st.empty()
        status.markdown('<div class="status-box">Analyzing request...</div>', unsafe_allow_html=True)

        try:
            with st.spinner("Running analysis and creating chart..."):
                analysis_text, plot_path = analyze_question(
                    user,
                    db_name,
                    question.strip(),
                    active_db_uri,
                    enforce_access=enforce_access,
                )
        except Exception as exc:
            status.empty()
            st.error(str(exc))
            return

        status.success("Analysis complete")

        result_col, chart_col = st.columns([1.05, 1], gap="large")
        with result_col:
            with st.container(border=True):
                st.markdown('<div class="section-title">Analysis Result</div>', unsafe_allow_html=True)
                st.markdown(analysis_text)

        with chart_col:
            with st.container(border=True):
                st.markdown('<div class="section-title">Visualization</div>', unsafe_allow_html=True)
                path = Path(plot_path) if plot_path else None
                if path and path.exists():
                    st.image(str(path), use_container_width=True)
                    st.caption(str(path))
                    st.download_button(
                        "Download chart",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="image/png",
                        use_container_width=True,
                    )
                else:
                    st.info("No chart was generated for this response.")


if __name__ == "__main__":
    main()
