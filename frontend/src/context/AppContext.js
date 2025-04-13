import React, { createContext, useContext, useReducer, useCallback } from 'react';

// Initial state for the application context
const initialState = {
  user: null,
  notifications: [],
  systemStatus: {
    isHealthy: true,
    lastCheck: null
  },
  preferences: {
    darkMode: true,
    autoRefresh: true,
    refreshInterval: 30000 // 30 seconds
  },
  ui: {
    sidebarOpen: true,
    currentView: 'dashboard'
  }
};

// Context setup
const AppContext = createContext();

// Action types
const ActionTypes = {
  SET_USER: 'SET_USER',
  LOGOUT_USER: 'LOGOUT_USER',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  CLEAR_NOTIFICATIONS: 'CLEAR_NOTIFICATIONS',
  UPDATE_SYSTEM_STATUS: 'UPDATE_SYSTEM_STATUS',
  UPDATE_PREFERENCES: 'UPDATE_PREFERENCES',
  UPDATE_UI_STATE: 'UPDATE_UI_STATE',
  RESET_STATE: 'RESET_STATE'
};

// Reducer function
const appReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_USER:
      return {
        ...state,
        user: action.payload
      };
      
    case ActionTypes.LOGOUT_USER:
      return {
        ...state,
        user: null
      };
      
    case ActionTypes.ADD_NOTIFICATION:
      // Add timestamp if not provided
      const notification = {
        ...action.payload,
        id: action.payload.id || Date.now().toString(),
        timestamp: action.payload.timestamp || Date.now()
      };
      
      return {
        ...state,
        notifications: [...state.notifications, notification]
      };
      
    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter(
          notification => notification.id !== action.payload
        )
      };
      
    case ActionTypes.CLEAR_NOTIFICATIONS:
      return {
        ...state,
        notifications: []
      };
      
    case ActionTypes.UPDATE_SYSTEM_STATUS:
      return {
        ...state,
        systemStatus: {
          ...state.systemStatus,
          ...action.payload,
          lastCheck: action.payload.lastCheck || Date.now()
        }
      };
      
    case ActionTypes.UPDATE_PREFERENCES:
      return {
        ...state,
        preferences: {
          ...state.preferences,
          ...action.payload
        }
      };
      
    case ActionTypes.UPDATE_UI_STATE:
      return {
        ...state,
        ui: {
          ...state.ui,
          ...action.payload
        }
      };
      
    case ActionTypes.RESET_STATE:
      return {
        ...initialState,
        // Preserve some state if needed
        preferences: state.preferences
      };
      
    default:
      return state;
  }
};

// Provider component
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);
  
  // Action creators
  const setUser = useCallback((user) => {
    dispatch({ type: ActionTypes.SET_USER, payload: user });
  }, []);
  
  const logoutUser = useCallback(() => {
    dispatch({ type: ActionTypes.LOGOUT_USER });
  }, []);
  
  const addNotification = useCallback((notification) => {
    dispatch({ type: ActionTypes.ADD_NOTIFICATION, payload: notification });
  }, []);
  
  const removeNotification = useCallback((id) => {
    dispatch({ type: ActionTypes.REMOVE_NOTIFICATION, payload: id });
  }, []);
  
  const clearNotifications = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_NOTIFICATIONS });
  }, []);
  
  const updateSystemStatus = useCallback((status) => {
    dispatch({ type: ActionTypes.UPDATE_SYSTEM_STATUS, payload: status });
  }, []);
  
  const updatePreferences = useCallback((preferences) => {
    dispatch({ type: ActionTypes.UPDATE_PREFERENCES, payload: preferences });
    
    // Apply preferences
    if (preferences.darkMode !== undefined) {
      document.documentElement.setAttribute(
        'data-bs-theme', 
        preferences.darkMode ? 'dark' : 'light'
      );
    }
  }, []);
  
  const updateUIState = useCallback((uiState) => {
    dispatch({ type: ActionTypes.UPDATE_UI_STATE, payload: uiState });
  }, []);
  
  const resetState = useCallback(() => {
    dispatch({ type: ActionTypes.RESET_STATE });
  }, []);
  
  // Expose state and actions
  const contextValue = {
    state,
    actions: {
      setUser,
      logoutUser,
      addNotification,
      removeNotification,
      clearNotifications,
      updateSystemStatus,
      updatePreferences,
      updateUIState,
      resetState
    }
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook for using the context
export const useAppContext = () => {
  const context = useContext(AppContext);
  
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  
  return context;
};

export default AppContext;