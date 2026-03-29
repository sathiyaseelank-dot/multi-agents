const express = require('express');

process.env.JWT_SECRET = 'test-secret';
process.env.JWT_EXPIRES_IN = '7d';

jest.mock('../models/User');
const User = require('../models/User');
const authRoutes = require('../routes/authRoutes');

const request = require('supertest');

const createApp = () => {
  const app = express();
  app.use(express.json());
  app.use('/api/auth', authRoutes);
  return app;
};

describe('Login Input Validation', () => {
  let app;

  beforeEach(() => {
    app = createApp();
    jest.clearAllMocks();
  });

  describe('Required fields', () => {
    it('should return 400 when email is missing', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ password: 'password123' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBeDefined();
      expect(typeof res.body.error).toBe('string');
    });

    it('should return 400 when password is missing', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@test.com' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBeDefined();
      expect(typeof res.body.error).toBe('string');
    });

    it('should return 400 when both email and password are missing', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({});

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBeDefined();
    });

    it('should return 400 when body is empty', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .set('Content-Type', 'application/json')
        .send();

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });
  });

  describe('Email format validation', () => {
    it('should reject email without @ symbol', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'notanemail', password: 'password123' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBeDefined();
    });

    it('should reject email without domain', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'user@', password: 'password123' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should reject email without local part', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: '@domain.com', password: 'password123' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should reject email with spaces', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'user @test.com', password: 'password123' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should reject empty string email', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: '', password: 'password123' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should accept valid email format', async () => {
      const mockUser = {
        _id: 'user123',
        email: 'valid@test.com',
        status: 'offline',
        matchPassword: jest.fn().mockResolvedValue(true),
        save: jest.fn().mockResolvedValue(true),
        toJSON() {
          return { _id: 'user123', email: 'valid@test.com', status: 'online' };
        },
      };

      User.findOne.mockReturnValue({
        select: jest.fn().mockResolvedValue(mockUser),
      });

      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'valid@test.com', password: 'password123' });

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
    });
  });

  describe('Password presence validation', () => {
    it('should reject empty string password', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@test.com', password: '' });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBeDefined();
    });

    it('should reject null password', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@test.com', password: null });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });

    it('should accept any non-empty password (server does not enforce length)', async () => {
      const mockUser = {
        _id: 'user123',
        email: 'test@test.com',
        status: 'offline',
        matchPassword: jest.fn().mockResolvedValue(true),
        save: jest.fn().mockResolvedValue(true),
        toJSON() {
          return { _id: 'user123', email: 'test@test.com', status: 'online' };
        },
      };

      User.findOne.mockReturnValue({
        select: jest.fn().mockResolvedValue(mockUser),
      });

      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@test.com', password: 'a' });

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
    });
  });

  describe('Validation error response consistency', () => {
    it('should return JSON with success: false for validation errors', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({});

      expect(res.headers['content-type']).toMatch(/json/);
      expect(res.body).toHaveProperty('success', false);
      expect(res.body).toHaveProperty('error');
    });

    it('should return string error message for validation errors', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'invalid', password: 'pass' });

      expect(typeof res.body.error).toBe('string');
      expect(res.body.error.length).toBeGreaterThan(0);
    });

    it('should use 400 status code for all validation failures', async () => {
      const invalidPayloads = [
        {},
        { email: 'test@test.com' },
        { password: 'password123' },
        { email: '', password: 'password123' },
        { email: 'test@test.com', password: '' },
        { email: 'notanemail', password: 'password123' },
      ];

      for (const payload of invalidPayloads) {
        const res = await request(app)
          .post('/api/auth/login')
          .send(payload);

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      }
    });

    it('should not return data property on validation error', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'invalid' });

      expect(res.body.data).toBeUndefined();
    });
  });

  describe('Credential validation', () => {
    it('should return 401 (not 400) for valid format but wrong credentials', async () => {
      User.findOne.mockReturnValue({
        select: jest.fn().mockResolvedValue(null),
      });

      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'nobody@test.com', password: 'password123' });

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBe('Invalid credentials');
    });

    it('should return 401 for wrong password with existing user', async () => {
      const mockUser = {
        _id: 'user123',
        matchPassword: jest.fn().mockResolvedValue(false),
      };

      User.findOne.mockReturnValue({
        select: jest.fn().mockResolvedValue(mockUser),
      });

      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@test.com', password: 'wrongpassword' });

      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBe('Invalid credentials');
    });

    it('should not reveal whether email exists in system', async () => {
      User.findOne.mockReturnValue({
        select: jest.fn().mockResolvedValue(null),
      });

      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'nonexistent@test.com', password: 'password123' });

      expect(res.body.error).toBe('Invalid credentials');
      expect(res.body.error).not.toContain('email');
      expect(res.body.error).not.toContain('user');
    });
  });

  describe('Server error handling', () => {
    it('should return 500 on database error during login', async () => {
      User.findOne.mockImplementation(() => {
        throw new Error('DB connection lost');
      });

      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@test.com', password: 'password123' });

      expect(res.status).toBe(500);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toBeDefined();
    });
  });
});
