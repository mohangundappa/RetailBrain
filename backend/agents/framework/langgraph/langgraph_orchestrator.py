"""
LangGraph-based orchestrator for Staples Brain.

This module provides a LangGraph-based orchestration mechanism for routing requests
to the appropriate agent based on detected intents.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent

logger = logging.getLogger(__name__)


class LangGraphOrchestrator:
    """
    Orchestrator for LangGraph agents.
    
    This class routes user requests to the appropriate agent based on detected intents,
    maintaining conversation continuity and context awareness.
    """
    
    def __init__(self, agents: Optional[List[LangGraphAgent]] = None, llm: Optional[ChatOpenAI] = None):
        """
        Initialize the orchestrator with optional agents and LLM.
        
        Args:
            agents: List of agent instances to coordinate
            llm: Language model for intent detection and other orchestration tasks
        """
        self.agents = agents or []
        
        # Set default LLM if not provided
        self.llm = llm or ChatOpenAI(
            model="gpt-4o",
            temperature=0.2  # Lower temperature for more deterministic routing
        )
        
        # Track conversation history by session
        self.session_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Track last agent used by session
        self.last_agent: Dict[str, str] = {}
        
        logger.info(f"Initialized LangGraph orchestrator with {len(self.agents)} agents")
    
    def list_agents(self) -> List[str]:
        """
        List all registered agents.
        
        Returns:
            List of agent names
        """
        return [agent.name for agent in self.agents]
    
    def register_agent(self, agent: LangGraphAgent) -> bool:
        """
        Register a new agent with the orchestrator.
        
        Args:
            agent: The agent instance to register
            
        Returns:
            True if registration was successful, False if agent was already registered
        """
        # Check if agent is already registered
        for existing_agent in self.agents:
            if existing_agent.name == agent.name:
                return False
        
        # Add agent to the list
        self.agents.append(agent)
        logger.info(f"Registered agent {agent.name} with orchestrator")
        return True
    
    async def process_message(self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a message and route to the appropriate agent.
        
        Args:
            message: User's message text
            session_id: Session identifier
            context: Additional context for processing
            
        Returns:
            Response with agent output
        """
        logger.info(f"TRACE: Entered LangGraphOrchestrator.process_message in backend/brain/agents/langgraph_orchestrator.py")
        if not self.agents:
            return {
                "response": "No agents are available to process your request.",
                "agent": "orchestrator",
                "confidence": 0.0
            }
        
        # Initialize context if not provided
        context = context or {}
        
        # Initialize session history if not exists
        if session_id not in self.session_history:
            self.session_history[session_id] = []
        
        # Add message to session history
        self.session_history[session_id].append({
            "role": "user",
            "content": message
        })
        
        # Detect special cases (greetings, goodbyes, etc.)
        special_case, confidence, response = await self._check_special_cases(message)
        if special_case and response:
            # Add response to session history
            self.session_history[session_id].append({
                "role": "assistant",
                "content": response,
                "agent": "orchestrator"
            })
            
            return {
                "response": response,
                "agent": "orchestrator",
                "confidence": confidence
            }
        
        # Select the appropriate agent
        selected_agent, confidence, context_used = await self._select_agent(message, {
            "session_id": session_id,
            "history": self.session_history.get(session_id, []),
            "last_agent": self.last_agent.get(session_id),
            **context
        })
        
        if not selected_agent:
            # No agent could handle this request
            fallback_response = "I'm sorry, I'm not sure how to help with that request. Could you please provide more details or try asking in a different way?"
            
            # Add fallback response to session history
            self.session_history[session_id].append({
                "role": "assistant",
                "content": fallback_response,
                "agent": "orchestrator"
            })
            
            return {
                "response": fallback_response,
                "agent": "orchestrator",
                "confidence": 0.0
            }
        
        # Process the message with the selected agent
        try:
            agent_response = await selected_agent.process_message(
                message, 
                session_id,
                context=context_used
            )
            
            # Update last agent
            self.last_agent[session_id] = selected_agent.name
            
            # Add response to session history
            self.session_history[session_id].append({
                "role": "assistant",
                "content": agent_response["response"],
                "agent": selected_agent.name
            })
            
            # Add confidence from selection process
            agent_response["confidence"] = confidence
            
            return agent_response
        except Exception as e:
            logger.error(f"Error processing message with agent {selected_agent.name}: {str(e)}", exc_info=True)
            error_response = f"I encountered an issue while processing your request. Please try again."
            
            # Add error response to session history
            self.session_history[session_id].append({
                "role": "assistant",
                "content": error_response,
                "agent": "orchestrator"
            })
            
            return {
                "response": error_response,
                "agent": "orchestrator",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _check_special_cases(self, message: str) -> Tuple[Optional[str], float, Optional[str]]:
        """
        Check for special case scenarios like greetings, conversation ends, and human transfer requests.
        
        Args:
            message: The user's message
            
        Returns:
            Tuple of (special_case_type, confidence, response)
        """
        # Define special case detection prompt
        special_case_prompt = PromptTemplate.from_template("""
Analyze the user message and determine if it falls into one of these special categories:
1. greeting - A simple greeting or introduction (e.g., "hello", "hi there")
2. goodbye - Ending the conversation (e.g., "bye", "thanks, that's all")
3. human_request - Explicitly asking for a human agent (e.g., "can I speak to a person")
4. none - Not a special case

User message: {message}

First categorize the message as one of: greeting, goodbye, human_request, or none.
Then provide a confidence score between 0.0 and 1.0 for your categorization.
For greetings and goodbyes, also provide an appropriate response.

Output as JSON with these fields:
- category: the category name
- confidence: a number between 0.0 and 1.0
- response: an appropriate response if category is greeting or goodbye, otherwise null

JSON Output:
""")
        
        # Create and invoke the chain
        special_case_chain = special_case_prompt | self.llm | StrOutputParser()
        
        try:
            result = await special_case_chain.ainvoke({"message": message})
            
            # Parse the result as JSON
            special_case_data = json.loads(result)
            
            category = special_case_data.get("category", "none")
            confidence = float(special_case_data.get("confidence", 0.0))
            response = special_case_data.get("response")
            
            if category != "none" and confidence > 0.7:
                return category, confidence, response
            
            return None, 0.0, None
        except Exception as e:
            logger.error(f"Error checking special cases: {str(e)}", exc_info=True)
            return None, 0.0, None
    
    async def _select_agent(self, message: str, context: Dict[str, Any]) -> Tuple[Optional[LangGraphAgent], float, Dict[str, Any]]:
        """
        Select the most appropriate agent for the user input.
        
        Args:
            message: The user's message
            context: Context information, including session_id and history
            
        Returns:
            Tuple of (selected_agent, confidence_score, context_used)
        """
        if not self.agents:
            return None, 0.0, {}
        
        # Check for conversation continuity
        last_agent_name = context.get("last_agent")
        history = context.get("history", [])
        
        # If we have a last agent and recent history, check if we should continue with the same agent
        if last_agent_name and len(history) >= 2:
            # Define continuity detection prompt
            continuity_prompt = PromptTemplate.from_template("""
Consider this conversation history:

{history}

Current user message: {message}

The previous message was handled by the agent: {last_agent}

Determine if the current message is continuing the same conversation topic that the previous agent was handling.
Output a JSON object with:
- continue_with_same_agent: boolean (true if the conversation is continuing, false if it's a new topic)
- confidence: number between 0.0 and 1.0
- reasoning: brief explanation of your decision

JSON Output:
""")
            
            # Format history for the prompt
            formatted_history = "\n".join([
                f"{entry['role'].upper()}: {entry['content']}"
                for entry in history[-4:]  # Use last 4 messages for context
            ])
            
            # Create and invoke the chain
            continuity_chain = continuity_prompt | self.llm | StrOutputParser()
            
            try:
                result = await continuity_chain.ainvoke({
                    "history": formatted_history,
                    "message": message,
                    "last_agent": last_agent_name
                })
                
                # Parse the result as JSON
                continuity_data = json.loads(result)
                
                if continuity_data.get("continue_with_same_agent", False):
                    continuity_confidence = float(continuity_data.get("confidence", 0.0))
                    
                    if continuity_confidence > 0.6:
                        # Find the last agent
                        for agent in self.agents:
                            if agent.name == last_agent_name:
                                context_used = {**context}
                                return agent, continuity_confidence, context_used
            except Exception as e:
                logger.error(f"Error checking conversation continuity: {str(e)}", exc_info=True)
                # Continue with agent selection
        
        # Perform intent detection to choose the best agent
        agent_scores: List[Tuple[LangGraphAgent, float]] = []
        
        # Define agent selection prompt
        agent_selection_prompt = PromptTemplate.from_template("""
I need to route a user request to the right specialized agent.

User message: {message}

Available agents:
{agent_descriptions}

For each agent, provide a relevance score between 0.0 and 1.0 indicating how well the agent matches the user's request.
0.0 means completely irrelevant, 1.0 means perfect match.

Output as a JSON object with agent names as keys and scores as values.
Sort in descending order of scores.

JSON Output:
""")
        
        # Format agent descriptions for the prompt
        agent_descriptions = "\n".join([
            f"- {agent.name}: {agent.description}"
            for agent in self.agents
        ])
        
        # Create and invoke the chain
        agent_selection_chain = agent_selection_prompt | self.llm | StrOutputParser()
        
        try:
            result = await agent_selection_chain.ainvoke({
                "message": message,
                "agent_descriptions": agent_descriptions
            })
            
            # Parse the result as JSON
            scores = json.loads(result)
            
            # Find the best scoring agent
            best_agent = None
            best_score = 0.0
            for agent in self.agents:
                score = scores.get(agent.name, 0.0)
                if score > best_score:
                    best_agent = agent
                    best_score = score
            
            if best_agent and best_score > 0.5:  # Require a minimum confidence
                context_used = {**context}
                return best_agent, best_score, context_used
            
        except Exception as e:
            logger.error(f"Error selecting agent: {str(e)}", exc_info=True)
        
        # If no agent was selected or an error occurred, return the first agent with low confidence
        if self.agents:
            return self.agents[0], 0.3, {**context}
        
        return None, 0.0, {}