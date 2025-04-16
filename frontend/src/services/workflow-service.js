/**
 * WorkflowService - Service for interacting with agent workflow APIs
 */
import { API_BASE_URL } from '../config';

class WorkflowService {
  /**
   * Fetch workflow information for an agent
   * @param {string} agentId - Agent ID
   * @returns {Promise<Object>} - Workflow data or null if not found
   */
  async getWorkflowInfo(agentId) {
    try {
      const response = await fetch(`${API_BASE_URL}/agent-workflow/${agentId}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          console.log(`No workflow found for agent ${agentId}`);
          return null;
        }
        throw new Error(`Error fetching workflow info: ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching workflow info:', error);
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
      const response = await fetch(`${API_BASE_URL}/workflow/${agentId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error(`Error executing workflow: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error executing workflow:', error);
      throw error;
    }
  }
}

export default new WorkflowService();