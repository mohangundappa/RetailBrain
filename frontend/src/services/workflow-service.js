/**
 * WorkflowService - Service for interacting with agent workflow APIs
 */
import { API_URL } from '../config';

class WorkflowService {
  /**
   * Fetch workflow information for an agent
   * @param {string} agentId - Agent ID
   * @returns {Promise<Object>} - Workflow data or null if not found
   */
  async getWorkflowInfo(agentId) {
    try {
      const response = await fetch(`${API_URL}/workflow-agents/info/${agentId}`);
      
      if (response.status === 404) {
        console.log(`No workflow found for agent ${agentId}`);
        return null;
      }
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching workflow for agent ${agentId}:`, error);
      return null;
    }
  }
  
  /**
   * Execute a workflow for a specific agent
   * @param {string} agentId - Agent ID
   * @param {Object} data - Request data including message and context
   * @returns {Promise<Object>} - Workflow execution response
   */
  async executeWorkflow(agentId, data) {
    try {
      const response = await fetch(`${API_URL}/workflow-agents/execute/${agentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error executing workflow for agent ${agentId}:`, error);
      throw error;
    }
  }
}

// Export as singleton
export default new WorkflowService();