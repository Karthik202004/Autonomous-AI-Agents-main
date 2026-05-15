import sqlite3
from multi_agent import create_multi_agent
from database_config import DATABASES
from visualization.plot_builder import create_plot

# Path to the database
db_path = "database/sakila.db"

def pass_sql_query(db_path: str):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # SQL query
    query = """
    SELECT category.name, AVG(length) as avg_length
    FROM film
    JOIN film_category USING (film_id)
    JOIN category USING (category_id)
    GROUP BY category.name
    ORDER BY avg_length DESC;
    """

    # Execute the query
    cur.execute(query)

    # Fetch all results
    rows = cur.fetchall()

    # Print results
    for name, avg_len in rows:
        print(f"{name}: {avg_len:.2f}")

    # Close connection
    conn.close()

db = "sakila"

multi_agent = create_multi_agent(DATABASES[db])

user_prompt = "Tabulate the average length of films by all categories. Visualization type: Pie."

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
