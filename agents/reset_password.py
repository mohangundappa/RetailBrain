import logging
import json
import os
from typing import Dict, Any, Optional, List
import requests
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser
from agents.base_agent import BaseAgent, EntityDefinition
from config import PASSWORD_RESET_ENDPOINT

logger = logging.getLogger(__name__)

class ResetPasswordAgent(BaseAgent):
    """
    Agent responsible for handling password reset requests.
    
    This agent can handle queries about resetting passwords, account recovery,
    and other authentication-related inquiries.
    """
    
    def __init__(self, llm):
        """
        Initialize the Reset Password Agent.
        
        Args:
            llm: The language model to use for this agent
        """
        super().__init__(
            name="Reset Password Agent",
            description="I can help you reset your password, recover your account, and resolve login issues.",
            llm=llm
        )
        
        # Customize the Staples Customer Service Representative persona for password reset
        self.persona = {
            "role": "Staples Customer Service Representative",
            "style": "helpful, friendly, and professional",
            "tone": "patient, reassuring, and security-focused",
            "knowledge_areas": [
                "Staples account systems",
                "password reset procedures", 
                "account recovery protocols",
                "login troubleshooting",
                "account security best practices",
                "multiple account types (website, rewards, business)"
            ],
            "communication_preferences": [
                "clear", 
                "step-by-step",
                "security-conscious",
                "empathetic with account access frustrations"
            ]
        }
        
        # Create specialized chains
        self.classifier_chain = self._create_classifier_chain()
        self.extraction_chain = self._create_extraction_chain()
        self.instruction_chain = self._create_instruction_chain()
        
        # Setup entity collection
        self.setup_entity_definitions()
        
    def setup_entity_definitions(self) -> None:
        """
        Set up entity definitions for password reset with validation patterns and examples.
        """
        # Define email entity
        email_entity = EntityDefinition(
            name="email",
            required=True,
            validation_pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            error_message="Please provide a valid email address.",
            description="Your email address associated with your Staples account",
            examples=["johndoe@example.com", "jane.smith@company.com"],
            alternate_names=["email address", "account email", "login email"]
        )
        
        # Define account type entity (optional)
        account_type_entity = EntityDefinition(
            name="account_type",
            required=False,
            validation_pattern=r'^[a-zA-Z0-9\s]{3,50}$',
            error_message="Please provide a valid account type (e.g., Staples.com, Rewards, Business).",
            description="The type of Staples account you have",
            examples=["Staples.com", "Rewards", "Business"],
            alternate_names=["type of account", "account kind", "membership type"]
        )
        
        # Set up entity collection with these entities
        self.setup_entity_collection([email_entity, account_type_entity])
    
    def _create_classifier_chain(self) -> RunnableSequence:
        """
        Create a chain to classify if an input is related to password reset.
        
        Returns:
            A RunnableSequence that can classify inputs
        """
        template = """
        You are an AI assistant that determines if a user's query is related to password reset or account recovery.
        
        User Query: {user_input}
        
        Is this query related to resetting a password, recovering an account, login issues, or forgotten credentials? 
        Please answer with a confidence score between 0 and 1, where:
        - 0 means definitely not related to password reset or account recovery
        - 1 means definitely related to password reset or account recovery
        
        Output only the confidence score as a float between 0 and 1.
        """
        
        return self._create_chain(template, ["user_input"])
    
    def _create_extraction_chain(self) -> RunnableSequence:
        """
        Create a chain to extract account information from user input.
        
        Returns:
            A RunnableSequence that can extract account details
        """
        template = """
        You are an AI assistant that extracts account information from user queries about password reset.
        
        User Query: {user_input}
        
        Extract the following information if present:
        1. Email address
        2. Username
        3. Account type or platform (e.g., Staples.com, Staples Rewards, etc.)
        4. Any specific issue mentioned (e.g., forgot password, account locked)
        
        Return your answer as a JSON object with these fields. If information is not available, use null.
        """
        
        return self._create_chain(template, ["user_input"])
    
    def _create_instruction_chain(self) -> RunnableSequence:
        """
        Create a chain to format password reset instructions into a user-friendly response
        in the style of a Staples Customer Service Representative.
        
        Returns:
            A RunnableSequence that can format instructions
        """
        template = """
        You are a Staples Customer Service Representative specializing in account recovery and password resets.

        CUSTOMER SERVICE GUIDELINES:
        - Be helpful, friendly, and professional in all communications
        - Use a patient, reassuring, and security-focused tone
        - Express empathy and understanding for the customer's account access frustrations
        - Speak as a Staples representative using "we" when referring to Staples
        - Never mention being an AI, language model, or assistant
        - Present information in clear, step-by-step instructions
        - Prioritize account security while still being helpful
        - Be knowledgeable about Staples account systems and recovery procedures
        - Focus on resolving the customer's login issues efficiently
        - Reassure customers about the security of their accounts

        Account Information:
        {account_info}
        
        Reset Status:
        {reset_status}
        
        Customer Query:
        {user_input}
        
        Respond in a conversational, helpful manner as a Staples Customer Service Representative.
        Include clear step-by-step instructions for resetting their password.
        If there are any issues or the status indicates a problem, acknowledge that and offer specific next steps or alternatives.
        Provide reassurance about Staples' commitment to helping them regain access to their account.
        Emphasize the importance of account security while being empathetic to their situation.
        """
        
        return self._create_chain(template, ["account_info", "reset_status", "user_input"])
    
    async def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query related to password reset with a Staples customer service persona.
        Applies guardrails to ensure appropriate responses.
        
        Args:
            user_input: The user's question about password reset
            context: Additional context information
            
        Returns:
            A dictionary containing the agent's response with guardrails applied
        """
        logger.debug(f"Processing password reset request: {user_input}")
        
        try:
            # First, let the base class handle simple greetings
            parent_response = await super().process(user_input, context)
            if parent_response:
                # If the parent class returned a response (e.g., for a greeting), use it
                return parent_response
                
            # Process entity collection first
            collection_complete, follow_up_prompt = await self.process_entity_collection(user_input, context)
            
            # If we need to continue collecting entities, return a follow-up question
            if not collection_complete and follow_up_prompt:
                # Add agent_name to context to ensure we stay with this agent during entity collection
                if context and 'conversation_memory' in context:
                    memory = context['conversation_memory']
                    memory.update_working_memory('continue_with_same_agent', True)
                    memory.update_working_memory('last_selected_agent', self.name)
                
                return {
                    "response": follow_up_prompt,
                    "agent": self.name,
                    "confidence": 1.0,
                    "continue_with_same_agent": True
                }
            
            # Get collected entity values
            collected_entities = self.get_collected_entity_values()
            
            # Extract account information from user input to get any entities we didn't collect
            extraction_result = await self.extraction_chain.ainvoke({"user_input": user_input})
            
            # extraction_result is a string, not a dictionary
            try:
                account_info = json.loads(extraction_result)
            except (json.JSONDecodeError, TypeError):
                # If the result isn't valid JSON, create an empty dict
                account_info = {}
                logger.warning(f"Couldn't parse extraction result as JSON: {extraction_result}")
            
            # Update account_info with collected entities if present
            if 'email' in collected_entities:
                account_info['email'] = collected_entities['email']
            if 'account_type' in collected_entities:
                account_info['account_type'] = collected_entities['account_type']
            
            # Get reset instructions or initiate reset process
            reset_status = self._get_reset_status(account_info, context)
            
            # Format the response with customer service persona
            formatted_result = await self.instruction_chain.ainvoke({
                "account_info": json.dumps(account_info, indent=2),
                "reset_status": json.dumps(reset_status, indent=2),
                "user_input": user_input
            })
            
            # Handle different types of formatted_result (string or dict)
            if isinstance(formatted_result, dict) and "text" in formatted_result:
                formatted_response = formatted_result["text"]
            elif isinstance(formatted_result, str):
                formatted_response = formatted_result
            else:
                formatted_response = str(formatted_result)
            
            # Apply guardrails to ensure appropriate responses
            corrected_response, violations = self.apply_response_guardrails(formatted_response)
            
            # Log if any guardrail violations were detected and corrected
            if violations:
                logger.warning(f"Guardrail violations detected in password reset response: {len(violations)}")
            
            # Create response object with guardrail-corrected response
            response = {
                "agent": self.name,
                "response": corrected_response,
                "account_info": account_info,
                "reset_status": reset_status,
                "guardrail_violations": violations,
                "success": True
            }
            
            # Add to memory
            self.add_to_memory({
                "role": "assistant",
                "content": corrected_response,
                "conversation_id": context.get("conversation_id") if context else None,
                "extracted_info": {
                    "email": account_info.get("email"),
                    "username": account_info.get("username"),
                    "account_type": account_info.get("account_type"),
                    "issue": account_info.get("issue"),
                    "reset_link_sent": reset_status.get("reset_link_sent", False)
                }
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing password reset request: {str(e)}", exc_info=True)
            # Create a customer service-appropriate error message
            error_response = f"I apologize, but I'm experiencing some difficulty processing your password reset request at the moment. Could you please provide additional details about your account? Alternatively, you can reach our dedicated customer service team at 1-800-STAPLES for immediate assistance with your account access."
            
            # Apply guardrails to error message too
            corrected_error, _ = self.apply_response_guardrails(error_response)
            
            return {
                "agent": self.name,
                "response": corrected_error,
                "success": False,
                "error": str(e)
            }
    
    def can_handle(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given user input.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A confidence score between 0 and 1
        """
        try:
            # Try several methods in sequence to handle both test and production environments
            confidence = None
            
            # Method 1: Try to use the classifier chain with the newer invoke API first
            if confidence is None:
                try:
                    # Invoke the classifier chain to get a confidence score
                    result = self.classifier_chain.invoke({"user_input": user_input})
                    # Handle various result formats
                    if isinstance(result, dict) and "text" in result:
                        confidence_str = result["text"].strip()
                    elif isinstance(result, str):
                        confidence_str = result.strip()
                    else:
                        confidence_str = str(result).strip()
                    
                    confidence = float(confidence_str)
                    logger.debug(f"Method 1 (invoke) succeeded with confidence: {confidence}")
                except Exception as e:
                    logger.debug(f"Method 1 (invoke) failed: {str(e)}")
                    confidence = None
            
            # Method 2: Try direct LLM call with client.chat.completions
            if confidence is None:
                try:
                    if hasattr(self.llm, 'client') and hasattr(self.llm.client, 'chat') and hasattr(self.llm.client.chat, 'completions'):
                        # Direct prompt for test or compatibility
                        prompt = "Rate your confidence (0-1) in handling this password reset request: " + user_input
                        messages = [{"role": "user", "content": prompt}]
                        
                        # Try the completion create method (newer OpenAI client)
                        try:
                            response = self.llm.client.chat.completions.create(
                                model=getattr(self.llm, 'model_name', 'gpt-4'),
                                messages=messages
                            )
                            confidence_str = response.choices[0].message.content.strip()
                            confidence = float(confidence_str)
                            logger.debug(f"Method 2 (client.chat.completions) succeeded with confidence: {confidence}")
                        except Exception as e2:
                            logger.debug(f"Method 2 (client.chat.completions) failed: {str(e2)}")
                            confidence = None
                except Exception as e:
                    logger.debug(f"Method 2 setup failed: {str(e)}")
                    confidence = None
            
            # Method 3: Try direct LLM call for MockChatModel in tests
            if confidence is None:
                try:
                    # Direct LLM call for tests
                    if hasattr(self.llm, '_generate'):
                        test_prompt = f"Rate your confidence from 0.0 to 1.0 on handling this password reset request: '{user_input}'"
                        messages = [{"role": "user", "content": test_prompt}]
                        result = self.llm._generate(messages)
                        if hasattr(result, 'generations') and result.generations:
                            confidence_str = result.generations[0].message.content
                            confidence = float(str(confidence_str).strip())
                            logger.debug(f"Method 3 (direct LLM) succeeded with confidence: {confidence}")
                except Exception as e:
                    logger.debug(f"Method 3 (direct LLM) failed: {str(e)}")
                    confidence = None
            
            # Method 4: Fallback to a reasonable default for testing
            if confidence is None:
                # For password reset related queries, default to 0.8, otherwise 0.2
                password_terms = ['password', 'reset', 'forgot', 'login', 'account', 'sign in', 'signin', 'log in', 'recover', 'change']
                if any(term in user_input.lower() for term in password_terms):
                    confidence = 0.8
                else:
                    confidence = 0.2
                logger.debug(f"Used fallback confidence: {confidence}")
                
            logger.debug(f"Password reset confidence: {confidence} for input: {user_input}")
            return min(max(confidence, 0.0), 1.0)  # Ensure confidence is between 0 and 1
        except Exception as e:
            logger.error(f"Error determining confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def _get_reset_status(self, account_info: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get the status of a password reset request or generate instructions.
        
        Args:
            account_info: Extracted account information
            context: Additional context information
            
        Returns:
            Reset status and instructions
        """
        try:
            email = account_info.get("email")
            username = account_info.get("username")
            account_type = account_info.get("account_type")
            
            if not (email or username):
                return {
                    "status": "insufficient_info",
                    "message": "Email or username required to reset password",
                    "instructions": [
                        "Please provide either your email address or username associated with your account.",
                        "Once provided, we can send you password reset instructions."
                    ]
                }
            
            # In a real implementation, this would call an actual password reset API
            # For this example, we're simulating a response
            headers = {"Content-Type": "application/json"}
            api_key = os.environ.get("RESET_API_KEY")
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "email": email,
                "username": username,
                "account_type": account_type
            }
            
            # Make API request to password reset service
            try:
                response = requests.post(
                    PASSWORD_RESET_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"Could not connect to password reset API: {str(e)}")
                # Fallback to simulated response
                return self._generate_reset_instructions(email, username, account_type)
                
        except Exception as e:
            logger.error(f"Error getting reset status: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error initiating password reset: {str(e)}",
                "instructions": []
            }
    
    def _generate_reset_instructions(self, email: Optional[str], username: Optional[str], account_type: Optional[str]) -> Dict[str, Any]:
        """
        Generate password reset instructions for various account types.
        
        Args:
            email: User's email address
            username: User's username
            account_type: Type of account
            
        Returns:
            Reset instructions
        """
        logger.warning(f"Using simulated password reset instructions for: {email or username}")
        
        # Default Staples.com instructions
        default_instructions = [
            "Go to Staples.com and click on 'Sign In' at the top of the page.",
            "Click on 'Forgot Password' below the login form.",
            "Enter your email address associated with your account.",
            "Check your email inbox for a password reset link.",
            "Click the link and follow the instructions to create a new password.",
            "Use your new password to log in."
        ]
        
        # Customize based on account type if provided
        if account_type and "reward" in account_type.lower():
            instructions = [
                "Go to Staples.com and click on 'Staples Rewards' at the top of the page.",
                "Click on 'Sign In' and then 'Forgot Password'.",
                "Enter your email address associated with your Rewards account.",
                "Check your email inbox for a password reset link.",
                "Click the link and follow the instructions to create a new password.",
                "Use your new password to log in to your Rewards account."
            ]
        elif account_type and "business" in account_type.lower():
            instructions = [
                "Go to Staples.com/business and click on 'Sign In' at the top of the page.",
                "Click on 'Forgot Password' below the login form.",
                "Enter your business account email address.",
                "Check your email inbox for a password reset link.",
                "Click the link and follow the instructions to create a new password.",
                "Use your new password to log in to your business account."
            ]
        else:
            instructions = default_instructions
        
        # Customize message based on available information
        if email:
            message = f"Password reset instructions for your account with email: {email}"
        elif username:
            message = f"Password reset instructions for your account with username: {username}"
        else:
            message = "General password reset instructions"
        
        return {
            "status": "instructions_provided",
            "message": message,
            "instructions": instructions,
            "reset_link_sent": False,
            "is_simulated": True
        }
