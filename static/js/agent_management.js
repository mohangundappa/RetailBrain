/**
 * Agent Management JavaScript
 * 
 * This file contains the functionality for managing agents in the Staples Brain system.
 * It provides functions for loading, creating, editing, and deleting agents.
 */

// Initialize event listeners when document is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Load agents list on page load if the element exists
  if (document.getElementById('existing-agents-list')) {
    loadAgentsList();
  }

  // Set up event listeners for management actions
  setupEventListeners();
});

/**
 * Setup event listeners for agent management actions
 */
function setupEventListeners() {
  // Event listener for Create New Agent button
  const createBtn = document.getElementById('create-new-agent');
  if (createBtn) {
    createBtn.addEventListener('click', createNewAgent);
  }

  // Event delegation for dynamic content (edit, delete buttons)
  const agentsList = document.getElementById('existing-agents-list');
  if (agentsList) {
    agentsList.addEventListener('click', function(event) {
      const target = event.target;
      
      // Handle edit button click
      if (target.classList.contains('edit-agent-btn') || 
          target.closest('.edit-agent-btn')) {
        const agentId = target.closest('tr').dataset.agentId;
        loadAgent(agentId);
        event.preventDefault();
      }
      
      // Handle delete button click
      if (target.classList.contains('delete-agent-btn') || 
          target.closest('.delete-agent-btn')) {
        const row = target.closest('tr');
        const agentId = row.dataset.agentId;
        const agentName = row.querySelector('td:first-child').textContent;
        showDeleteConfirmation(agentId, agentName);
        event.preventDefault();
      }
    });
  }

  // Event listener for delete confirmation
  const confirmDeleteBtn = document.getElementById('confirm-delete-agent');
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', confirmDeleteAgent);
  }
}

/**
 * Load the list of existing agents
 */
function loadAgentsList() {
  const agentsListElement = document.getElementById('existing-agents-list');
  
  if (!agentsListElement) return;
  
  // Show loading indicator
  agentsListElement.innerHTML = `
    <tr>
      <td colspan="5" class="text-center">
        <div class="spinner-border spinner-border-sm text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        Loading agents...
      </td>
    </tr>
  `;
  
  // Fetch agents from the API
  fetch('/api/builder/agents')
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .then(agents => {
      if (agents.length === 0) {
        // No agents found
        agentsListElement.innerHTML = `
          <tr>
            <td colspan="5" class="text-center">
              No agents found. Create your first agent to get started.
            </td>
          </tr>
        `;
        return;
      }
      
      // Create table rows for each agent
      let html = '';
      agents.forEach(agent => {
        const updatedAt = agent.updated_at ? new Date(agent.updated_at).toLocaleString() : 'N/A';
        html += `
          <tr data-agent-id="${agent.id}">
            <td>${agent.name}</td>
            <td>${agent.description || 'No description'}</td>
            <td>${agent.component_count}</td>
            <td>${updatedAt}</td>
            <td>
              <div class="btn-group btn-group-sm" role="group">
                <button class="btn btn-outline-primary edit-agent-btn" title="Edit agent">
                  <i class="bi bi-pencil"></i> Edit
                </button>
                <button class="btn btn-outline-danger delete-agent-btn" title="Delete agent">
                  <i class="bi bi-trash"></i> Delete
                </button>
              </div>
            </td>
          </tr>
        `;
      });
      
      agentsListElement.innerHTML = html;
    })
    .catch(error => {
      console.error('Error loading agents:', error);
      agentsListElement.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-danger">
            <i class="bi bi-exclamation-triangle-fill"></i> 
            Error loading agents. Please try again.
          </td>
        </tr>
      `;
    });
}

/**
 * Show the delete confirmation dialog
 */
function showDeleteConfirmation(agentId, agentName) {
  // Set the agent name in the confirmation modal
  document.getElementById('delete-agent-name').textContent = agentName;
  
  // Store the agent ID as a data attribute on the confirm button
  document.getElementById('confirm-delete-agent').dataset.agentId = agentId;
  
  // Show the modal
  const deleteModal = new bootstrap.Modal(document.getElementById('deleteAgentModal'));
  deleteModal.show();
}

/**
 * Handle confirmation of agent deletion
 */
function confirmDeleteAgent() {
  const agentId = this.dataset.agentId;
  
  if (!agentId) {
    console.error('No agent ID found for deletion');
    return;
  }
  
  // Show loading state
  this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
  this.disabled = true;
  
  // Send delete request to the API
  fetch(`/api/builder/agents/${agentId}`, {
    method: 'DELETE'
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .then(data => {
      // Hide the modal
      bootstrap.Modal.getInstance(document.getElementById('deleteAgentModal')).hide();
      
      // Reload the agents list
      loadAgentsList();
      
      // Show success message
      showNotification('success', `Agent deleted successfully.`);
    })
    .catch(error => {
      console.error('Error deleting agent:', error);
      
      // Reset button state
      this.innerHTML = 'Delete Agent';
      this.disabled = false;
      
      // Show error message
      showNotification('danger', 'Error deleting agent. Please try again.');
    });
}

/**
 * Create a new agent (reset the canvas)
 */
function createNewAgent() {
  // Clear any existing agent ID from the canvas
  if (window.currentAgentId) {
    window.currentAgentId = null;
  }
  
  // Reset form fields
  document.getElementById('agent-name').value = 'New Agent';
  document.getElementById('agent-description').value = '';
  
  // Clear the canvas
  const canvas = document.getElementById('agent-canvas');
  const canvasHelp = document.getElementById('canvas-help');
  
  if (canvas) {
    // Remove all components except the help overlay
    Array.from(canvas.children).forEach(child => {
      if (child !== canvasHelp) {
        canvas.removeChild(child);
      }
    });
    
    // Show the help overlay
    if (canvasHelp) {
      canvasHelp.style.display = 'block';
    }
  }
  
  // Update canvas title
  const currentAgentName = document.getElementById('current-agent-name');
  if (currentAgentName) {
    currentAgentName.textContent = 'New Agent';
  }
  
  // Ensure the test console is hidden
  const testConsole = document.getElementById('test-console');
  if (testConsole) {
    testConsole.classList.add('d-none');
  }
  
  // Notify user
  showNotification('info', 'Started creating a new agent. Drag components to the canvas to begin.');
}

/**
 * Show a notification message
 */
function showNotification(type, message) {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
  notification.setAttribute('role', 'alert');
  notification.style.zIndex = '9999';
  
  notification.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  // Add to document
  document.body.appendChild(notification);
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    notification.classList.remove('show');
    
    // Remove from DOM after animation
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 5000);
}