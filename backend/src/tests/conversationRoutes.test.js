const express = require('express');
const jwt = require('jsonwebtoken');

process.env.JWT_SECRET = 'test-secret';

jest.mock('../models/Conversation');
jest.mock('../models/User');

const Conversation = require('../models/Conversation');
const User = require('../models/User');
const conversationRoutes = require('../routes/conversationRoutes');

const createApp = () => {
  const app = express();
  app.use(express.json());
  app.use('/api/conversations', conversationRoutes);
  app.use((err, req, res, next) => {
    res.status(500).json({ success: false, error: err.message });
  });
  return app;
};

const request = require('supertest');

describe('Conversation Routes Integration', () => {
  let app;
  let authToken;

  beforeEach(() => {
    app = createApp();
    authToken = jwt.sign({ id: 'user123' }, 'test-secret');
    jest.clearAllMocks();
  });

  describe('GET /api/conversations', () => {
    it('should return user conversations', async () => {
      const mockConversations = [
        {
          _id: 'conv1',
          type: 'direct',
          participants: [{ user: { _id: 'user123', username: 'user1' } }],
          isActive: true,
        },
      ];

      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
        sort: jest.fn().mockReturnThis(),
        skip: jest.fn().mockReturnThis(),
        limit: jest.fn().mockResolvedValue(mockConversations),
      };

      Conversation.find.mockReturnValue(mockQuery);

      const res = await request(app)
        .get('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data).toEqual(mockConversations);
    });

    it('should return 401 without auth token', async () => {
      const res = await request(app).get('/api/conversations');

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
    });

    it('should support pagination', async () => {
      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
        sort: jest.fn().mockReturnThis(),
        skip: jest.fn().mockReturnThis(),
        limit: jest.fn().mockResolvedValue([]),
      };

      Conversation.find.mockReturnValue(mockQuery);

      await request(app)
        .get('/api/conversations?page=2&limit=10')
        .set('Authorization', `Bearer ${authToken}`);

      expect(mockQuery.skip).toHaveBeenCalledWith(10);
      expect(mockQuery.limit).toHaveBeenCalledWith(10);
    });

    it('should handle server errors', async () => {
      Conversation.find.mockImplementation(() => {
        throw new Error('DB error');
      });

      const res = await request(app)
        .get('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(500);
      expect(res.body.success).toBe(false);
    });
  });

  describe('GET /api/conversations/:id', () => {
    it('should return a specific conversation', async () => {
      const mockConversation = {
        _id: 'conv1',
        type: 'direct',
        participants: [{ user: { _id: 'user123' } }],
        isParticipant: jest.fn().mockReturnValue(true),
      };

      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
      };
      mockQuery.populate.mockReturnValueOnce(mockQuery);
      mockQuery.populate.mockResolvedValueOnce(mockConversation);

      Conversation.findById.mockReturnValue(mockQuery);

      const res = await request(app)
        .get('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
    });

    it('should return 404 for non-existent conversation', async () => {
      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
      };
      mockQuery.populate.mockReturnValueOnce(mockQuery);
      mockQuery.populate.mockResolvedValueOnce(null);

      Conversation.findById.mockReturnValue(mockQuery);

      const res = await request(app)
        .get('/api/conversations/nonexistent')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(404);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBe('Conversation not found');
    });

    it('should return 403 for non-participant', async () => {
      const mockConversation = {
        _id: 'conv1',
        participants: [{ user: { _id: 'otheruser' } }],
        isParticipant: jest.fn().mockReturnValue(false),
      };

      const mockQuery = {
        populate: jest.fn().mockReturnThis(),
      };
      mockQuery.populate.mockReturnValueOnce(mockQuery);
      mockQuery.populate.mockResolvedValueOnce(mockConversation);

      Conversation.findById.mockReturnValue(mockQuery);

      const res = await request(app)
        .get('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(403);
      expect(res.body.success).toBe(false);
    });
  });

  describe('POST /api/conversations', () => {
    it('should create a new direct conversation', async () => {
      const mockParticipant = {
        _id: 'user456',
        username: 'participant',
      };

      const mockConversation = {
        _id: 'conv1',
        type: 'direct',
        participants: [
          { user: 'user123', role: 'admin' },
          { user: 'user456', role: 'member' },
        ],
      };

      User.findById.mockResolvedValue(mockParticipant);
      Conversation.findOne.mockResolvedValue(null);
      Conversation.create.mockResolvedValue(mockConversation);
      Conversation.findById.mockReturnValue({
        populate: jest.fn().mockResolvedValue(mockConversation),
      });
      User.findByIdAndUpdate.mockResolvedValue({});

      const res = await request(app)
        .post('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ participantId: 'user456' });

      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
    });

    it('should return existing direct conversation if already exists', async () => {
      const existingConv = {
        _id: 'conv1',
        type: 'direct',
        participants: [
          { user: 'user123' },
          { user: 'user456' },
        ],
      };

      User.findById.mockResolvedValue({ _id: 'user456' });
      Conversation.findOne.mockResolvedValue(existingConv);

      const res = await request(app)
        .post('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ participantId: 'user456' });

      expect(res.status).toBe(200);
      expect(res.body.isExisting).toBe(true);
    });

    it('should return 404 for non-existent participant', async () => {
      User.findById.mockResolvedValue(null);

      const res = await request(app)
        .post('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ participantId: 'nonexistent' });

      expect(res.status).toBe(404);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBe('Participant not found');
    });

    it('should reject with missing participantId', async () => {
      const res = await request(app)
        .post('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`)
        .send({});

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should return 401 without auth token', async () => {
      const res = await request(app)
        .post('/api/conversations')
        .send({ participantId: 'user456' });

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
    });
  });

  describe('PUT /api/conversations/:id', () => {
    it('should update conversation name', async () => {
      const mockConversation = {
        _id: 'conv1',
        name: 'Old Name',
        isParticipant: jest.fn().mockReturnValue(true),
        save: jest.fn().mockResolvedValue(true),
      };

      Conversation.findById.mockResolvedValue(mockConversation);

      const res = await request(app)
        .put('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ name: 'New Name' });

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(mockConversation.name).toBe('New Name');
    });

    it('should update conversation description', async () => {
      const mockConversation = {
        _id: 'conv1',
        description: '',
        isParticipant: jest.fn().mockReturnValue(true),
        save: jest.fn().mockResolvedValue(true),
      };

      Conversation.findById.mockResolvedValue(mockConversation);

      const res = await request(app)
        .put('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ description: 'New description' });

      expect(res.status).toBe(200);
      expect(mockConversation.description).toBe('New description');
    });

    it('should return 404 for non-existent conversation', async () => {
      Conversation.findById.mockResolvedValue(null);

      const res = await request(app)
        .put('/api/conversations/nonexistent')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ name: 'New Name' });

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Conversation not found');
    });

    it('should return 403 for non-participant', async () => {
      const mockConversation = {
        _id: 'conv1',
        isParticipant: jest.fn().mockReturnValue(false),
      };

      Conversation.findById.mockResolvedValue(mockConversation);

      const res = await request(app)
        .put('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ name: 'New Name' });

      expect(res.status).toBe(403);
      expect(res.body.error).toBe('Not authorized to update this conversation');
    });
  });

  describe('DELETE /api/conversations/:id', () => {
    it('should soft-delete (archive) conversation', async () => {
      const mockConversation = {
        _id: 'conv1',
        isActive: true,
        isParticipant: jest.fn().mockReturnValue(true),
        save: jest.fn().mockResolvedValue(true),
      };

      Conversation.findById.mockResolvedValue(mockConversation);

      const res = await request(app)
        .delete('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.message).toBe('Conversation archived successfully');
      expect(mockConversation.isActive).toBe(false);
    });

    it('should return 404 for non-existent conversation', async () => {
      Conversation.findById.mockResolvedValue(null);

      const res = await request(app)
        .delete('/api/conversations/nonexistent')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Conversation not found');
    });

    it('should return 403 for non-participant', async () => {
      const mockConversation = {
        _id: 'conv1',
        isParticipant: jest.fn().mockReturnValue(false),
      };

      Conversation.findById.mockResolvedValue(mockConversation);

      const res = await request(app)
        .delete('/api/conversations/conv1')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(403);
      expect(res.body.error).toBe('Not authorized to delete this conversation');
    });
  });
});
