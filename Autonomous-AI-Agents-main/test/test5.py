import sqlite3
from multi_agent import create_multi_agent
from database_config import DATABASES
import pandas as pd
from visualization.plot_builder import create_plot

# Path to the database
db_path = "database/chinook.db"

def pass_sql_query(db_path: str):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # SQL query
    query = """
    SELECT CAST(strftime('%Y', invoice_."InvoiceDate") AS BIGINT) AS "Year",
    SUM(CASE WHEN invoice_."BillingCountry" = 'USA'
        THEN invoice_."Total" END) AS "USA",
    SUM(CASE WHEN invoice_."BillingCountry" = 'United Kingdom'
        THEN invoice_."Total" END) AS "United Kingdom",
    SUM(CASE WHEN invoice_."BillingCountry" = 'Canada'
        THEN invoice_."Total" END) AS "Canada"
    FROM "Invoices" AS invoice_
    WHERE invoice_."BillingCountry" IN ('USA', 'United Kingdom', 'Canada')
    GROUP BY 1
    ORDER BY 1 ASC
    """

    # Execute the query
    cur.execute(query)

    # Fetch all results
    rows = cur.fetchall()

    # Column names
    columns = [desc[0] for desc in cur.description]

    # Load into a pandas DataFrame
    df = pd.DataFrame(rows, columns=columns)

    # Display results
    print(df)

    # Close connection
    conn.close()

db = "chinook"

multi_agent = create_multi_agent(DATABASES[db])

user_prompt = "Tabulate the annual sales in USA, United Kingdom, and Canada. Visualization type: Stacked bar chart."

print("Database: \n", db)
print("User prompt:\n", user_prompt)

print("\n\nCorrect analysis result for verification:\n")

pass_sql_query(db_path)

result = multi_agent.invoke({
    "input": user_prompt,
    "messages": []
})

analysis_result = result["analysis_text"]
print("\nAnalysed results:\n", analysis_result)

plot_path = create_plot(analysis_result, user_prompt)
print("Visualization generated successfully:", plot_path)
