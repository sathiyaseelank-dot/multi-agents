import { useState, useRef, useEffect, useCallback } from 'react';
import { useSocket } from '../../context/SocketContext';
import './MessageComposer.css';

const MessageComposer = ({ 
  conversationId, 
  onSendMessage, 
  disabled = false 
}) => {
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const { sendTyping, sendStopTyping } = useSocket();

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 150);
    textarea.style.height = `${newHeight}px`;
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [message, adjustTextareaHeight]);

  const handleTyping = useCallback(() => {
    if (!conversationId) return;
    
    sendTyping(conversationId);
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    typingTimeoutRef.current = setTimeout(() => {
      sendStopTyping(conversationId);
    }, 2000);
  }, [conversationId, sendTyping, sendStopTyping]);

  const handleChange = (e) => {
    const value = e.target.value;
    if (value.length <= 10000) {
      setMessage(value);
      setError(null);
      handleTyping();
    } else {
      setError('Message is too long (max 10000 characters)');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isSending || disabled) return;

    setIsSending(true);
    setError(null);

    try {
      await onSendMessage(trimmedMessage);
      setMessage('');
      sendStopTyping(conversationId);
    } catch (err) {
      setError(err.message || 'Failed to send message');
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handlePaste = (e) => {
    const text = e.clipboardData?.getData('text') || '';
    if (message.length + text.length > 10000) {
      e.preventDefault();
      setError('Message is too long (max 10000 characters)');
    }
  };

  const isDisabled = disabled || isSending;

  return (
    <form className="message-composer" onSubmit={handleSubmit}>
      {error && (
        <div className="composer-error">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}
      
      <div className="composer-container">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="Type a message..."
          disabled={isDisabled}
          rows={1}
          className="composer-input"
        />
        
        <button
          type="submit"
          className="composer-send"
          disabled={isDisabled || !message.trim()}
          title="Send message"
        >
          {isSending ? (
            <span className="send-loading"></span>
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          )}
        </button>
      </div>
      
      <div className="composer-hint">
        Press Enter to send, Shift+Enter for new line
      </div>
    </form>
  );
};

export default MessageComposer;
