import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSocket } from '../context/SocketContext';
import { useChatApi } from '../api/chat';
import MessageList from '../components/chat/MessageList';
import MessageComposer from '../components/chat/MessageComposer';
import './ChatPage.css';

const ConversationList = ({ 
  conversations, 
  selectedId, 
  onSelect, 
  isLoading 
}) => {
  const { user } = useAuth();

  const getConversationName = (conv) => {
    if (conv.is_group) return conv.name;
    const other = conv.participants?.find(p => p.id !== user?.id);
    return other?.username || 'Unknown';
  };

  const getConversationAvatar = (conv) => {
    if (conv.is_group) return conv.name?.charAt(0).toUpperCase() || '#';
    const other = conv.participants?.find(p => p.id !== user?.id);
    return other?.username?.charAt(0).toUpperCase() || '?';
  };

  if (isLoading) {
    return (
      <div className="conversation-list-loading">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="conversation-list-empty">
        <p>No conversations yet</p>
      </div>
    );
  }

  return (
    <div className="conversation-list">
      {conversations.map(conv => (
        <div
          key={conv.id}
          className={`conversation-item ${selectedId === conv.id ? 'active' : ''}`}
          onClick={() => onSelect(conv.id)}
        >
          <div className="conversation-avatar">
            {getConversationAvatar(conv)}
          </div>
          <div className="conversation-info">
            <div className="conversation-header">
              <span className="conversation-name">{getConversationName(conv)}</span>
              {conv.unread_count > 0 && (
                <span className="conversation-badge">{conv.unread_count}</span>
              )}
            </div>
            {conv.last_message && (
              <div className="conversation-preview">
                {conv.last_message.sender_id === user?.id && 'You: '}
                {conv.last_message.content}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

const ChatPage = () => {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const { 
    socket, 
    isConnected, 
    joinConversation, 
    leaveConversation,
    onMessage,
    offMessage,
    onTyping,
    onStopTyping,
    getTypingUsers,
    markAsRead
  } = useSocket();
  const { 
    getConversations, 
    getMessages, 
    sendMessage, 
    deleteMessage,
    markConversationRead 
  } = useChatApi();

  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [error, setError] = useState(null);
  const [typingUsers, setTypingUsers] = useState([]);

  const loadConversations = useCallback(async () => {
    try {
      setIsLoadingConversations(true);
      const data = await getConversations();
      setConversations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingConversations(false);
    }
  }, [getConversations]);

  const loadMessages = useCallback(async (convId, loadMore = false) => {
    if (!convId) return;
    
    try {
      setIsLoadingMessages(!loadMore);
      setIsLoadingMore(loadMore);
      
      const beforeId = loadMore ? messages[0]?.id : null;
      const data = await getMessages(convId, { limit: 50, before: beforeId });
      
      if (loadMore) {
        setMessages(prev => [...data, ...prev]);
      } else {
        setMessages(data);
      }
      
      setHasMoreMessages(data.length === 50);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingMessages(false);
      setIsLoadingMore(false);
    }
  }, [getMessages, messages]);

  const handleNewMessage = useCallback((message) => {
    setMessages(prev => {
      if (prev.some(m => m.id === message.id)) return prev;
      return [...prev, message];
    });
  }, []);

  const handleTyping = useCallback((data) => {
    if (data.conversation_id === parseInt(conversationId)) {
      setTypingUsers(getTypingUsers(conversationId));
    }
  }, [conversationId, getTypingUsers]);

  const handleStopTyping = useCallback((data) => {
    if (data.conversation_id === parseInt(conversationId)) {
      setTypingUsers(getTypingUsers(conversationId));
    }
  }, [conversationId, getTypingUsers]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (isAuthenticated) {
      loadConversations();
    }
  }, [isAuthenticated, loadConversations]);

  useEffect(() => {
    if (conversationId && isAuthenticated) {
      loadMessages(conversationId);
      joinConversation(parseInt(conversationId));
      markConversationRead(parseInt(conversationId));
      markAsRead(parseInt(conversationId));
      
      const msgHandler = (msg) => {
        if (msg.conversation_id === parseInt(conversationId)) {
          handleNewMessage(msg);
        }
      };
      
      onMessage(msgHandler);
      onTyping(handleTyping);
      onStopTyping(handleStopTyping);
      
      return () => {
        leaveConversation(parseInt(conversationId));
        offMessage(msgHandler);
      };
    }
  }, [conversationId, isAuthenticated]);

  useEffect(() => {
    const currentConv = conversations.find(c => c.id === parseInt(conversationId));
    setCurrentConversation(currentConv);
  }, [conversationId, conversations]);

  const handleSendMessage = async (content) => {
    const msg = await sendMessage(conversationId, content);
    setMessages(prev => [...prev, msg]);
    markAsRead(parseInt(conversationId));
  };

  const handleDeleteMessage = async (messageId) => {
    await deleteMessage(messageId);
    setMessages(prev => prev.filter(m => m.id !== messageId));
  };

  const handleLoadMore = () => {
    if (!isLoadingMore && hasMoreMessages) {
      loadMessages(conversationId, true);
    }
  };

  const getConversationName = () => {
    if (!currentConversation) return 'Chat';
    if (currentConversation.is_group) return currentConversation.name;
    const other = currentConversation.participants?.find(p => p.id !== user?.id);
    return other?.username || 'Unknown';
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="chat-page">
      <aside className="chat-sidebar">
        <div className="sidebar-header">
          <h2>Chats</h2>
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`} 
                title={isConnected ? 'Connected' : 'Disconnected'}>
          </span>
        </div>
        
        <ConversationList
          conversations={conversations}
          selectedId={conversationId ? parseInt(conversationId) : null}
          onSelect={(id) => navigate(`/chat/${id}`)}
          isLoading={isLoadingConversations}
        />
      </aside>
      
      <main className="chat-main">
        {!conversationId ? (
          <div className="chat-empty">
            <div className="empty-icon">💬</div>
            <h3>Select a conversation</h3>
            <p>Choose a conversation from the list to start chatting</p>
          </div>
        ) : (
          <>
            <header className="chat-header">
              <div className="chat-header-info">
                <h3>{getConversationName()}</h3>
                {currentConversation?.is_group && (
                  <span className="group-members">
                    {currentConversation.participants?.length} members
                  </span>
                )}
              </div>
            </header>
            
            <MessageList
              messages={messages}
              isLoading={isLoadingMessages}
              hasMore={hasMoreMessages}
              onLoadMore={handleLoadMore}
              typingUsers={typingUsers}
              onDeleteMessage={handleDeleteMessage}
              isLoadingMore={isLoadingMore}
            />
            
            <MessageComposer
              conversationId={parseInt(conversationId)}
              onSendMessage={handleSendMessage}
              disabled={!isConnected}
            />
            
            {!isConnected && (
              <div className="connection-warning">
                Connection lost. Reconnecting...
              </div>
            )}
          </>
        )}
        
        {error && (
          <div className="chat-error">
            <span>{error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}
      </main>
    </div>
  );
};

export default ChatPage;
