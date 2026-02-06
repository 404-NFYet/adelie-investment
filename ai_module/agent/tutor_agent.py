"""AI Tutor agent using LangGraph with Tool-based Router pattern."""

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Sequence, TypedDict, Optional, AsyncGenerator
import json

from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .prompts import get_system_prompt


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence, add_messages]
    difficulty: str
    context_type: Optional[str]
    context_id: Optional[int]


class TutorAgent:
    """AI Tutor agent using LangGraph."""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        difficulty: str = "beginner",
        checkpointer=None,
    ):
        """
        Initialize the AI Tutor agent.
        
        Args:
            model: OpenAI model to use
            difficulty: Default difficulty level
            checkpointer: Optional LangGraph checkpointer for session persistence
        """
        self.model_name = model
        self.default_difficulty = difficulty
        self.checkpointer = checkpointer
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            streaming=True,
        )
        
        # Initialize tools
        self.tools = self._load_tools()
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Create the graph
        self.graph = self._build_graph()
    
    def _load_tools(self):
        """Load all available tools."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "ai-module"))
        
        from tools import (
            get_glossary,
            lookup_term,
            search_historical_cases,
            get_related_companies,
            get_supply_chain,
            get_today_briefing,
            compare_past_present,
        )
        
        return [
            get_glossary,
            lookup_term,
            search_historical_cases,
            get_related_companies,
            get_supply_chain,
            get_today_briefing,
            compare_past_present,
        ]
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        
        # Create the graph
        graph = StateGraph(AgentState)
        
        # Define nodes
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self.tools))
        
        # Define edges
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END,
            }
        )
        graph.add_edge("tools", "agent")
        
        # Compile the graph
        if self.checkpointer:
            return graph.compile(checkpointer=self.checkpointer)
        return graph.compile()
    
    def _agent_node(self, state: AgentState) -> dict:
        """Agent node that processes messages and decides actions."""
        messages = list(state["messages"])
        difficulty = state.get("difficulty", self.default_difficulty)
        
        # Window memory: keep max 20 turns (40 messages)
        MAX_MESSAGES = 40  # 20 turns
        if len(messages) > MAX_MESSAGES:
            messages = messages[-MAX_MESSAGES:]
        
        # Get system prompt
        system_prompt = get_system_prompt(difficulty)
        
        # Prepare messages with system prompt
        all_messages = [SystemMessage(content=system_prompt)] + messages
        
        # Get response from LLM
        response = self.llm_with_tools.invoke(all_messages)
        
        return {"messages": [response]}
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue to tools or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the LLM made tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        
        return "end"
    
    def invoke(
        self,
        message: str,
        difficulty: str = None,
        context_type: str = None,
        context_id: int = None,
    ) -> str:
        """
        Process a message and return a response.
        
        Args:
            message: User message
            difficulty: Difficulty level
            context_type: Context type (briefing/case/comparison/glossary)
            context_id: Context ID
            
        Returns:
            Agent response
        """
        # Build initial state
        state = {
            "messages": [HumanMessage(content=message)],
            "difficulty": difficulty or self.default_difficulty,
            "context_type": context_type,
            "context_id": context_id,
        }
        
        # Run the graph
        result = self.graph.invoke(state)
        
        # Extract final response
        final_message = result["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            return final_message.content
        
        return str(final_message)
    
    async def astream(
        self,
        message: str,
        difficulty: str = None,
        context_type: str = None,
        context_id: int = None,
        thread_id: str = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the agent response.
        
        Args:
            message: User message
            difficulty: Difficulty level
            context_type: Context type
            context_id: Context ID
            thread_id: Optional thread ID for session persistence
            
        Yields:
            Stream events (thinking, tool_call, text_delta, done)
        """
        # Build initial state
        state = {
            "messages": [HumanMessage(content=message)],
            "difficulty": difficulty or self.default_difficulty,
            "context_type": context_type,
            "context_id": context_id,
        }
        
        # Build config with thread_id for checkpointer
        config = {}
        if thread_id:
            config = {"configurable": {"thread_id": thread_id}}
        
        # Signal thinking
        yield {"type": "thinking", "content": "질문을 분석하고 있습니다..."}
        
        # Stream the graph
        async for event in self.graph.astream(state, config=config, stream_mode="updates"):
            for node, updates in event.items():
                if node == "agent":
                    messages = updates.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            # Check for tool calls
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    yield {
                                        "type": "tool_call",
                                        "tool": tool_call["name"],
                                        "args": tool_call["args"],
                                    }
                            else:
                                # Stream text content
                                yield {
                                    "type": "text_delta",
                                    "content": msg.content,
                                }
                
                elif node == "tools":
                    # Tool results
                    messages = updates.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, ToolMessage):
                            yield {
                                "type": "tool_result",
                                "tool": msg.name,
                                "result_preview": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                            }
        
        yield {"type": "done"}


def create_tutor_agent(
    model: str = None,
    difficulty: str = "beginner",
    checkpointer=None,
) -> TutorAgent:
    """
    Create a TutorAgent instance.
    
    Args:
        model: OpenAI model to use (defaults to env variable or gpt-4o-mini)
        difficulty: Default difficulty level
        checkpointer: Optional LangGraph checkpointer for session persistence
        
    Returns:
        TutorAgent instance
    """
    if model is None:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    return TutorAgent(model=model, difficulty=difficulty, checkpointer=checkpointer)


# Simple test
if __name__ == "__main__":
    agent = create_tutor_agent()
    
    # Test invoke
    response = agent.invoke("PER이 뭐야?", difficulty="beginner")
    print(response)
