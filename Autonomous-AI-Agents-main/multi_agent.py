from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.messages import AIMessage
from data_analysis_agent.data_analysis_agent import create_analysis_agent

class GraphState(TypedDict):
    input: str  # User question
    analysis_text: str  # Analyzed data from the analysis agent
    messages: List[AIMessage]

def create_multi_agent(db: str):

    # Create the data analysis agent and node
    analysis_agent = create_analysis_agent(db)

    def analysis_node(state: GraphState):
        result = analysis_agent.invoke({"input": state["input"]})

        analysis_output = result["output"]

        return {
            "analysis_text": analysis_output,
            "messages": state["messages"]
        }

    # Create the state graph
    graph = StateGraph(GraphState)
    graph.add_node("analysis", analysis_node)
    graph.set_entry_point("analysis")
    graph.add_edge("analysis", END)

    return graph.compile()
