from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain.tools import tool

def create_vis_agent():
    # System prompt for the data visualization agent
    system_prompt = """
    You are a data visualization agent.
    You will work with a data analysis agent who provides you with the analyzed data.
    You must translate the analyzed data into Python code that uses matplotlib and seaborn to create visualizations.
    
    You MUST:
    1. Parse the table structure (headers and rows).
    2. Infer x-axis and y-axis.
    3. Generate Python code to visualize the data.
    4. You MUST apply the corporate seaborn theme by calling:
    from company_template import apply_company_template
    apply_company_template()
    5. Do NOT define colors, fonts, or styles manually.

    Rules:
    - Use matplotlib and seaborn only.
    - Do NOT call plt.show().
    - Save the figure using plt.savefig("visualization/<output_file>.png").
    - Generate executable Python code only.

    Output:
    - Return only the python code snippet.
    - Do NOT include any other text.
    """

    # LLM instance
    llm = llm = ChatOllama(model="llama3.1")

    # Create the agent
    agent = create_agent(
        model=llm,        
        tools=[],           
        system_prompt=system_prompt,        
        debug=False        
    )

    return agent