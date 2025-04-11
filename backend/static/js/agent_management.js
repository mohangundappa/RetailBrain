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
        // Redirect to the agent builder page with the agent ID
        window.location.href = `/agent-builder?id=${agentId}`;
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
      
      // Handle view button click for built-in agents
      if (target.classList.contains('view-agent-btn') || 
          target.closest('.view-agent-btn')) {
        const row = target.closest('tr');
        const agentId = row.dataset.agentId;
        const agentName = row.querySelector('td:first-child').textContent.trim();
        
        // Create modal to show built-in agent details
        const modalHtml = `
          <div class="modal fade" id="viewBuiltinAgentModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title">${agentName.replace('<span class="badge bg-secondary ms-2">Built-in</span>', '')}</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                  <div class="alert alert-info">
                    <i class="bi bi-info-circle-fill me-2"></i>
                    This is a built-in agent that is defined in the code and cannot be edited through the Agent Builder interface.
                  </div>
                  <p>Built-in agents are specialized for specific tasks and are directly integrated with the Staples Brain architecture.</p>
                  <p>To implement custom agent functionality, create a new agent using the Agent Builder.</p>
                </div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
              </div>
            </div>
          </div>
        `;
        
        // Add modal to document if it doesn't exist
        if (!document.getElementById('viewBuiltinAgentModal')) {
          document.body.insertAdjacentHTML('beforeend', modalHtml);
        } else {
          document.getElementById('viewBuiltinAgentModal').outerHTML = modalHtml;
        }
        
        // Show the modal
        const builtinModal = new bootstrap.Modal(document.getElementById('viewBuiltinAgentModal'));
        builtinModal.show();
        
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
        const isCustom = agent.is_custom !== false;  // Default to true if not specified
        const canEdit = agent.can_edit !== false;    // Default to true if not specified
        
        html += `
          <tr data-agent-id="${agent.id}" class="${isCustom ? 'custom-agent' : 'builtin-agent'}">
            <td>
              ${agent.name}
              ${!isCustom ? '<span class="badge bg-secondary ms-2">Built-in</span>' : ''}
            </td>
            <td>${agent.description || 'No description'}</td>
            <td>${isCustom ? agent.component_count : '<i>Native</i>'}</td>
            <td>${updatedAt}</td>
            <td>
              <div class="btn-group btn-group-sm" role="group">
                ${canEdit ? `
                  <button class="btn btn-outline-primary edit-agent-btn" title="Edit agent">
                    <i class="bi bi-pencil"></i> Edit
                  </button>
                  <button class="btn btn-outline-danger delete-agent-btn" title="Delete agent">
                    <i class="bi bi-trash"></i> Delete
                  </button>
                ` : `
                  <button class="btn btn-outline-secondary view-agent-btn" title="View agent details">
                    <i class="bi bi-eye"></i> View
                  </button>
                `}
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
 * Create a new agent (redirect to builder page)
 */
function createNewAgent() {
  // Redirect to the agent builder page without an ID
  window.location.href = '/agent-builder';
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