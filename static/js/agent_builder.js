/**
 * Agent Builder JavaScript
 * 
 * This file handles the drag-and-drop interface for creating custom agents.
 * It uses jsPlumb for connection management.
 */

// Global variables
let jsPlumbInstance;
let selectedComponent = null;
let currentAgent = {
  id: null,
  name: 'New Agent',
  description: '',
  components: [],
  connections: []
};
let nextComponentId = 1;
let connectingFrom = null;

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
  // Initialize jsPlumb
  jsPlumbInstance = jsPlumb.getInstance({
    Container: 'agent-canvas',
    ConnectionsDetachable: true,
    Connector: ['Bezier', { curviness: 60 }],
    Endpoint: ['Dot', { radius: 5 }],
    PaintStyle: { stroke: '#6c757d', strokeWidth: 2 },
    HoverPaintStyle: { stroke: '#007bff', strokeWidth: 3 },
    EndpointStyle: { fill: '#6c757d', stroke: '#6c757d' },
    EndpointHoverStyle: { fill: '#007bff' },
    ConnectionOverlays: [
      ['Arrow', { location: 1, width: 10, length: 10 }]
    ]
  });
  
  initDragAndDrop();
  initEventListeners();
  
  // Get agent ID from URL if editing existing agent
  const urlParams = new URLSearchParams(window.location.search);
  const agentId = urlParams.get('id');
  
  if (agentId) {
    loadAgent(agentId);
  }
});

/**
 * Initialize drag and drop functionality
 */
function initDragAndDrop() {
  // Make palette components draggable
  const draggableComponents = document.querySelectorAll('.draggable-component');
  draggableComponents.forEach(component => {
    component.setAttribute('draggable', true);
    
    component.addEventListener('dragstart', function(event) {
      event.dataTransfer.setData('componentType', component.dataset.componentType);
      event.dataTransfer.setData('componentTemplate', component.dataset.componentTemplate);
    });
  });
  
  // Make canvas a drop target
  const canvas = document.getElementById('agent-canvas');
  
  canvas.addEventListener('dragover', function(event) {
    event.preventDefault(); // Allow dropping
  });
  
  canvas.addEventListener('drop', function(event) {
    event.preventDefault();
    
    const componentType = event.dataTransfer.getData('componentType');
    const componentTemplate = event.dataTransfer.getData('componentTemplate');
    
    if (componentType && componentTemplate) {
      // Calculate position relative to canvas
      const canvasRect = canvas.getBoundingClientRect();
      const x = event.clientX - canvasRect.left;
      const y = event.clientY - canvasRect.top;
      
      // Add component to canvas
      addComponentToCanvas(componentType, componentTemplate, x, y);
    }
  });
}

/**
 * Initialize event listeners
 */
function initEventListeners() {
  // Save agent button
  document.getElementById('save-agent').addEventListener('click', saveAgent);
  
  // Test agent button
  document.getElementById('test-agent').addEventListener('click', function() {
    const testConsole = document.getElementById('test-console');
    testConsole.classList.toggle('d-none');
  });
  
  // Run test button
  document.getElementById('run-test').addEventListener('click', testAgent);
  
  // Agent name input
  document.getElementById('agent-name').addEventListener('input', function(event) {
    currentAgent.name = event.target.value;
    document.getElementById('current-agent-name').textContent = currentAgent.name;
  });
  
  // Agent description input
  document.getElementById('agent-description').addEventListener('input', function(event) {
    currentAgent.description = event.target.value;
  });
  
  // Save connection button
  document.getElementById('save-connection').addEventListener('click', saveConnection);
  
  // Initialize temperature sliders
  document.querySelector('input[data-config-key="temperature"]').addEventListener('input', function(event) {
    document.getElementById('temperature-value').textContent = event.target.value;
  });
  
  // Canvas click event to deselect components
  document.getElementById('agent-canvas').addEventListener('click', function(event) {
    if (event.target.id === 'agent-canvas') {
      deselectComponent();
    }
  });
}

/**
 * Add a component to the canvas
 */
