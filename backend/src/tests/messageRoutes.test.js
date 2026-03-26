const express = require('express');
const jwt = require('jsonwebtoken');

process.env.JWT_SECRET = 'test-secret';

jest.mock('../models/Message');
jest.mock('../models/Conversation');

const Message = require('../models/Message');
const Conversation = require('../models/Conversation');
const messageRoutes = require('../routes/messageRoutes');

const createApp = () => {
  const app = express();
  app.use(express.json());
  app.set('io', { to: jest.fn().mockReturnValue({ emit: jest.fn() }) });
  app.use('/api/messages', messageRoutes);
  app.use((err, req, res, next) => {
    res.status(500).json({ success: false, error: err.message });
  });
  return app;
};

const request = require('supertest');

describe('Message Routes Integration', () => {
  let app;
  let authToken;

  beforeEach(() => {
    app = createApp();
    authToken = jwt.sign({ id: 'user123' }, 'test-secret');
    jest.clearAllMocks();
  });

  describe('GET /api/messages/conversation/:conversationId', () => {
    it('should return messages for a conversation', async () => {
      const mockMessages = [
        {
          _id: 'msg1',
          content: 'Hello',
          sender: { _id: 'user123', username: 'user1' },
        },
      ];

      Conversation.findById.mockResolvedValue({
        _id: 'conv1',
        isParticipant: jest.fn().mockReturnValue(true),
      });

      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
        sort: jest.fn().mockReturnThis(),
        skip: jest.fn().mockReturnThis(),
        limit: jest.fn().mockResolvedValue(mockMessages),
      };

      Message.find.mockReturnValue(mockQuery);
      Message.countDocuments.mockResolvedValue(1);

      const res = await request(app)
        .get('/api/messages/conversation/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data).toBeDefined();
      expect(res.body.pagination).toBeDefined();
    });

    it('should return 404 for non-existent conversation', async () => {
      Conversation.findById.mockResolvedValue(null);

      const res = await request(app)
        .get('/api/messages/conversation/nonexistent')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Conversation not found');
    });

    it('should return 403 for non-participant', async () => {
      Conversation.findById.mockResolvedValue({
        _id: 'conv1',
        isParticipant: jest.fn().mockReturnValue(false),
      });

      const res = await request(app)
        .get('/api/messages/conversation/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(403);
      expect(res.body.error).toBe('Not authorized to view these messages');
    });

    it('should return 401 without auth token', async () => {
      const res = await request(app).get('/api/messages/conversation/conv1');

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
    });

    it('should support pagination', async () => {
      Conversation.findById.mockResolvedValue({
        isParticipant: jest.fn().mockReturnValue(true),
      });

      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
        sort: jest.fn().mockReturnThis(),
        skip: jest.fn().mockReturnThis(),
        limit: jest.fn().mockResolvedValue([]),
      };

      Message.find.mockReturnValue(mockQuery);
      Message.countDocuments.mockResolvedValue(100);

      const res = await request(app)
        .get('/api/messages/conversation/conv1?page=3&limit=20')
        .set('Authorization', `Bearer ${authToken}`);

      expect(mockQuery.skip).toHaveBeenCalledWith(40);
      expect(mockQuery.limit).toHaveBeenCalledWith(20);
      expect(res.body.pagination.page).toBe(3);
      expect(res.body.pagination.limit).toBe(20);
    });

    it('should exclude deleted messages', async () => {
      Conversation.findById.mockResolvedValue({
        isParticipant: jest.fn().mockReturnValue(true),
      });

      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
        sort: jest.fn().mockReturnThis(),
        skip: jest.fn().mockReturnThis(),
        limit: jest.fn().mockResolvedValue([]),
      };

      Message.find.mockReturnValue(mockQuery);
      Message.countDocuments.mockResolvedValue(0);

      await request(app)
        .get('/api/messages/conversation/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(Message.find).toHaveBeenCalledWith(
        expect.objectContaining({ isDeleted: false })
      );
    });
  });

  describe('POST /api/messages', () => {
    it('should send a new message', async () => {
      const mockMessage = {
        _id: 'msg1',
        conversationId: 'conv1',
        sender: 'user123',
        content: 'Hello!',
        messageType: 'text',
      };

      const mockConversation = {
        _id: 'conv1',
        isParticipant: jest.fn().mockReturnValue(true),
        unreadCount: [{ user: 'user123', count: 0 }],
        save: jest.fn().mockResolvedValue(true),
      };

      Conversation.findById.mockResolvedValue(mockConversation);
      Message.create.mockResolvedValue(mockMessage);
      Message.findById.mockReturnValue({
        populate: jest.fn().mockResolvedValue({
          ...mockMessage,
          sender: { _id: 'user123', username: 'user1' },
        }),
      });

      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ conversationId: 'conv1', content: 'Hello!' });

      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
      expect(res.body.data).toBeDefined();
    });

    it('should reject message with missing conversationId', async () => {
      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ content: 'Hello!' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should reject text message with empty content', async () => {
      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ conversationId: 'conv1', content: '', messageType: 'text' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should return 404 for non-existent conversation', async () => {
      Conversation.findById.mockResolvedValue(null);

      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ conversationId: 'nonexistent', content: 'Hello!' });

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Conversation not found');
    });

    it('should return 403 for non-participant', async () => {
      Conversation.findById.mockResolvedValue({
        isParticipant: jest.fn().mockReturnValue(false),
      });

      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ conversationId: 'conv1', content: 'Hello!' });

      expect(res.status).toBe(403);
      expect(res.body.error).toBe('Not authorized to send messages to this conversation');
    });

    it('should return 401 without auth token', async () => {
      const res = await request(app)
        .post('/api/messages')
        .send({ conversationId: 'conv1', content: 'Hello!' });

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
    });

    it('should create message with replyTo reference', async () => {
      const mockMessage = {
        _id: 'msg2',
        conversationId: 'conv1',
        sender: 'user123',
        content: 'Reply!',
        replyTo: 'msg1',
      };

      const mockConversation = {
        _id: 'conv1',
        isParticipant: jest.fn().mockReturnValue(true),
        unreadCount: [],
        save: jest.fn().mockResolvedValue(true),
      };

      Conversation.findById.mockResolvedValue(mockConversation);
      Message.create.mockResolvedValue(mockMessage);
      Message.findById.mockReturnValue({
        populate: jest.fn().mockResolvedValue(mockMessage),
      });

      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ conversationId: 'conv1', content: 'Reply!', replyTo: 'msg1' });

      expect(res.status).toBe(201);
      expect(Message.create).toHaveBeenCalledWith(
        expect.objectContaining({ replyTo: 'msg1' })
      );
    });
  });

  describe('PUT /api/messages/:id/read', () => {
    it('should mark message as read', async () => {
      const mockMessage = {
        _id: 'msg1',
        conversationId: 'conv1',
        readBy: [],
        isReadBy: jest.fn().mockReturnValue(false),
        save: jest.fn().mockResolvedValue(true),
      };

      Message.findById.mockResolvedValue(mockMessage);
      Conversation.findById.mockResolvedValue({
        unreadCount: [{ user: 'user123', count: 3 }],
        isParticipant: jest.fn().mockReturnValue(true),
        save: jest.fn().mockResolvedValue(true),
      });

      const res = await request(app)
        .put('/api/messages/msg1/read')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
    });

    it('should not duplicate read entry if already read', async () => {
      const mockMessage = {
        _id: 'msg1',
        conversationId: 'conv1',
        readBy: [{ user: 'user123' }],
        isReadBy: jest.fn().mockReturnValue(true),
        save: jest.fn().mockResolvedValue(true),
      };

      Message.findById.mockResolvedValue(mockMessage);
      Conversation.findById.mockResolvedValue({
        unreadCount: [],
        isParticipant: jest.fn().mockReturnValue(true),
        save: jest.fn().mockResolvedValue(true),
      });

      const res = await request(app)
        .put('/api/messages/msg1/read')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(mockMessage.readBy).toHaveLength(1);
    });

    it('should return 404 for non-existent message', async () => {
      Message.findById.mockResolvedValue(null);

      const res = await request(app)
        .put('/api/messages/nonexistent/read')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Message not found');
    });
  });

  describe('PUT /api/messages/:id/reaction', () => {
    it('should add a reaction to a message', async () => {
      const mockMessage = {
        _id: 'msg1',
        reactions: [],
        addReaction: jest.fn(),
        save: jest.fn().mockResolvedValue(true),
      };

      Message.findById.mockResolvedValue(mockMessage);

      const res = await request(app)
        .put('/api/messages/msg1/reaction')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ emoji: '👍' });

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(mockMessage.addReaction).toHaveBeenCalledWith('user123', '👍');
    });

    it('should remove a reaction from a message', async () => {
      const mockMessage = {
        _id: 'msg1',
        reactions: [{ user: 'user123', emoji: '👍' }],
        removeReaction: jest.fn(),
        save: jest.fn().mockResolvedValue(true),
      };

      Message.findById.mockResolvedValue(mockMessage);

      const res = await request(app)
        .put('/api/messages/msg1/reaction')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ emoji: '👍', action: 'remove' });

      expect(res.status).toBe(200);
      expect(mockMessage.removeReaction).toHaveBeenCalledWith('user123', '👍');
    });

    it('should return 404 for non-existent message', async () => {
      Message.findById.mockResolvedValue(null);

      const res = await request(app)
        .put('/api/messages/nonexistent/reaction')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ emoji: '👍' });

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Message not found');
    });
  });

  describe('DELETE /api/messages/:id', () => {
    it('should soft-delete own message', async () => {
      const mockMessage = {
        _id: 'msg1',
        sender: 'user123',
        content: 'Hello!',
        isDeleted: false,
        save: jest.fn().mockResolvedValue(true),
      };

      Message.findById.mockResolvedValue(mockMessage);

      const res = await request(app)
        .delete('/api/messages/msg1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.message).toBe('Message deleted successfully');
      expect(mockMessage.isDeleted).toBe(true);
      expect(mockMessage.deletedAt).toBeInstanceOf(Date);
      expect(mockMessage.content).toBe('This message was deleted');
    });

    it('should not allow deleting another users message', async () => {
      const mockMessage = {
        _id: 'msg1',
        sender: 'otheruser',
      };

      Message.findById.mockResolvedValue(mockMessage);

      const res = await request(app)
        .delete('/api/messages/msg1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(403);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBe('Not authorized to delete this message');
    });

    it('should return 404 for non-existent message', async () => {
      Message.findById.mockResolvedValue(null);

      const res = await request(app)
        .delete('/api/messages/nonexistent')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Message not found');
    });

    it('should return 401 without auth token', async () => {
      const res = await request(app).delete('/api/messages/msg1');

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
    });
  });
});
