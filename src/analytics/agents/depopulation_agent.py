"""
Depopulation Analysis Agent
===========================
LangGraph-based agent for analyzing rural depopulation in Spain.

Uses Groq (Llama 3) as the LLM and multiple tools for comprehensive analysis.
"""

import os
from typing import TypedDict, Annotated, List, Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from loguru import logger

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Local imports
from .tools.snowflake_tool import query_snowflake, get_schema_info
from .tools.ine_tool import query_ine
from .tools.web_search_tool import search_web, search_depopulation_research
from .tools.analysis_tool import analyze_depopulation_factors
from .prompts.expert_prompts import SYSTEM_PROMPT, ROUTER_PROMPT
from .memory.conversation import ConversationMemory

load_dotenv()


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[List, "The messages in the conversation"]
    context: Dict[str, Any]  # Extracted context
    tool_results: List[str]  # Results from tool calls
    iterations: int  # Number of agent iterations
    final_answer: Optional[str]  # The final synthesized answer


class DepopulationAgent:
    """
    AI Agent specialized in Spanish rural depopulation analysis.

    Features:
    - Multi-tool reasoning (Snowflake, INE, web search, analysis)
    - Conversational memory for follow-up questions
    - Expert prompts for accurate, insightful responses
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        model: str = "qwen/qwen3-32b",
        temperature: float = 0.1,
        max_iterations: int = 3
    ):
        self.max_iterations = max_iterations
        """
        Initialize the depopulation analysis agent.

        Args:
            groq_api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Groq model to use (default: llama-3.1-70b-versatile)
            temperature: LLM temperature (lower = more focused)
        """
        self.api_key = groq_api_key or os.getenv('GROQ_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or pass groq_api_key parameter."
            )

        # Initialize LLM
        self.llm = ChatGroq(
            api_key=self.api_key,
            model=model,
            temperature=temperature
        )

        # Define tools
        self.tools = [
            query_snowflake,
            query_ine,
            search_web,
            search_depopulation_research,
            analyze_depopulation_factors
        ]

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Initialize memory
        self.memory = ConversationMemory()

        # Build the graph
        self.graph = self._build_graph()

        logger.info(f"DepopulationAgent initialized with model: {model}")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""

        # Create the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("synthesize", self._synthesize_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": "synthesize"
            }
        )

        # Tools always go back to agent
        workflow.add_edge("tools", "agent")

        # Synthesize goes to END
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    def _agent_node(self, state: AgentState) -> AgentState:
        """Main agent reasoning node."""
        messages = state["messages"]
        iterations = state.get("iterations", 0) + 1

        logger.debug(f"Agent iteration: {iterations}/{self.max_iterations}")

        # Add system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(content=SYSTEM_PROMPT + "\n\n" + get_schema_info())
            messages = [system_msg] + messages

        # Call LLM with tools
        response = self.llm_with_tools.invoke(messages)

        # Add response to messages
        return {"messages": messages + [response], "iterations": iterations}

    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue with tools or synthesize."""
        last_message = state["messages"][-1]
        iterations = state.get("iterations", 0)

        # Check if max iterations reached
        if iterations >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached. Forcing synthesis.")
            return "end"

        # If there are tool calls, continue
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"

        # Otherwise, synthesize the final answer
        return "end"

    def _synthesize_node(self, state: AgentState) -> AgentState:
        """Synthesize the final answer from all gathered information."""
        messages = state["messages"]

        # Get the last AI message content
        last_ai_message = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                last_ai_message = msg
                break

        if last_ai_message:
            return {"final_answer": last_ai_message.content}

        return {"final_answer": "I couldn't generate a response. Please try again."}

    def chat(self, message: str) -> str:
        """
        Send a message to the agent and get a response.

        Args:
            message: User's question or message

        Returns:
            Agent's response
        """
        # Add to memory
        self.memory.add_user_message(message)

        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "context": self.memory.get_context(),
            "tool_results": [],
            "iterations": 0,
            "final_answer": None
        }

        # Run the graph
        try:
            result = self.graph.invoke(initial_state)

            # Get final answer
            answer = result.get("final_answer", "")

            if not answer:
                # Extract from last message
                for msg in reversed(result.get("messages", [])):
                    if isinstance(msg, AIMessage):
                        answer = msg.content
                        break

            # Add to memory
            self.memory.add_assistant_message(answer)

            return answer

        except Exception as e:
            logger.error(f"Error in agent: {e}")
            return f"Error processing your request: {str(e)}"

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")

    def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        print("\n" + "="*70)
        print("🏘️  SPAIN DEPOPULATION ANALYSIS AGENT")
        print("="*70)
        print("\n📊 I can help you analyze rural depopulation in Spain.")
        print("   I have access to population data, economic indicators,")
        print("   and academic research.\n")
        print("💡 Example questions:")
        print("   • How many depopulated municipalities are there in Spain?")
        print("   • Which provinces have the highest depopulation rates?")
        print("   • What factors contribute to rural depopulation?")
        print("   • Compare population trends between 2003 and 2023")
        print("   • What strategies can help repopulate rural areas?")
        print("\n   Type 'exit' or 'quit' to end the conversation.")
        print("   Type 'clear' to clear conversation history.")
        print("-"*70 + "\n")

        while True:
            try:
                user_input = input("👤 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit', 'salir', 'q']:
                    print("\n👋 Goodbye! Thank you for using the agent.")
                    break

                if user_input.lower() == 'clear':
                    self.clear_memory()
                    print("🗑️  Conversation history cleared.\n")
                    continue

                print("\n🤖 Agent: Analyzing...\n")
                response = self.chat(user_input)
                print(f"🤖 Agent: {response}\n")
                print("-"*70 + "\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")


def create_agent(
    groq_api_key: Optional[str] = None,
    model: str = "qwen/qwen3-32b"
) -> DepopulationAgent:
    """
    Factory function to create a depopulation analysis agent.

    Args:
        groq_api_key: Groq API key
        model: Model to use

    Returns:
        Configured DepopulationAgent instance
    """
    return DepopulationAgent(groq_api_key=groq_api_key, model=model)


def main():
    """Main entry point for the agent."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Spain Depopulation Analysis Agent"
    )
    parser.add_argument(
        "--model",
        default="qwen/qwen3-32b",
        help="Groq model to use"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query mode - ask one question and exit"
    )

    args = parser.parse_args()

    try:
        agent = create_agent(model=args.model)

        if args.query:
            # Single query mode
            response = agent.chat(args.query)
            print(response)
        else:
            # Interactive mode
            agent.run_interactive()

    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nTo fix this:")
        print("1. Get a free API key from https://console.groq.com/")
        print("2. Add to your .env file: GROQ_API_KEY=your_key_here")


if __name__ == "__main__":
    main()