function addComponentToCanvas(componentType, templateName, x, y) {
  const componentId = `component-${nextComponentId++}`;
  
  // Create component DOM element
  const componentElement = document.createElement('div');
  componentElement.id = componentId;
  componentElement.className = 'canvas-component';
  componentElement.dataset.componentType = componentType;
  componentElement.dataset.componentTemplate = templateName;
  componentElement.style.left = `${x}px`;
  componentElement.style.top = `${y}px`;
  
  // Format the component name for display
  const displayName = formatTemplateName(templateName);
  
  // Component content
  componentElement.innerHTML = `
    <div class="component-header">
      <div class="component-title">${displayName}</div>
      <div class="component-actions">
        <button class="btn btn-sm btn-link p-0 text-danger delete-component" title="Delete component">
          <i class="bi bi-x"></i>
        </button>
      </div>
    </div>
    <div class="component-body">
      <div class="component-type">${componentType}</div>
    </div>
    <div class="input-point connection-point" data-point-type="input"></div>
    <div class="output-point connection-point" data-point-type="output"></div>
  `;
  
  document.getElementById('agent-canvas').appendChild(componentElement);
  
  // Make the component draggable with jsPlumb
  jsPlumbInstance.draggable(componentId, {
    containment: 'parent',
    stop: function(event) {
      // Update component position in the currentAgent object
      const componentIndex = currentAgent.components.findIndex(comp => comp.id === componentId);
      if (componentIndex !== -1) {
        currentAgent.components[componentIndex].position_x = parseInt(componentElement.style.left);
        currentAgent.components[componentIndex].position_y = parseInt(componentElement.style.top);
      }
    }
  });
  
  // Add connection endpoints
  if (componentType !== 'output') { // Only add output endpoint if not an output component
    jsPlumbInstance.addEndpoint(componentId, {
      anchor: 'Bottom',
      isSource: true,
      maxConnections: -1, // Unlimited connections
      endpoint: 'Dot',
      uniqueEndpoint: false
    });
  }
  
  if (componentType !== 'prompt') { // Only add input endpoint if not a prompt component
    jsPlumbInstance.addEndpoint(componentId, {
      anchor: 'Top',
      isTarget: true,
      maxConnections: -1, // Unlimited connections
      endpoint: 'Dot',
      uniqueEndpoint: false
    });
  }
  
  // Add component to current agent object
  currentAgent.components.push({
    id: componentId,
    component_type: componentType,
    name: displayName,
    template: templateName,
    position_x: x,
    position_y: y,
    configuration: getDefaultConfiguration(templateName)
  });
  
  // Add click event handler for component selection
  componentElement.addEventListener('click', function(event) {
    event.stopPropagation();
    if (!event.target.classList.contains('delete-component')) {
      selectComponent(componentId);
    }
  });
  
  // Add click handler for delete button
  componentElement.querySelector('.delete-component').addEventListener('click', function(event) {
    event.stopPropagation();
    deleteComponent(componentId);
  });
  
  // Add connection points click handlers
  componentElement.querySelectorAll('.connection-point').forEach(point => {
    point.addEventListener('click', function(event) {
      event.stopPropagation();
      handleConnectionPoint(componentId, point.dataset.pointType);
    });
  });
  
  // Select the newly added component
  selectComponent(componentId);
}

/**
 * Format template name for display
 */
