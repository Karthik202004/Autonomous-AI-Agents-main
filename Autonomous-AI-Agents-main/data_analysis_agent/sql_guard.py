# Safe guard to make sure no data manipulation or definition queries are run except SELECT
FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "create", "truncate", "attach", "detach"
]

def validate_sql(sql: str):
    sql_l = sql.lower()
    if not sql_l.strip().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_l:
            raise ValueError(f"Forbidden SQL keyword: {keyword}")
