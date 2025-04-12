"""
LangGraph-based agent implementation for Staples Brain.

This module provides a base agent implementation built on LangGraph that can be
initialized from database agent definitions.
"""
import logging
import json
import re
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set, Callable, Union, TypedDict, cast

# LangGraph imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Import utility classes from base_agent
from backend.agents.base_agent import Guardrails, EntityCollectionState

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    messages: List[BaseMessage]  # The messages in the conversation
    context: Dict[str, Any]  # Additional context about the conversation
    entities: Dict[str, Any]  # Entities collected during the conversation
    tools_calls: List[Dict[str, Any]]  # Tools called during the conversation
    tools_results: List[Dict[str, Any]]  # Results from tool calls
    agent_config: Dict[str, Any]  # Configuration for the agent
    current_step: str  # Current step in the conversation
    memory: Dict[str, Any]  # Memory for the agent


class LangGraphAgent:
    """
    LangGraph-based agent implementation.
    
    This agent uses LangGraph to define a state machine for handling conversations,
    with entity extraction, tool calling, and response generation.
    """
    
    def __init__(self, config: Dict[str, Any], llm: Optional[ChatOpenAI] = None):
        """
        Initialize the LangGraph agent with configuration and optional LLM.
        
        Args:
            config: Agent configuration loaded from the database
            llm: Optional LLM instance to use for this agent
        """
        self.config = config
        self.name = config["name"]
        self.description = config.get("description", "")
        self.id = config.get("id", str(uuid.uuid4()))
        self.tools = config.get("tools", [])
        self.patterns = config.get("patterns", [])
        self.response_templates = config.get("response_templates", {})
        
        # Set default model if not provided
        model_name = config.get("model_name", "gpt-4o")
        temperature = config.get("temperature", 0.7)
        
        # Initialize LLM if not provided
        self.llm = llm or ChatOpenAI(
            model=model_name,
            temperature=temperature
        )
        
        # Initialize guardrails
        self.guardrails = Guardrails()
        
        # Create the agent graph
        self.graph = self._create_agent_graph()
        
    def _create_agent_graph(self) -> StateGraph:
        """
        Create the LangGraph state machine for this agent.
        
        Returns:
            StateGraph instance configured for this agent
        """
        # Define the graph and its nodes
        graph = StateGraph(AgentState)
        
        # Add nodes to the graph
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("extract_entities", self._extract_entities)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("generate_response", self._generate_response)
        
        # Define the edges between nodes
        graph.add_edge("initialize", "extract_entities")
        graph.add_conditional_edges(
            "extract_entities",
            self._should_execute_tools,
            {
                True: "execute_tools",
                False: "generate_response"
            }
        )
        graph.add_edge("execute_tools", "generate_response")
        graph.add_edge("generate_response", END)
        
        # Set the entry point
        graph.set_entry_point("initialize")
        
        # Compile the graph
        return graph.compile()
    
    async def process_message(self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a message through the agent graph.
        
        Args:
            message: The user message to process
            session_id: Session identifier
            context: Additional context for processing
            
        Returns:
            Response with agent output
        """
        # Create initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "context": context or {},
            "entities": {},
            "tools_calls": [],
            "tools_results": [],
            "agent_config": self.config,
            "current_step": "initialize",
            "memory": {
                "session_id": session_id,
                "conversation_history": []
            }
        }
        
        # Add session_id to the context
        initial_state["context"]["session_id"] = session_id
        
        # Process the message through the graph
        try:
            config = {"configurable": {"thread_id": session_id}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Get the AI message from the final state
            ai_messages = [m for m in final_state["messages"] if isinstance(m, AIMessage)]
            if not ai_messages:
                # Fallback if no AI message was generated
                return {
                    "response": "I'm sorry, I couldn't process your request properly.",
                    "agent": self.name,
                    "confidence": 0.0,
                    "entities": final_state["entities"],
                    "tools_used": [tc["tool_name"] for tc in final_state["tools_calls"]]
                }
            
            # Get the last AI message
            ai_message = ai_messages[-1]
            
            # Apply guardrails to the response
            corrected_response, violations = self.guardrails.apply_guardrails(ai_message.content)
            
            return {
                "response": corrected_response,
                "agent": self.name,
                "confidence": 1.0,  # This agent was specifically invoked
                "entities": final_state["entities"],
                "tools_used": [tc["tool_name"] for tc in final_state["tools_calls"]],
                "violations": [v.to_dict() for v in violations] if violations else []
            }
        except Exception as e:
            logger.error(f"Error processing message with agent {self.name}: {str(e)}", exc_info=True)
            return {
                "response": f"I encountered an issue while processing your request: {str(e)}",
                "agent": self.name,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _initialize_state(self, state: AgentState) -> AgentState:
        """
        Initialize the state for a new conversation turn.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Set current step
        state["current_step"] = "extract_entities"
        
        # Add system message if it doesn't exist
        if not any(isinstance(m, SystemMessage) for m in state["messages"]):
            system_prompt = self._create_system_prompt()
            state["messages"].insert(0, SystemMessage(content=system_prompt))
        
        return state
    
    def _create_system_prompt(self) -> str:
        """
        Create a system prompt for the agent based on configuration.
        
        Returns:
            System prompt string
        """
        # Use system prompt from config if available
        if "system_prompt" in self.config:
            return self.config["system_prompt"]
        
        # Otherwise, create a default system prompt
        return f"""You are a Staples customer service AI assistant named {self.name}.
Your primary responsibility is: {self.description}

When helping customers:
- Always be professional, helpful, and friendly
- Identify yourself as a Staples customer service representative
- Never mention that you are an AI, just say you're a Staples representative
- Always stay within the scope of Staples products and services
- If you need more information to help a customer, ask clarifying questions
- Use tools available to you to provide accurate information

Your goal is to provide accurate, helpful assistance to Staples customers."""
    
    async def _extract_entities(self, state: AgentState) -> AgentState:
        """
        Extract entities from the user message.
        
        Args:
            state: Current state
            
        Returns:
            Updated state with extracted entities
        """
        # Get the last user message
        user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        if not user_messages:
            return state
        
        user_message = user_messages[-1].content
        
        # Define entity extraction prompt
        entity_prompt = PromptTemplate.from_template("""
Extract the following entities from the user message:
{entity_definitions}

User message: {user_message}

Return a JSON object with the extracted entities, with the entity name as the key and the extracted value as the value.
If an entity is not present, do not include it in the response.

Output (JSON only):
""")
        
        # Get entity definitions from config
        entity_definitions = self.config.get("entity_definitions", [])
        if not entity_definitions:
            # No entity definitions, skip extraction
            state["current_step"] = "execute_tools"
            return state
        
        # Format entity definitions for the prompt
        entity_defs_text = "\n".join([
            f"- {e['name']}: {e.get('description', '')}" 
            for e in entity_definitions
        ])
        
        # Create and invoke the extraction chain
        entity_chain = entity_prompt | self.llm | StrOutputParser()
        
        try:
            result = await entity_chain.ainvoke({
                "entity_definitions": entity_defs_text,
                "user_message": user_message
            })
            
            # Parse the result as JSON
            extracted_entities = json.loads(result)
            
            # Update state with extracted entities
            state["entities"].update(extracted_entities)
            
            # Set current step
            state["current_step"] = "execute_tools"
            
            return state
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}", exc_info=True)
            # Continue to next step on failure
            state["current_step"] = "execute_tools"
            return state
    
    def _should_execute_tools(self, state: AgentState) -> bool:
        """
        Determine if tools should be executed based on the state.
        
        Args:
            state: Current state
            
        Returns:
            True if tools should be executed, False otherwise
        """
        # Check if there are any tools defined for this agent
        if not self.tools:
            return False
        
        # For now, always try to execute tools if they exist
        return True
    
    async def _execute_tools(self, state: AgentState) -> AgentState:
        """
        Execute tools based on the extracted entities.
        
        Args:
            state: Current state
            
        Returns:
            Updated state with tool execution results
        """
        # Get the last user message
        user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        if not user_messages:
            state["current_step"] = "generate_response"
            return state
        
        user_message = user_messages[-1].content
        
        # Define tool calling prompt
        tool_prompt = PromptTemplate.from_template("""
You have access to the following tools:
{tool_definitions}

Based on the user message and extracted entities, determine if any tools should be called.
If a tool should be called, return a JSON object with the tool name and arguments.
If no tool should be called, return an empty JSON object.

User message: {user_message}
Extracted entities: {entities}

Output (JSON only):
""")
        
        # Format tool definitions for the prompt
        tool_defs_text = "\n".join([
            f"- {t['name']}: {t.get('description', '')}\n  Arguments: {', '.join(t.get('parameters', {}))}" 
            for t in self.tools
        ])
        
        # Create and invoke the tool calling chain
        tool_chain = tool_prompt | self.llm | StrOutputParser()
        
        try:
            result = await tool_chain.ainvoke({
                "tool_definitions": tool_defs_text,
                "user_message": user_message,
                "entities": json.dumps(state["entities"])
            })
            
            # Parse the result as JSON
            tool_call = json.loads(result)
            
            if tool_call and "tool_name" in tool_call and "tool_args" in tool_call:
                # Add the tool call to the state
                state["tools_calls"].append(tool_call)
                
                # Execute the tool
                # Note: This is a stub - in a real implementation, this would call the actual tool
                tool_result = {
                    "tool_name": tool_call["tool_name"],
                    "result": f"Tool {tool_call['tool_name']} executed with args {tool_call['tool_args']}",
                    "status": "success"
                }
                
                # Add the tool result to the state
                state["tools_results"].append(tool_result)
        except Exception as e:
            logger.error(f"Error executing tools: {str(e)}", exc_info=True)
            # Continue to next step on failure
        
        # Set current step
        state["current_step"] = "generate_response"
        
        return state
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """
        Generate a response based on the conversation and tool results.
        
        Args:
            state: Current state
            
        Returns:
            Updated state with generated response
        """
        # Create the response generation prompt
        response_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self._create_system_prompt()),
            MessagesPlaceholder(variable_name="messages"),
            SystemMessage(content="""
If any tools were called during this conversation, here are the results:
{tool_results}

If any entities were extracted, here are the entities:
{entities}

Respond to the user's message based on all the above information.
Be helpful, accurate, and professional.""")
        ])
        
        # Format tool results for the prompt
        tool_results_text = "\n".join([
            f"- {tr['tool_name']}: {tr['result']}" 
            for tr in state["tools_results"]
        ]) if state["tools_results"] else "No tools were called."
        
        # Format entities for the prompt
        entities_text = "\n".join([
            f"- {k}: {v}" 
            for k, v in state["entities"].items()
        ]) if state["entities"] else "No entities were extracted."
        
        # Create the response generation chain
        response_chain = response_prompt | self.llm
        
        try:
            # Invoke the response chain
            response = await response_chain.ainvoke({
                "messages": state["messages"],
                "tool_results": tool_results_text,
                "entities": entities_text
            })
            
            # Add the response to the message history
            state["messages"].append(response)
            
            # Set current step
            state["current_step"] = "complete"
            
            return state
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            # Add error message to history
            state["messages"].append(AIMessage(content=f"I apologize, but I encountered an issue while generating a response."))
            
            # Set current step
            state["current_step"] = "complete"
            
            return state