function formatTemplateName(templateName) {
  return templateName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get default configuration for a component template
 */
function getDefaultConfiguration(templateName) {
  switch (templateName) {
    case 'intent_classifier':
      return {
        available_intents: 'package_tracking, order_status, password_reset, store_locator, product_info',
        system_prompt: 'You are an intent classifier. Identify the user\'s intent based on their query.',
        temperature: 0.3
      };
    case 'entity_extractor':
      return {
        entity_types: 'tracking_number, email, location, product_name',
        extraction_prompt: 'Extract the following entities from the user query based on the identified intent.'
      };
    case 'openai_gpt4':
      return {
        model_name: 'gpt-4o',
        temperature: 0.3,
        max_tokens: 1000
      };
    case 'json_formatter':
      return {
        schema: '{\n  "response": "string",\n  "confidence": "number"\n}',
        enforce_schema: true
      };
    default:
      return {};
  }
}

/**
 * Select a component and show its properties
 */
function selectComponent(componentId) {
  // Deselect previously selected component
  if (selectedComponent) {
    document.getElementById(selectedComponent).classList.remove('component-selected');
  }
  
  // Mark new component as selected
  selectedComponent = componentId;
  document.getElementById(componentId).classList.add('component-selected');
  
  // Show component properties
  document.getElementById('agent-properties').classList.add('d-none');
  
  const componentProperties = document.getElementById('component-properties');
  componentProperties.classList.remove('d-none');
  
  // Find component in currentAgent
  const component = currentAgent.components.find(comp => comp.id === componentId);
  
  // Load template for this component type
  const templateId = `template-${component.template}`;
  const template = document.getElementById(templateId);
  
  if (template) {
    // Clone the template content
    const propertiesHTML = template.cloneNode(true);
    propertiesHTML.id = 'current-properties';
    
    // Clear previous properties
    componentProperties.innerHTML = '';
    componentProperties.appendChild(propertiesHTML);
    
    // Set values from component configuration
    const configFields = componentProperties.querySelectorAll('.component-config');
    configFields.forEach(field => {
      const configKey = field.dataset.configKey;
      if (component.configuration && component.configuration[configKey] !== undefined) {
        if (field.type === 'checkbox') {
          field.checked = component.configuration[configKey];
        } else {
          field.value = component.configuration[configKey];
        }
      }
      
      // Add event listener to update configuration when changed
      field.addEventListener('change', function(event) {
        const value = field.type === 'checkbox' ? field.checked : field.value;
        const componentIndex = currentAgent.components.findIndex(comp => comp.id === selectedComponent);
        
        if (componentIndex !== -1) {
          if (!currentAgent.components[componentIndex].configuration) {
            currentAgent.components[componentIndex].configuration = {};
          }
          currentAgent.components[componentIndex].configuration[configKey] = value;
        }
      });
    });
    
    // Special handling for sliders to update displayed value
    const temperatureSlider = componentProperties.querySelector('input[data-config-key="temperature"]');
    if (temperatureSlider) {
      const valueDisplay = temperatureSlider.parentElement.querySelector('small:nth-child(2)');
      if (valueDisplay) {
        valueDisplay.textContent = temperatureSlider.value;
      }
      
      temperatureSlider.addEventListener('input', function(event) {
        if (valueDisplay) {
          valueDisplay.textContent = event.target.value;
        }
      });
    }
  } else {
    componentProperties.innerHTML = `
      <div class="text-center text-muted p-4">
        No properties available for this component type
      </div>
    `;
  }
}

/**
 * Deselect the currently selected component
 */
function deselectComponent() {
  if (selectedComponent) {
    document.getElementById(selectedComponent).classList.remove('component-selected');
    selectedComponent = null;
    
    // Show agent properties, hide component properties
    document.getElementById('agent-properties').classList.remove('d-none');
    document.getElementById('component-properties').classList.add('d-none');
  }
  
  // Reset connecting state
  if (connectingFrom) {
    const elem = document.getElementById(connectingFrom);
    if (elem) {
      elem.querySelector(`.connection-point[data-point-type="${connectingPointType}"]`).classList.remove('connecting');
    }
    connectingFrom = null;
    connectingPointType = null;
  }
}

/**
 * Delete a component from the canvas
 */
function deleteComponent(componentId) {
  // Remove all connections to/from this component
  jsPlumbInstance.remove(componentId);
  
  // Remove from currentAgent.components
  currentAgent.components = currentAgent.components.filter(comp => comp.id !== componentId);
  
  // Remove from currentAgent.connections
  currentAgent.connections = currentAgent.connections.filter(conn => 
    conn.source_id !== componentId && conn.target_id !== componentId);
  
  // If this was the selected component, deselect it
  if (selectedComponent === componentId) {
    deselectComponent();
  }
}

let connectingPointType = null;

/**
 * Handle clicks on connection points
 */
function handleConnectionPoint(componentId, pointType) {
  if (connectingFrom === null) {
    // Start connecting
    connectingFrom = componentId;
    connectingPointType = pointType;
    document.getElementById(componentId)
      .querySelector(`.connection-point[data-point-type="${pointType}"]`)
      .classList.add('connecting');
  } else {
    // Complete connection if valid
    if (connectingFrom !== componentId && connectingPointType !== pointType) {
      // Determine source and target based on point types
      let sourceId, targetId;
      
      if (connectingPointType === 'output') {
        sourceId = connectingFrom;
        targetId = componentId;
      } else {
        sourceId = componentId;
        targetId = connectingFrom;
      }
      
      // Show connection config modal
      const modal = new bootstrap.Modal(document.getElementById('connection-modal'));
      modal.show();
      
      // Store the connection info for when the modal is submitted
      document.getElementById('connection-modal').dataset.sourceId = sourceId;
      document.getElementById('connection-modal').dataset.targetId = targetId;
    }
    
    // Remove connecting class
    document.getElementById(connectingFrom)
      .querySelector(`.connection-point[data-point-type="${connectingPointType}"]`)
      .classList.remove('connecting');
    
    // Reset connecting state
    connectingFrom = null;
    connectingPointType = null;
  }
}

/**
 * Save a connection after modal confirmation
 */
function saveConnection() {
  const modal = document.getElementById('connection-modal');
  const sourceId = modal.dataset.sourceId;
  const targetId = modal.dataset.targetId;
  const connectionType = document.getElementById('connection-type').value;
  const description = document.getElementById('connection-description').value;
  
  // Create a connection with jsPlumb
  jsPlumbInstance.connect({
    source: sourceId,
    target: targetId,
    anchors: ["Bottom", "Top"],
    overlays: [
      ["Label", { 
        label: connectionType, 
        location: 0.5,
        cssClass: "connection-label" 
      }]
    ]
  });
  
  // Add to current agent connections
  const connectionId = `connection-${Date.now()}`;
  currentAgent.connections.push({
    id: connectionId,
    source_id: sourceId,
    target_id: targetId,
    connection_type: connectionType,
    description: description
  });
  
  // Close the modal
  bootstrap.Modal.getInstance(modal).hide();
  
  // Reset the form
  document.getElementById('connection-form').reset();
}

/**
 * Save the current agent
 */
function saveAgent() {
  // Update agent name and description from form
  currentAgent.name = document.getElementById('agent-name').value || 'New Agent';
  currentAgent.description = document.getElementById('agent-description').value || '';
  
  // Validate the agent
  if (currentAgent.components.length === 0) {
    alert('Your agent needs at least one component');
    return;
  }
  
  // Send to server
  fetch('/api/builder/agents', {
    method: currentAgent.id ? 'PUT' : 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(currentAgent)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to save agent');
    }
    return response.json();
  })
  .then(data => {
    // Update current agent with server-assigned ID if new
    if (!currentAgent.id) {
      currentAgent.id = data.id;
      // Update URL to include the agent ID
      history.pushState(null, '', `/agent-builder?id=${data.id}`);
    }
    
    alert('Agent saved successfully!');
  })
  .catch(error => {
    console.error('Error saving agent:', error);
    alert('Error saving agent: ' + error.message);
  });
}

