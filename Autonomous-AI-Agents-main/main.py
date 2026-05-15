from database_config import DATABASES, USER_DB_ACCESS
from multi_agent import create_multi_agent
from visualization.plot_builder import create_plot

# Function to check if the user has access to the requested database
def check_database_access(user: str, db_name: str):
    if db_name not in DATABASES:
        print("Unknown database.")
        return False

    elif db_name not in USER_DB_ACCESS.get(user, []):
        print("You do not have access to this database.")
        return False
    return True
    
def main():
    user = input("User: ")
    db = input("Database: ")

    # Check if user has access to database
    if(not check_database_access(user, db)):
       return

    multi_agent = create_multi_agent(DATABASES[db])
    
    while True:
        # Get user question
        question = input("\nQuestion (type \"exit\" if done): ").strip()
        
        if question == "exit":
            break
        if not question:
            continue

        # Initial state
        state = {
            "input": question,
            "analysis_text": "",
            "messages": []
        }

        print("\n[Streaming agent progress]\n")

        # Stream execution
        for event in multi_agent.stream(state):
            for node_name, node_update in event.items():

                if node_name == "analysis":
                    print("[Data Analysis agent finished]")
                    print(node_update["analysis_text"], "\n")

                # Merge partial update into state
                state.update(node_update)

        # Retrieve final outputs
        analysis_result = state["analysis_text"]

        try:
            plot_path = create_plot(analysis_result, question)
            print(f"[Visualization saved] {plot_path}")
        except ValueError as exc:
            print(f"[Visualization skipped] {exc}")

if __name__ == "__main__":
    main()
