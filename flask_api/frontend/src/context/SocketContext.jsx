import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';

const SocketContext = createContext(null);

const SOCKET_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5000' 
  : '';

export const SocketProvider = ({ children }) => {
  const { token, isAuthenticated } = useAuth();
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState({});
  const socketRef = useRef(null);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
        setSocket(null);
        setIsConnected(false);
      }
      return;
    }

    const loadSocketIO = async () => {
      const { io } = await import('socket.io-client');
      
      const newSocket = io(SOCKET_URL, {
        auth: { token },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });

      newSocket.on('connect', () => {
        setIsConnected(true);
        console.log('Socket connected');
      });

      newSocket.on('disconnect', () => {
        setIsConnected(false);
        console.log('Socket disconnected');
      });

      newSocket.on('error', (data) => {
        console.error('Socket error:', data.message);
      });

      newSocket.on('online_users', (users) => {
        setOnlineUsers(users);
      });

      socketRef.current = newSocket;
      setSocket(newSocket);
    };

    loadSocketIO();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, [isAuthenticated, token]);

  const joinConversation = useCallback((conversationId) => {
    if (socket) {
      socket.emit('join', { conversation_id: conversationId });
    }
  }, [socket]);

  const leaveConversation = useCallback((conversationId) => {
    if (socket) {
      socket.emit('leave', { conversation_id: conversationId });
    }
  }, [socket]);

  const sendTyping = useCallback((conversationId) => {
    if (socket) {
      socket.emit('typing', { conversation_id: conversationId });
    }
  }, [socket]);

  const sendStopTyping = useCallback((conversationId) => {
    if (socket) {
      socket.emit('stop_typing', { conversation_id: conversationId });
    }
  }, [socket]);

  const markAsRead = useCallback((conversationId) => {
    if (socket) {
      socket.emit('read', { conversation_id: conversationId });
    }
  }, [socket]);

  const onMessage = useCallback((callback) => {
    if (socket) {
      socket.on('message', callback);
    }
  }, [socket]);

  const offMessage = useCallback((callback) => {
    if (socket) {
      socket.off('message', callback);
    }
  }, [socket]);

  const onTyping = useCallback((callback) => {
    if (socket) {
      socket.on('typing', (data) => {
        setTypingUsers(prev => ({
          ...prev,
          [data.conversation_id || 'unknown']: {
            ...prev[data.conversation_id || 'unknown'],
            [data.user_id]: data.username,
          }
        }));
        callback(data);
      });
    }
  }, [socket]);

  const onStopTyping = useCallback((callback) => {
    if (socket) {
      socket.on('stop_typing', (data) => {
        setTypingUsers(prev => {
          const conv = prev[data.conversation_id || 'unknown'] || {};
          const { [data.user_id]: _, ...rest } = conv;
          return {
            ...prev,
            [data.conversation_id || 'unknown']: rest,
          };
        });
        callback(data);
      });
    }
  }, [socket]);

  const onRead = useCallback((callback) => {
    if (socket) {
      socket.on('read', callback);
    }
  }, [socket]);

  const offRead = useCallback((callback) => {
    if (socket) {
      socket.off('read', callback);
    }
  }, [socket]);

  const getTypingUsers = useCallback((conversationId) => {
    return Object.values(typingUsers[conversationId] || {});
  }, [typingUsers]);

  const value = {
    socket,
    isConnected,
    onlineUsers,
    typingUsers,
    joinConversation,
    leaveConversation,
    sendTyping,
    sendStopTyping,
    markAsRead,
    onMessage,
    offMessage,
    onTyping,
    onStopTyping,
    onRead,
    offRead,
    getTypingUsers,
  };

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};

export default SocketContext;
