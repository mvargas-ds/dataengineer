"""
Agent Graph Definition
======================
Defines the LangGraph workflow for the depopulation analysis agent.
"""

from typing import TypedDict, Annotated, List, Optional, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


class AgentState(TypedDict):
    """
    State schema for the depopulation analysis agent.

    Attributes:
        messages: List of conversation messages
        context: Extracted context from the conversation
        tool_results: Results from tool executions
        current_step: Current step in the workflow
        iterations: Number of tool-calling iterations
        final_answer: The final synthesized response
    """
    messages: Annotated[List, "Conversation messages"]
    context: Dict[str, Any]
    tool_results: List[str]
    current_step: str
    iterations: int
    final_answer: Optional[str]


def create_agent_graph(llm_with_tools, tools: list, max_iterations: int = 5):
    """
    Create the LangGraph workflow for the depopulation agent.

    The workflow follows this pattern:

    ```
    [START] → [Router] → [Agent] ←→ [Tools]
                           ↓
                      [Synthesize] → [END]
    ```

    Args:
        llm_with_tools: LLM with tools bound
        tools: List of available tools
        max_iterations: Maximum tool-calling iterations

    Returns:
        Compiled LangGraph workflow
    """

    def router_node(state: AgentState) -> AgentState:
        """
        Route the incoming query to determine the best approach.
        """
        state["current_step"] = "routing"
        state["iterations"] = 0
        return state

    def agent_node(state: AgentState) -> AgentState:
        """
        Main agent reasoning node.
        Decides whether to call tools or generate final answer.
        """
        messages = state["messages"]

        # Call LLM
        response = llm_with_tools.invoke(messages)

        # Update state
        state["messages"] = messages + [response]
        state["current_step"] = "agent"
        state["iterations"] = state.get("iterations", 0) + 1

        return state

    def should_continue(state: AgentState) -> Literal["tools", "synthesize"]:
        """
        Determine if we should continue with tools or synthesize the answer.
        """
        last_message = state["messages"][-1]
        iterations = state.get("iterations", 0)

        # Check for max iterations
        if iterations >= max_iterations:
            return "synthesize"

        # Check if there are tool calls
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"

        return "synthesize"

    def synthesize_node(state: AgentState) -> AgentState:
        """
        Synthesize the final answer from all gathered information.
        """
        messages = state["messages"]

        # Find the last AI message with content
        final_answer = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_answer = msg.content
                break

        state["final_answer"] = final_answer or "Unable to generate response."
        state["current_step"] = "complete"

        return state

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("synthesize", synthesize_node)

    # Set entry point
    workflow.set_entry_point("router")

    # Add edges
    workflow.add_edge("router", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "synthesize": "synthesize"
        }
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("synthesize", END)

    return workflow.compile()


def visualize_graph():
    """
    Print a text visualization of the agent graph.
    """
    graph_viz = """
    ┌─────────────────────────────────────────────────────────────┐
    │               DEPOPULATION AGENT WORKFLOW                   │
    └─────────────────────────────────────────────────────────────┘
    
                          ┌─────────┐
                          │  START  │
                          └────┬────┘
                               │
                               ▼
                          ┌─────────┐
                          │ ROUTER  │  Analyze query type
                          └────┬────┘
                               │
                               ▼
                     ┌─────────────────┐
              ┌──────│     AGENT       │◄─────┐
              │      │  (LLM + Tools)  │      │
              │      └────────┬────────┘      │
              │               │               │
              │    ┌──────────┴──────────┐    │
              │    │                     │    │
              │    ▼                     ▼    │
              │ [Has tool calls?]   [No tools]│
              │    │                     │    │
              │    ▼                     │    │
              │ ┌──────┐                 │    │
              │ │TOOLS │                 │    │
              │ │      │─────────────────┘    │
              │ │ • Snowflake (SQL)          │
              │ │ • INE (Live Stats)         │
              │ │ • Web Search               │
              │ │ • Analysis                 │
              │ └──────┘                      │
              │                               │
              └───────────────────────────────┘
                               │
                               ▼
                      ┌───────────────┐
                      │  SYNTHESIZE   │  Combine results
                      └───────┬───────┘
                              │
                              ▼
                          ┌───────┐
                          │  END  │
                          └───────┘
    """
    print(graph_viz)

