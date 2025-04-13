import React, { createContext, useReducer, useContext } from 'react';

// Initial state
const initialState = {
  user: null,
  isAuthenticated: false,
  agents: [],
  conversations: [],
  currentConversation: null,
  loading: false,
  error: null,
  notifications: []
};

// Action types
const ActionTypes = {
  SET_USER: 'SET_USER',
  SET_AGENTS: 'SET_AGENTS',
  SET_CONVERSATIONS: 'SET_CONVERSATIONS',
  SET_CURRENT_CONVERSATION: 'SET_CURRENT_CONVERSATION',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  CLEAR_NOTIFICATIONS: 'CLEAR_NOTIFICATIONS',
  RESET_STATE: 'RESET_STATE'
};

// Reducer function
const appReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_USER:
      return {
        ...state,
        user: action.payload,
        isAuthenticated: !!action.payload
      };
    case ActionTypes.SET_AGENTS:
      return {
        ...state,
        agents: action.payload
      };
    case ActionTypes.SET_CONVERSATIONS:
      return {
        ...state,
        conversations: action.payload
      };
    case ActionTypes.SET_CURRENT_CONVERSATION:
      return {
        ...state,
        currentConversation: action.payload
      };
    case ActionTypes.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        error: action.payload
      };
    case ActionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, action.payload]
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
    case ActionTypes.RESET_STATE:
      return initialState;
    default:
      return state;
  }
};

// Create context
const AppContext = createContext();

// Provider component
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Helper functions for common actions
  const setUser = (user) => {
    dispatch({ type: ActionTypes.SET_USER, payload: user });
  };

  const setAgents = (agents) => {
    dispatch({ type: ActionTypes.SET_AGENTS, payload: agents });
  };

  const setConversations = (conversations) => {
    dispatch({ type: ActionTypes.SET_CONVERSATIONS, payload: conversations });
  };

  const setCurrentConversation = (conversation) => {
    dispatch({ type: ActionTypes.SET_CURRENT_CONVERSATION, payload: conversation });
  };

  const setLoading = (isLoading) => {
    dispatch({ type: ActionTypes.SET_LOADING, payload: isLoading });
  };

  const setError = (error) => {
    dispatch({ type: ActionTypes.SET_ERROR, payload: error });
  };

  const addNotification = (notification) => {
    const id = Date.now();
    dispatch({
      type: ActionTypes.ADD_NOTIFICATION,
      payload: { id, ...notification }
    });

    // Auto-dismiss notifications after 5 seconds
    if (notification.autoClose !== false) {
      setTimeout(() => {
        removeNotification(id);
      }, notification.duration || 5000);
    }

    return id;
  };

  const removeNotification = (id) => {
    dispatch({ type: ActionTypes.REMOVE_NOTIFICATION, payload: id });
  };

  const clearNotifications = () => {
    dispatch({ type: ActionTypes.CLEAR_NOTIFICATIONS });
  };

  const resetState = () => {
    dispatch({ type: ActionTypes.RESET_STATE });
  };

  // Context value
  const contextValue = {
    ...state,
    setUser,
    setAgents,
    setConversations,
    setCurrentConversation,
    setLoading,
    setError,
    addNotification,
    removeNotification,
    clearNotifications,
    resetState
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook to use the app context
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

export default AppContext;