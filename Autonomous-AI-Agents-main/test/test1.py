from multi_agent import create_multi_agent
from database_config import DATABASES
from visualization.plot_builder import create_plot

db = "chinook"

multi_agent = create_multi_agent(DATABASES[db])

user_prompt = "Tabulate the sales of rock genre music in the last 5 years. Visualization type: Line."

print("User prompt:\n", user_prompt)

result = multi_agent.invoke({
    "input": user_prompt,
    "messages": []
})

analysis_result = result["analysis_text"]
print("Analysed results:\n", analysis_result)

plot_path = create_plot(analysis_result, user_prompt)
print("Visualization generated successfully:", plot_path)
