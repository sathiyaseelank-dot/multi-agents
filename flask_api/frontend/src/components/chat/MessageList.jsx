import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import './MessageList.css';

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  
  if (isToday) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + 
         date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const isNewGroup = (messages, index) => {
  if (index === 0) return true;
  
  const currentMessage = messages[index];
  const prevMessage = messages[index - 1];
  
  if (currentMessage.sender_id !== prevMessage.sender_id) return true;
  
  const timeDiff = new Date(currentMessage.created_at) - new Date(prevMessage.created_at);
  return timeDiff > 5 * 60 * 1000;
};

const Message = ({ message, isOwn, showAvatar, showTimestamp, onDelete }) => {
  const messageRef = useRef(null);
  
  useEffect(() => {
    if (messageRef.current) {
      messageRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, []);

  const handleDelete = () => {
    if (window.confirm('Delete this message?')) {
      onDelete(message.id);
    }
  };

  return (
    <div 
      ref={messageRef}
      className={`message ${isOwn ? 'message-own' : 'message-other'} ${!showAvatar ? 'message-consecutive' : ''}`}
    >
      {!isOwn && showAvatar && (
        <div className="message-avatar">
          {message.sender?.username?.charAt(0).toUpperCase() || '?'}
        </div>
      )}
      
      <div className="message-content-wrapper">
        {!isOwn && showAvatar && (
          <div className="message-sender-name">{message.sender?.username}</div>
        )}
        
        <div className="message-bubble">
          {message.message_type === 'image' ? (
            <img src={message.content} alt="Shared" className="message-image" />
          ) : message.message_type === 'file' ? (
            <a href={message.content} target="_blank" rel="noopener noreferrer" className="message-file">
              📎 File
            </a>
          ) : message.message_type === 'system' ? (
            <div className="message-system">{message.content}</div>
          ) : (
            <div className="message-text">{message.content}</div>
          )}
        </div>
        
        <div className="message-meta">
          {showTimestamp && (
            <span className="message-time">{formatTime(message.created_at)}</span>
          )}
          {isOwn && message.is_read && <span className="message-read">✓✓</span>}
        </div>
        
        {isOwn && (
          <button className="message-delete" onClick={handleDelete} title="Delete message">
            ×
          </button>
        )}
      </div>
    </div>
  );
};

const TypingIndicator = ({ users }) => {
  if (!users || users.length === 0) return null;
  
  const text = users.length === 1 
    ? `${users[0]} is typing...`
    : users.length === 2
      ? `${users[0]} and ${users[1]} are typing...`
      : `${users.length} people are typing...`;

  return (
    <div className="typing-indicator">
      <div className="typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span className="typing-text">{text}</span>
    </div>
  );
};

const MessageList = ({ 
  messages = [], 
  isLoading, 
  hasMore, 
  onLoadMore, 
  typingUsers = [],
  onDeleteMessage,
  isLoadingMore 
}) => {
  const containerRef = useRef(null);
  const { user } = useAuth();

  const handleScroll = useCallback(() => {
    if (!containerRef.current || isLoadingMore || !hasMore) return;
    
    const { scrollTop } = containerRef.current;
    if (scrollTop < 100) {
      onLoadMore?.();
    }
  }, [isLoadingMore, hasMore, onLoadMore]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  useEffect(() => {
    if (!isLoading && containerRef.current && messages.length > 0) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages.length, isLoading]);

  if (isLoading) {
    return (
      <div className="message-list-container">
        <div className="message-list-loading">
          <div className="loading-spinner"></div>
          <span>Loading messages...</span>
        </div>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="message-list-container">
        <div className="message-list-empty">
          <div className="empty-icon">💬</div>
          <h3>No messages yet</h3>
          <p>Start the conversation by sending a message below.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list-container" ref={containerRef}>
      {isLoadingMore && (
        <div className="message-list-loading-more">
          <div className="loading-spinner small"></div>
        </div>
      )}
      
      <div className="message-list">
        {messages.map((message, index) => (
          <Message
            key={message.id || index}
            message={message}
            isOwn={message.sender_id === user?.id}
            showAvatar={isNewGroup(messages, index)}
            showTimestamp={isNewGroup(messages, index)}
            onDelete={onDeleteMessage}
          />
        ))}
        
        {typingUsers.length > 0 && (
          <TypingIndicator users={typingUsers} />
        )}
      </div>
    </div>
  );
};

export default MessageList;
