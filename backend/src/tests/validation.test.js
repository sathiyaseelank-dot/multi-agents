const express = require('express');
const jwt = require('jsonwebtoken');

process.env.JWT_SECRET = 'test-secret';

jest.mock('../models/User');
jest.mock('../models/Conversation');
jest.mock('../models/Message');

const User = require('../models/User');
const Conversation = require('../models/Conversation');
const Message = require('../models/Message');
const authRoutes = require('../routes/authRoutes');
const userRoutes = require('../routes/userRoutes');
const conversationRoutes = require('../routes/conversationRoutes');
const messageRoutes = require('../routes/messageRoutes');

const request = require('supertest');

const createApp = () => {
  const app = express();
  app.use(express.json());
  app.use('/api/auth', authRoutes);
  app.use('/api/users', userRoutes);
  app.use('/api/conversations', conversationRoutes);
  app.use('/api/messages', messageRoutes);
  return app;
};

describe('Input Validation Tests', () => {
  let app;

  beforeEach(() => {
    app = createApp();
    jest.clearAllMocks();
  });

  describe('Auth route validations', () => {
    describe('Registration validation', () => {
      it('should reject empty username', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: '', email: 'test@test.com', password: 'password123' });

        expect(res.status).toBe(400);
      });

      it('should reject username with only spaces', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: '   ', email: 'test@test.com', password: 'password123' });

        expect(res.status).toBe(400);
      });

      it('should reject email without domain', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', email: 'test@', password: 'password123' });

        expect(res.status).toBe(400);
      });

      it('should reject email without @', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', email: 'testtest.com', password: 'password123' });

        expect(res.status).toBe(400);
      });

      it('should reject password with less than 6 chars', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', email: 'test@test.com', password: 'abc' });

        expect(res.status).toBe(400);
      });

      it('should accept valid registration data', async () => {
        User.findOne.mockResolvedValue(null);
        User.create.mockResolvedValue({
          _id: 'user123',
          username: 'testuser',
          email: 'test@test.com',
          toJSON() { return { _id: 'user123', username: 'testuser', email: 'test@test.com' }; },
        });

        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', email: 'test@test.com', password: 'password123' });

        expect(res.status).toBe(201);
      });
    });

    describe('Login validation', () => {
      it('should reject missing email', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ password: 'password123' });

        expect(res.status).toBe(400);
      });

      it('should reject missing password', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@test.com' });

        expect(res.status).toBe(400);
      });

      it('should reject invalid email format', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'notanemail', password: 'password123' });

        expect(res.status).toBe(400);
      });
    });
  });

  describe('User route validations', () => {
    let authToken;

    beforeEach(() => {
      authToken = jwt.sign({ id: 'user123' }, 'test-secret');
    });

    describe('Profile update validation', () => {
      it('should reject username shorter than 3 characters', async () => {
        const res = await request(app)
          .put('/api/users/profile')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ username: 'ab' });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Username must be 3-30 characters');
      });

      it('should reject username longer than 30 characters', async () => {
        const res = await request(app)
          .put('/api/users/profile')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ username: 'a'.repeat(31) });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Username must be 3-30 characters');
      });

      it('should reject invalid avatar URL', async () => {
        const res = await request(app)
          .put('/api/users/profile')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ avatar: 'not-a-url' });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Avatar must be a valid URL');
      });

      it('should accept valid avatar URL', async () => {
        User.findByIdAndUpdate.mockResolvedValue({
          _id: 'user123',
          username: 'testuser',
          avatar: 'https://example.com/avatar.png',
        });

        const res = await request(app)
          .put('/api/users/profile')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ avatar: 'https://example.com/avatar.png' });

        expect(res.status).toBe(200);
      });

      it('should accept valid username update', async () => {
        User.findOne.mockResolvedValue(null);
        User.findByIdAndUpdate.mockResolvedValue({
          _id: 'user123',
          username: 'newusername',
        });

        const res = await request(app)
          .put('/api/users/profile')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ username: 'newusername' });

        expect(res.status).toBe(200);
      });
    });

    describe('Status update validation', () => {
      it('should reject invalid status value', async () => {
        const res = await request(app)
          .put('/api/users/status')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ status: 'busy' });

        expect(res.status).toBe(400);
        expect(res.body.error).toBe('Invalid status');
      });

      it('should accept online status', async () => {
        User.findByIdAndUpdate.mockResolvedValue({ _id: 'user123', status: 'online' });

        const res = await request(app)
          .put('/api/users/status')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ status: 'online' });

        expect(res.status).toBe(200);
      });

      it('should accept offline status', async () => {
        User.findByIdAndUpdate.mockResolvedValue({ _id: 'user123', status: 'offline' });

        const res = await request(app)
          .put('/api/users/status')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ status: 'offline' });

        expect(res.status).toBe(200);
      });

      it('should accept away status', async () => {
        User.findByIdAndUpdate.mockResolvedValue({ _id: 'user123', status: 'away' });

        const res = await request(app)
          .put('/api/users/status')
          .set('Authorization', `Bearer ${authToken}`)
          .send({ status: 'away' });

        expect(res.status).toBe(200);
      });
    });
  });

  describe('Conversation route validations', () => {
    let authToken;

    beforeEach(() => {
      authToken = jwt.sign({ id: 'user123' }, 'test-secret');
    });

    it('should reject creating conversation without participantId', async () => {
      const res = await request(app)
        .post('/api/conversations')
        .set('Authorization', `Bearer ${authToken}`)
        .send({});

      expect(res.status).toBe(400);
    });
  });

  describe('Message route validations', () => {
    let authToken;

    beforeEach(() => {
      authToken = jwt.sign({ id: 'user123' }, 'test-secret');
    });

    it('should reject message without conversationId', async () => {
      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ content: 'Hello!' });

      expect(res.status).toBe(400);
    });

    it('should reject empty text message', async () => {
      const res = await request(app)
        .post('/api/messages')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ conversationId: 'conv1', content: '' });

      expect(res.status).toBe(400);
    });
  });

  describe('Authentication requirement', () => {
    it('should reject all protected user routes without token', async () => {
      const endpoints = [
        { method: 'get', path: '/api/users' },
        { method: 'get', path: '/api/users/user123' },
        { method: 'put', path: '/api/users/profile' },
        { method: 'put', path: '/api/users/status' },
      ];

      for (const endpoint of endpoints) {
        const res = await request(app)[endpoint.method](endpoint.path);
        expect(res.status).toBe(401);
      }
    });

    it('should reject all protected conversation routes without token', async () => {
      const endpoints = [
        { method: 'get', path: '/api/conversations' },
        { method: 'get', path: '/api/conversations/conv1' },
        { method: 'post', path: '/api/conversations' },
        { method: 'put', path: '/api/conversations/conv1' },
        { method: 'delete', path: '/api/conversations/conv1' },
      ];

      for (const endpoint of endpoints) {
        const res = await request(app)[endpoint.method](endpoint.path);
        expect(res.status).toBe(401);
      }
    });

    it('should reject all protected message routes without token', async () => {
      const endpoints = [
        { method: 'get', path: '/api/messages/conversation/conv1' },
        { method: 'post', path: '/api/messages' },
        { method: 'put', path: '/api/messages/msg1/read' },
        { method: 'put', path: '/api/messages/msg1/reaction' },
        { method: 'delete', path: '/api/messages/msg1' },
      ];

      for (const endpoint of endpoints) {
        const res = await request(app)[endpoint.method](endpoint.path);
        expect(res.status).toBe(401);
      }
    });
  });
});
