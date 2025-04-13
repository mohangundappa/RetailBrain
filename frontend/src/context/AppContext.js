import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { healthService, agentService } from '../api/apiService';

// Initial state
const initialState = {
  // System state
  systemStatus: {
    isHealthy: null,
    loading: true,
    error: null,
    lastChecked: null,
    metrics: {}
  },
  
  // Agents state
  agents: {
    list: [],
    loading: true,
    error: null,
    selected: null
  },
  
  // Chat state
  chat: {
    sessionId: null,
    messages: [],
    loading: false,
    error: null,
    activeAgent: null
  },
  
  // UI state
  ui: {
    sidebarOpen: true,
    theme: 'dark',
    currentPage: 'home',
    notifications: []
  },
  
  // User state (for future authentication)
  user: {
    authenticated: false,
    preferences: {}
  }
};

// Action types
const ActionTypes = {
  SET_SYSTEM_STATUS: 'SET_SYSTEM_STATUS',
  SET_AGENTS: 'SET_AGENTS',
  SELECT_AGENT: 'SELECT_AGENT',
  ADD_CHAT_MESSAGE: 'ADD_CHAT_MESSAGE',
  SET_CHAT_SESSION: 'SET_CHAT_SESSION',
  SET_CHAT_LOADING: 'SET_CHAT_LOADING',
  SET_CHAT_ERROR: 'SET_CHAT_ERROR',
  TOGGLE_SIDEBAR: 'TOGGLE_SIDEBAR',
  SET_THEME: 'SET_THEME',
  SET_CURRENT_PAGE: 'SET_CURRENT_PAGE',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  SET_USER: 'SET_USER'
};

// Reducer function
function appReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_SYSTEM_STATUS:
      return {
        ...state,
        systemStatus: {
          ...state.systemStatus,
          ...action.payload,
          lastChecked: new Date()
        }
      };
    
    case ActionTypes.SET_AGENTS:
      return {
        ...state,
        agents: {
          ...state.agents,
          list: action.payload.agents,
          loading: false,
          error: action.payload.error
        }
      };
    
    case ActionTypes.SELECT_AGENT:
      return {
        ...state,
        agents: {
          ...state.agents,
          selected: action.payload
        }
      };
    
    case ActionTypes.ADD_CHAT_MESSAGE:
      return {
        ...state,
        chat: {
          ...state.chat,
          messages: [...state.chat.messages, action.payload]
        }
      };
    
    case ActionTypes.SET_CHAT_SESSION:
      return {
        ...state,
        chat: {
          ...state.chat,
          sessionId: action.payload,
          messages: []
        }
      };
    
    case ActionTypes.SET_CHAT_LOADING:
      return {
        ...state,
        chat: {
          ...state.chat,
          loading: action.payload
        }
      };
    
    case ActionTypes.SET_CHAT_ERROR:
      return {
        ...state,
        chat: {
          ...state.chat,
          error: action.payload
        }
      };
    
    case ActionTypes.TOGGLE_SIDEBAR:
      return {
        ...state,
        ui: {
          ...state.ui,
          sidebarOpen: !state.ui.sidebarOpen
        }
      };
    
    case ActionTypes.SET_THEME:
      return {
        ...state,
        ui: {
          ...state.ui,
          theme: action.payload
        }
      };
    
    case ActionTypes.SET_CURRENT_PAGE:
      return {
        ...state,
        ui: {
          ...state.ui,
          currentPage: action.payload
        }
      };
    
    case ActionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        ui: {
          ...state.ui,
          notifications: [...state.ui.notifications, { 
            id: Date.now(), 
            ...action.payload 
          }]
        }
      };
    
    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        ui: {
          ...state.ui,
          notifications: state.ui.notifications.filter(
            notification => notification.id !== action.payload
          )
        }
      };
    
    case ActionTypes.SET_USER:
      return {
        ...state,
        user: {
          ...state.user,
          ...action.payload
        }
      };
    
    default:
      return state;
  }
}

// Create the context
const AppContext = createContext();

// Context provider component
export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  
  // Load system status on initial render
  useEffect(() => {
    async function checkSystemStatus() {
      try {
        const response = await healthService.getStatus();
        dispatch({
          type: ActionTypes.SET_SYSTEM_STATUS,
          payload: {
            isHealthy: response.success && response.data?.health === 'healthy',
            loading: false,
            error: response.error || null,
            metrics: response.data?.metrics || {}
          }
        });
      } catch (error) {
        dispatch({
          type: ActionTypes.SET_SYSTEM_STATUS,
          payload: {
            isHealthy: false,
            loading: false,
            error: error.message
          }
        });
      }
    }
    
    // Initial check
    checkSystemStatus();
    
    // Set up interval for regular checks (every 30 seconds)
    const interval = setInterval(checkSystemStatus, 30000);
    
    return () => clearInterval(interval);
  }, []);
  
  // Load agents on initial render
  useEffect(() => {
    async function loadAgents() {
      try {
        const response = await agentService.listAgents();
        dispatch({
          type: ActionTypes.SET_AGENTS,
          payload: {
            agents: response.success ? response.agents : [],
            error: response.error || null
          }
        });
      } catch (error) {
        dispatch({
          type: ActionTypes.SET_AGENTS,
          payload: {
            agents: [],
            error: error.message
          }
        });
      }
    }
    
    loadAgents();
  }, []);
  
  // Context value
  const contextValue = {
    state,
    dispatch,
    actions: {
      setSystemStatus: (status) => dispatch({ 
        type: ActionTypes.SET_SYSTEM_STATUS, 
        payload: status 
      }),
      selectAgent: (agentId) => dispatch({ 
        type: ActionTypes.SELECT_AGENT, 
        payload: agentId 
      }),
      addChatMessage: (message) => dispatch({ 
        type: ActionTypes.ADD_CHAT_MESSAGE, 
        payload: message 
      }),
      setChatSession: (sessionId) => dispatch({ 
        type: ActionTypes.SET_CHAT_SESSION, 
        payload: sessionId 
      }),
      setChatLoading: (isLoading) => dispatch({ 
        type: ActionTypes.SET_CHAT_LOADING, 
        payload: isLoading 
      }),
      setChatError: (error) => dispatch({ 
        type: ActionTypes.SET_CHAT_ERROR, 
        payload: error 
      }),
      toggleSidebar: () => dispatch({ 
        type: ActionTypes.TOGGLE_SIDEBAR 
      }),
      setTheme: (theme) => dispatch({ 
        type: ActionTypes.SET_THEME, 
        payload: theme 
      }),
      setCurrentPage: (page) => dispatch({ 
        type: ActionTypes.SET_CURRENT_PAGE, 
        payload: page 
      }),
      addNotification: (notification) => dispatch({ 
        type: ActionTypes.ADD_NOTIFICATION, 
        payload: notification 
      }),
      removeNotification: (id) => dispatch({ 
        type: ActionTypes.REMOVE_NOTIFICATION, 
        payload: id 
      }),
      setUser: (user) => dispatch({ 
        type: ActionTypes.SET_USER, 
        payload: user 
      })
    }
  };
  
  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

// Custom hook to use the app context
export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}

export default AppContext;