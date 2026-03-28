import { useAuth } from '../context/AuthContext';

const API_BASE = '/api/chat';

export const useChatApi = () => {
  const { fetchWithAuth, token } = useAuth();

  const getConversations = async () => {
    const response = await fetchWithAuth(`${API_BASE}/conversations`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch conversations');
    }
    return response.json();
  };

  const getConversation = async (conversationId) => {
    const response = await fetchWithAuth(`${API_BASE}/conversations/${conversationId}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch conversation');
    }
    return response.json();
  };

  const createConversation = async (participantIds, isGroup = false, name = null) => {
    const response = await fetchWithAuth(`${API_BASE}/conversations`, {
      method: 'POST',
      body: JSON.stringify({ participant_ids: participantIds, is_group: isGroup, name }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create conversation');
    }
    return response.json();
  };

  const getMessages = async (conversationId, options = {}) => {
    const { limit = 50, before } = options;
    let url = `${API_BASE}/conversations/${conversationId}/messages?limit=${limit}`;
    if (before) {
      url += `&before=${before}`;
    }
    
    const response = await fetchWithAuth(url);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch messages');
    }
    return response.json();
  };

  const sendMessage = async (conversationId, content, messageType = 'text') => {
    const response = await fetchWithAuth(`${API_BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, message_type: messageType }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to send message');
    }
    return response.json();
  };

  const updateMessage = async (messageId, content) => {
    const response = await fetchWithAuth(`${API_BASE}/messages/${messageId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to update message');
    }
    return response.json();
  };

  const deleteMessage = async (messageId) => {
    const response = await fetchWithAuth(`${API_BASE}/messages/${messageId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete message');
    }
    return response.json();
  };

  const markConversationRead = async (conversationId) => {
    const response = await fetchWithAuth(`${API_BASE}/conversations/${conversationId}/read`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to mark as read');
    }
    return response.json();
  };

  const searchUsers = async (query) => {
    if (query.length < 2) return [];
    
    const response = await fetchWithAuth(`/api/chat/users/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to search users');
    }
    return response.json();
  };

  const addParticipant = async (conversationId, userId) => {
    const response = await fetchWithAuth(`${API_BASE}/conversations/${conversationId}/participants`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to add participant');
    }
    return response.json();
  };

  const removeParticipant = async (conversationId, userId) => {
    const response = await fetchWithAuth(`${API_BASE}/conversations/${conversationId}/participants/${userId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to remove participant');
    }
    return response.json();
  };

  return {
    getConversations,
    getConversation,
    createConversation,
    getMessages,
    sendMessage,
    updateMessage,
    deleteMessage,
    markConversationRead,
    searchUsers,
    addParticipant,
    removeParticipant,
  };
};

export default useChatApi;