/**
 * Load an existing agent
 */
function loadAgent(agentId) {
  fetch(`/api/builder/agents/${agentId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Agent not found');
      }
      return response.json();
    })
    .then(data => {
      // Clear the canvas
      jsPlumbInstance.reset();
      document.getElementById('agent-canvas').innerHTML = '';
      
      // Set agent data
      currentAgent = data;
      
      // Update form fields
      document.getElementById('agent-name').value = data.name;
      document.getElementById('agent-description').value = data.description || '';
      document.getElementById('current-agent-name').textContent = data.name;
      
      // Add components to canvas
      data.components.forEach(component => {
        const componentElement = document.createElement('div');
        const componentId = component.id;
        
        componentElement.id = componentId;
        componentElement.className = 'canvas-component';
        componentElement.dataset.componentType = component.component_type;
        componentElement.dataset.componentTemplate = component.template;
        componentElement.style.left = `${component.position_x}px`;
        componentElement.style.top = `${component.position_y}px`;
        
        componentElement.innerHTML = `
          <div class="component-header">
            <div class="component-title">${component.name}</div>
            <div class="component-actions">
              <button class="btn btn-sm btn-link p-0 text-danger delete-component" title="Delete component">
                <i class="bi bi-x"></i>
              </button>
            </div>
          </div>
          <div class="component-body">
            <div class="component-type">${component.component_type}</div>
          </div>
          <div class="input-point connection-point" data-point-type="input"></div>
          <div class="output-point connection-point" data-point-type="output"></div>
        `;
        
        document.getElementById('agent-canvas').appendChild(componentElement);
        
        // Make component draggable
        jsPlumbInstance.draggable(componentId, {
          containment: 'parent',
          stop: function(event) {
            const componentIndex = currentAgent.components.findIndex(comp => comp.id === componentId);
            if (componentIndex !== -1) {
              currentAgent.components[componentIndex].position_x = parseInt(componentElement.style.left);
              currentAgent.components[componentIndex].position_y = parseInt(componentElement.style.top);
            }
          }
        });
        
        // Add endpoints
        if (component.component_type !== 'output') {
          jsPlumbInstance.addEndpoint(componentId, {
            anchor: 'Bottom',
            isSource: true,
            maxConnections: -1,
            endpoint: 'Dot',
            uniqueEndpoint: false
          });
        }
        
        if (component.component_type !== 'prompt') {
          jsPlumbInstance.addEndpoint(componentId, {
            anchor: 'Top',
            isTarget: true,
            maxConnections: -1,
            endpoint: 'Dot',
            uniqueEndpoint: false
          });
        }
        
        // Add event handlers
        componentElement.addEventListener('click', function(event) {
          event.stopPropagation();
          if (!event.target.classList.contains('delete-component')) {
            selectComponent(componentId);
          }
        });
        
        componentElement.querySelector('.delete-component').addEventListener('click', function(event) {
          event.stopPropagation();
          deleteComponent(componentId);
        });
        
        componentElement.querySelectorAll('.connection-point').forEach(point => {
          point.addEventListener('click', function(event) {
            event.stopPropagation();
            handleConnectionPoint(componentId, point.dataset.pointType);
          });
        });
      });
      
      // Add connections
      data.connections.forEach(connection => {
        jsPlumbInstance.connect({
          source: connection.source_id,
          target: connection.target_id,
          anchors: ["Bottom", "Top"],
          overlays: [
            ["Label", { 
              label: connection.connection_type, 
              location: 0.5,
              cssClass: "connection-label" 
            }]
          ]
        });
      });
      
      // Set next component ID to avoid conflicts
      nextComponentId = Math.max(...data.components.map(comp => {
        const idNum = parseInt(comp.id.split('-')[1]);
        return isNaN(idNum) ? 1 : idNum;
      }), 0) + 1;
    })
    .catch(error => {
      console.error('Error loading agent:', error);
      alert('Error loading agent: ' + error.message);
    });
}

/**
 * Test the current agent
 */
function testAgent() {
  const testInput = document.getElementById('test-input').value;
  const testOutput = document.getElementById('test-output');
  
  if (!testInput) {
    testOutput.textContent = 'Please enter some test input';
    return;
  }
  
  // Save the agent first if it doesn't have an ID
  if (!currentAgent.id) {
    alert('Please save the agent before testing');
    return;
  }
  
  // Show loading state
  testOutput.textContent = 'Processing...';
  
  // Send test request
  fetch(`/api/builder/agents/${currentAgent.id}/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ input: testInput })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Test failed');
    }
    return response.json();
  })
  .then(data => {
    // Display formatted result
    testOutput.textContent = JSON.stringify(data, null, 2);
  })
  .catch(error => {
    console.error('Error testing agent:', error);
    testOutput.textContent = 'Error: ' + error.message;
  });
}