import logging
import os
import time
import json
import requests
from typing import Dict, Any, List, Optional
from config import DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_CLUSTER_ID

logger = logging.getLogger(__name__)

class DatabricksConnector:
    """
    Utility class to interact with Databricks.
    
    This class provides methods to execute code on Databricks, retrieve data,
    and manage LLM models deployed on Databricks.
    """
    
    def __init__(self):
        """Initialize the Databricks connector."""
        self.host = DATABRICKS_HOST
        self.token = DATABRICKS_TOKEN
        self.cluster_id = DATABRICKS_CLUSTER_ID
        
        if not self.host or not self.token:
            logger.warning("Databricks host or token not provided. Some functionality will be limited.")
    
    def is_configured(self) -> bool:
        """
        Check if the Databricks connector is properly configured.
        
        Returns:
            True if configured, False otherwise
        """
        return bool(self.host and self.token and self.cluster_id)
    
    def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Execute code on a Databricks cluster.
        
        Args:
            code: The code to execute
            language: The language of the code (python, scala, sql, r)
            
        Returns:
            Response from the execution
        """
        if not self.is_configured():
            logger.error("Databricks connector not configured")
            return {
                "status": "error",
                "message": "Databricks connector not configured"
            }
        
        try:
            # Create command
            command = {
                "language": language,
                "clusterId": self.cluster_id,
                "content": code
            }
            
            # Execute command
            response = self._post_request(
                f"{self.host}/api/2.0/commands/execute",
                data=json.dumps(command)
            )
            
            if not response or "id" not in response:
                logger.error(f"Failed to execute code: {response}")
                return {
                    "status": "error",
                    "message": f"Failed to execute code: {response}"
                }
            
            # Get command results
            command_id = response["id"]
            status = "running"
            result = None
            
            while status == "running":
                time.sleep(1)
                result = self._get_request(f"{self.host}/api/2.0/commands/status?clusterId={self.cluster_id}&commandId={command_id}")
                status = result.get("status", "error")
            
            return {
                "status": status,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing code on Databricks: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error executing code: {str(e)}"
            }
    
    def query_data(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SQL query on Databricks and retrieve results.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            Query results
        """
        return self.execute_code(sql_query, language="sql")
    
    def load_model(self, model_name: str) -> Dict[str, Any]:
        """
        Load a machine learning model from Databricks.
        
        Args:
            model_name: The name of the model to load
            
        Returns:
            Information about the loaded model
        """
        code = f"""
        from mlflow.store.artifact.models_artifact_repo import ModelsArtifactRepository
        import mlflow

        model = mlflow.pyfunc.load_model("models:/{model_name}/latest")
        print(f"Loaded model: {model_name}")
        """
        
        return self.execute_code(code)
    
    def create_langchain_agent(self, agent_code: str) -> Dict[str, Any]:
        """
        Create and initialize a LangChain agent on Databricks.
        
        Args:
            agent_code: The agent definition code
            
        Returns:
            Information about the created agent
        """
        setup_code = """
        import os
        import json
        from langchain.llms import OpenAI
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        from langchain.agents import Tool, initialize_agent, AgentType
        """
        
        full_code = f"{setup_code}\n\n{agent_code}\n\nprint('Agent initialized successfully')"
        
        return self.execute_code(full_code)
    
    def _get_request(self, url: str) -> Dict[str, Any]:
        """
        Send a GET request to Databricks API.
        
        Args:
            url: The API URL
            
        Returns:
            API response
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code >= 400:
            logger.error(f"Databricks API error: {response.status_code}, {response.text}")
            return {"error": response.text}
        
        return response.json()
    
    def _post_request(self, url: str, data: str) -> Dict[str, Any]:
        """
        Send a POST request to Databricks API.
        
        Args:
            url: The API URL
            data: The request data
            
        Returns:
            API response
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, data=data)
        if response.status_code >= 400:
            logger.error(f"Databricks API error: {response.status_code}, {response.text}")
            return {"error": response.text}
        
        return response.json()
