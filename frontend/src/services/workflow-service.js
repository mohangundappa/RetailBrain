import { fetchWithAuth } from '../utils/fetch';

/**
 * WorkflowService - Service for interacting with agent workflow APIs
 */
class WorkflowService {
  /**
   * Fetch workflow information for an agent
   * @param {string} agentId - Agent ID
   * @returns {Promise<Object>} - Workflow data or null if not found
   */
  async getWorkflowInfo(agentId) {
    try {
      const response = await fetchWithAuth(`/api/v1/agent-workflow/${agentId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to fetch workflow: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching workflow info:', error);
      throw error;
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
      const response = await fetchWithAuth(`/api/v1/workflow/${agentId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to execute workflow: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error executing workflow:', error);
      throw error;
    }
  }
}

// Create and export a singleton instance
const workflowService = new WorkflowService();
export default workflowService;