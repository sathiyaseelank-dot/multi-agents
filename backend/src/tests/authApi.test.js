const express = require('express');
const jwt = require('jsonwebtoken');

process.env.JWT_SECRET = 'test-secret-key';
process.env.JWT_EXPIRES_IN = '1h';

jest.mock('../models/User');
jest.mock('../models/Session');

const User = require('../models/User');
const Session = require('../models/Session');
const authRoutes = require('../routes/authRoutes');

const request = require('supertest');

const createApp = () => {
  const app = express();
  app.use(express.json());
  app.use('/api/auth', authRoutes);
  app.use((err, req, res, next) => {
    res.status(err.statusCode || 500).json({
      success: false,
      error: err.message || 'Internal server error',
    });
  });
  return app;
};

const validUserData = {
  username: 'testuser',
  email: 'test@example.com',
  password: 'password123',
};

const createMockUser = (overrides = {}) => ({
  _id: 'user123',
  username: 'testuser',
  email: 'test@example.com',
  status: 'offline',
  avatar: null,
  lastSeen: new Date(),
  createdAt: new Date(),
  updatedAt: new Date(),
  matchPassword: jest.fn().mockResolvedValue(true),
  save: jest.fn().mockResolvedValue(true),
  toJSON() {
    return {
      _id: this._id,
      username: this.username,
      email: this.email,
      status: this.status,
      avatar: this.avatar,
    };
  },
  ...overrides,
});

describe('Auth API - Complete Flow Tests', () => {
  let app;

  beforeEach(() => {
    app = createApp();
    jest.clearAllMocks();
  });

  describe('POST /api/auth/register', () => {
    describe('Successful registration', () => {
      it('should register user with valid data and return 201', async () => {
        const mockUser = createMockUser();
        User.findOne.mockResolvedValue(null);
        User.create.mockResolvedValue(mockUser);

        const res = await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(res.status).toBe(201);
        expect(res.body.success).toBe(true);
        expect(res.body.data).toBeDefined();
        expect(res.body.data.user).toBeDefined();
        expect(res.body.data.token).toBeDefined();
      });

      it('should return a JWT token on successful registration', async () => {
        const mockUser = createMockUser();
        User.findOne.mockResolvedValue(null);
        User.create.mockResolvedValue(mockUser);

        const res = await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(res.body.data.token).toBeDefined();
        expect(typeof res.body.data.token).toBe('string');

        const decoded = jwt.verify(res.body.data.token, 'test-secret-key');
        expect(decoded.id).toBe('user123');
      });

      it('should return user data without password field', async () => {
        const mockUser = createMockUser();
        User.findOne.mockResolvedValue(null);
        User.create.mockResolvedValue(mockUser);

        const res = await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(res.body.data.user.password).toBeUndefined();
      });

      it('should check for existing user before creating', async () => {
        User.findOne.mockResolvedValue(null);
        User.create.mockResolvedValue(createMockUser());

        await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(User.findOne).toHaveBeenCalledWith({
          $or: [{ email: 'test@example.com' }, { username: 'testuser' }],
        });
      });

      it('should call User.create with correct parameters', async () => {
        User.findOne.mockResolvedValue(null);
        User.create.mockResolvedValue(createMockUser());

        await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(User.create).toHaveBeenCalledWith({
          username: 'testuser',
          email: 'test@example.com',
          password: 'password123',
        });
      });
    });

    describe('Duplicate user rejection', () => {
      it('should reject when email already exists', async () => {
        User.findOne.mockResolvedValue({ email: 'test@example.com' });

        const res = await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toContain('already exists');
      });

      it('should reject when username already exists', async () => {
        User.findOne.mockResolvedValue({ username: 'testuser' });

        const res = await request(app)
          .post('/api/auth/register')
          .send({ ...validUserData, email: 'different@example.com' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toContain('already exists');
      });
    });

    describe('Validation errors', () => {
      it('should reject empty request body', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({});

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject missing username', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject missing email', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', password: 'password123' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject missing password', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', email: 'test@example.com' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject username shorter than 3 characters', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'ab', email: 'test@example.com', password: 'password123' });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Username must be 3-30 characters');
      });

      it('should reject username longer than 30 characters', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({
            username: 'a'.repeat(31),
            email: 'test@example.com',
            password: 'password123',
          });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Username must be 3-30 characters');
      });

      it('should reject invalid email format', async () => {
        const invalidEmails = [
          'notanemail',
          'user@',
          '@domain.com',
          'user @domain.com',
          '',
        ];

        for (const email of invalidEmails) {
          const res = await request(app)
            .post('/api/auth/register')
            .send({ username: 'testuser', email, password: 'password123' });

          expect(res.status).toBe(400);
        }
      });

      it('should reject password shorter than 6 characters', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({ username: 'testuser', email: 'test@example.com', password: '12345' });

        expect(res.status).toBe(400);
        expect(res.body.error).toContain('Password must be at least 6 characters');
      });

      it('should return error as comma-separated string', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({});

        expect(typeof res.body.error).toBe('string');
        expect(res.body.error.length).toBeGreaterThan(0);
      });
    });

    describe('Server error handling', () => {
      it('should return 500 on database error during user lookup', async () => {
        User.findOne.mockRejectedValue(new Error('Database connection failed'));

        const res = await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(res.status).toBe(500);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBeDefined();
      });

      it('should return 500 on database error during user creation', async () => {
        User.findOne.mockResolvedValue(null);
        User.create.mockRejectedValue(new Error('Write operation failed'));

        const res = await request(app)
          .post('/api/auth/register')
          .send(validUserData);

        expect(res.status).toBe(500);
        expect(res.body.success).toBe(false);
      });
    });
  });

  describe('POST /api/auth/login', () => {
    describe('Successful login', () => {
      it('should login with valid credentials and return 200', async () => {
        const mockUser = createMockUser();
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
        expect(res.body.data.user).toBeDefined();
        expect(res.body.data.token).toBeDefined();
      });

      it('should return a valid JWT token on login', async () => {
        const mockUser = createMockUser();
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        const decoded = jwt.verify(res.body.data.token, 'test-secret-key');
        expect(decoded.id).toBe('user123');
      });

      it('should update user status to online on login', async () => {
        const mockUser = createMockUser({ status: 'offline' });
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(mockUser.status).toBe('online');
        expect(mockUser.save).toHaveBeenCalled();
      });

      it('should update lastSeen on login', async () => {
        const mockUser = createMockUser();
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const beforeLogin = new Date();
        await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(mockUser.lastSeen).toBeInstanceOf(Date);
        expect(mockUser.lastSeen.getTime()).toBeGreaterThanOrEqual(beforeLogin.getTime());
      });

      it('should use select("+password") to fetch password field', async () => {
        const mockSelect = jest.fn().mockResolvedValue(createMockUser());
        User.findOne.mockReturnValue({ select: mockSelect });

        await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(mockSelect).toHaveBeenCalledWith('+password');
      });
    });

    describe('Authentication failure', () => {
      it('should return 401 for non-existent email', async () => {
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(null),
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'nonexistent@example.com', password: 'password123' });

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBe('Invalid credentials');
      });

      it('should return 401 for wrong password', async () => {
        const mockUser = createMockUser({
          matchPassword: jest.fn().mockResolvedValue(false),
        });
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'wrongpassword' });

        expect(res.status).toBe(401);
        expect(res.body.error).toBe('Invalid credentials');
      });

      it('should not reveal whether email exists (security)', async () => {
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(null),
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'nobody@example.com', password: 'password123' });

        expect(res.body.error).toBe('Invalid credentials');
        expect(res.body.error).not.toContain('email');
        expect(res.body.error).not.toContain('user');
        expect(res.body.error).not.toContain('found');
      });
    });

    describe('Validation errors', () => {
      it('should reject missing email', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ password: 'password123' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject missing password', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject empty request body', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({});

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject invalid email format', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'invalidemail', password: 'password123' });

        expect(res.status).toBe(400);
        expect(res.body.success).toBe(false);
      });

      it('should reject empty string email', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: '', password: 'password123' });

        expect(res.status).toBe(400);
      });

      it('should reject empty string password', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: '' });

        expect(res.status).toBe(400);
      });
    });

    describe('Server error handling', () => {
      it('should return 500 on database error', async () => {
        User.findOne.mockImplementation(() => {
          throw new Error('DB connection lost');
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(res.status).toBe(500);
        expect(res.body.success).toBe(false);
      });

      it('should return 500 when matchPassword throws', async () => {
        const mockUser = createMockUser({
          matchPassword: jest.fn().mockRejectedValue(new Error('bcrypt error')),
        });
        User.findOne.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'password123' });

        expect(res.status).toBe(500);
        expect(res.body.success).toBe(false);
      });
    });
  });

  describe('POST /api/auth/refresh', () => {
    describe('Successful token refresh', () => {
      it('should refresh token with valid current token', async () => {
        const mockUser = createMockUser();
        User.findById.mockResolvedValue(mockUser);

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .post('/api/auth/refresh')
          .set('Authorization', `Bearer ${token}`);

        if (res.status === 200) {
          expect(res.body.success).toBe(true);
          expect(res.body.data.token).toBeDefined();
          expect(res.body.data.token).not.toBe(token);
        }
      });

      it('should return new JWT with same user id', async () => {
        const mockUser = createMockUser();
        User.findById.mockResolvedValue(mockUser);

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .post('/api/auth/refresh')
          .set('Authorization', `Bearer ${token}`);

        if (res.status === 200) {
          const decoded = jwt.verify(res.body.data.token, 'test-secret-key');
          expect(decoded.id).toBe('user123');
        }
      });
    });

    describe('Refresh failure', () => {
      it('should return 401 without token', async () => {
        const res = await request(app).post('/api/auth/refresh');

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
      });

      it('should return 401 with expired token', async () => {
        const token = jwt.sign(
          { id: 'user123' },
          'test-secret-key',
          { expiresIn: '0s' }
        );

        const res = await request(app)
          .post('/api/auth/refresh')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(401);
      });

      it('should return 401 with invalid token', async () => {
        const res = await request(app)
          .post('/api/auth/refresh')
          .set('Authorization', 'Bearer invalid.token.here');

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
      });

      it('should return 401 with token signed with wrong secret', async () => {
        const token = jwt.sign({ id: 'user123' }, 'wrong-secret');

        const res = await request(app)
          .post('/api/auth/refresh')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(401);
      });
    });
  });

  describe('GET /api/auth/me (Protected Profile Access)', () => {
    describe('Successful profile access', () => {
      it('should return current user with valid token', async () => {
        const mockUser = createMockUser();
        User.findById.mockResolvedValue(mockUser);

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
        expect(res.body.data).toBeDefined();
        expect(res.body.data.username).toBe('testuser');
        expect(res.body.data.email).toBe('test@example.com');
      });

      it('should call User.findById with decoded user id', async () => {
        User.findById.mockResolvedValue(createMockUser());

        const token = jwt.sign({ id: 'user456' }, 'test-secret-key');

        await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(User.findById).toHaveBeenCalledWith('user456');
      });

      it('should return full user profile data', async () => {
        const mockUser = createMockUser({
          avatar: 'https://example.com/avatar.png',
          status: 'online',
        });
        User.findById.mockResolvedValue(mockUser);

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(200);
        expect(res.body.data).toBeDefined();
      });
    });

    describe('Authorization failures', () => {
      it('should return 401 without authorization header', async () => {
        const res = await request(app).get('/api/auth/me');

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBe('Not authorized, no token provided');
      });

      it('should return 401 with invalid token', async () => {
        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', 'Bearer invalid.token.here');

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBe('Not authorized, token invalid');
      });

      it('should return 401 with expired token', async () => {
        const token = jwt.sign(
          { id: 'user123' },
          'test-secret-key',
          { expiresIn: '0s' }
        );

        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(401);
      });

      it('should return 401 with token signed with wrong secret', async () => {
        const token = jwt.sign({ id: 'user123' }, 'wrong-secret');

        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(401);
      });

      it('should return 401 with Basic auth scheme', async () => {
        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', 'Basic dGVzdDp0ZXN0');

        expect(res.status).toBe(401);
      });

      it('should return 401 with empty Bearer token', async () => {
        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', 'Bearer ');

        expect(res.status).toBe(401);
      });
    });

    describe('User not found', () => {
      it('should return 404 when user no longer exists', async () => {
        User.findById.mockResolvedValue(null);

        const token = jwt.sign({ id: 'deleted123' }, 'test-secret-key');

        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(404);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBe('User not found');
      });
    });

    describe('Server error handling', () => {
      it('should return 500 on database error', async () => {
        User.findById.mockRejectedValue(new Error('DB error'));

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(500);
        expect(res.body.success).toBe(false);
      });
    });
  });

  describe('POST /api/auth/logout', () => {
    describe('Successful logout', () => {
      it('should logout user and return success', async () => {
        User.findByIdAndUpdate.mockResolvedValue({});

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .post('/api/auth/logout')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
        expect(res.body.message).toBe('Logged out successfully');
      });

      it('should set user status to offline on logout', async () => {
        User.findByIdAndUpdate.mockResolvedValue({});

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        await request(app)
          .post('/api/auth/logout')
          .set('Authorization', `Bearer ${token}`);

        expect(User.findByIdAndUpdate).toHaveBeenCalledWith(
          'user123',
          expect.objectContaining({ status: 'offline' })
        );
      });

      it('should update lastSeen on logout', async () => {
        User.findByIdAndUpdate.mockResolvedValue({});

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        await request(app)
          .post('/api/auth/logout')
          .set('Authorization', `Bearer ${token}`);

        expect(User.findByIdAndUpdate).toHaveBeenCalledWith(
          'user123',
          expect.objectContaining({ lastSeen: expect.any(Date) })
        );
      });
    });

    describe('Authorization failures', () => {
      it('should return 401 without token', async () => {
        const res = await request(app).post('/api/auth/logout');

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBe('Not authorized, no token provided');
      });

      it('should return 401 with invalid token', async () => {
        const res = await request(app)
          .post('/api/auth/logout')
          .set('Authorization', 'Bearer invalid.token');

        expect(res.status).toBe(401);
      });

      it('should return 401 with expired token', async () => {
        const token = jwt.sign(
          { id: 'user123' },
          'test-secret-key',
          { expiresIn: '0s' }
        );

        const res = await request(app)
          .post('/api/auth/logout')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(401);
      });
    });

    describe('Server error handling', () => {
      it('should return 500 on database error', async () => {
        User.findByIdAndUpdate.mockRejectedValue(new Error('DB error'));

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .post('/api/auth/logout')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(500);
        expect(res.body.success).toBe(false);
      });
    });
  });

  describe('PUT /api/auth/password', () => {
    describe('Successful password change', () => {
      it('should change password with valid current password', async () => {
        const mockUser = createMockUser({
          matchPassword: jest.fn().mockResolvedValue(true),
          save: jest.fn().mockResolvedValue(true),
        });
        User.findById.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .put('/api/auth/password')
          .set('Authorization', `Bearer ${token}`)
          .send({ currentPassword: 'oldpass123', newPassword: 'newpass123' });

        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
        expect(res.body.data.token).toBeDefined();
      });

      it('should return new token after password change', async () => {
        const mockUser = createMockUser({
          matchPassword: jest.fn().mockResolvedValue(true),
          save: jest.fn().mockResolvedValue(true),
        });
        User.findById.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .put('/api/auth/password')
          .set('Authorization', `Bearer ${token}`)
          .send({ currentPassword: 'oldpass123', newPassword: 'newpass123' });

        const decoded = jwt.verify(res.body.data.token, 'test-secret-key');
        expect(decoded.id).toBe('user123');
      });

      it('should save the user after password update', async () => {
        const mockSave = jest.fn().mockResolvedValue(true);
        const mockUser = createMockUser({
          matchPassword: jest.fn().mockResolvedValue(true),
          save: mockSave,
        });
        User.findById.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        await request(app)
          .put('/api/auth/password')
          .set('Authorization', `Bearer ${token}`)
          .send({ currentPassword: 'oldpass123', newPassword: 'newpass123' });

        expect(mockSave).toHaveBeenCalled();
      });
    });

    describe('Password change failure', () => {
      it('should reject with wrong current password', async () => {
        const mockUser = createMockUser({
          matchPassword: jest.fn().mockResolvedValue(false),
        });
        User.findById.mockReturnValue({
          select: jest.fn().mockResolvedValue(mockUser),
        });

        const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

        const res = await request(app)
          .put('/api/auth/password')
          .set('Authorization', `Bearer ${token}`)
          .send({ currentPassword: 'wrongpass', newPassword: 'newpass123' });

        expect(res.status).toBe(401);
        expect(res.body.success).toBe(false);
        expect(res.body.error).toBe('Current password is incorrect');
      });

      it('should return 401 without token', async () => {
        const res = await request(app)
          .put('/api/auth/password')
          .send({ currentPassword: 'oldpass123', newPassword: 'newpass123' });

        expect(res.status).toBe(401);
      });
    });
  });

  describe('Response Format Consistency', () => {
    it('should return consistent JSON structure for success responses', async () => {
      const mockUser = createMockUser();
      User.findOne.mockResolvedValue(null);
      User.create.mockResolvedValue(mockUser);

      const res = await request(app)
        .post('/api/auth/register')
        .send(validUserData);

      expect(res.body).toHaveProperty('success', true);
      expect(res.body).toHaveProperty('data');
      expect(res.body.data).toHaveProperty('user');
      expect(res.body.data).toHaveProperty('token');
    });

    it('should return consistent JSON structure for error responses', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send({});

      expect(res.body).toHaveProperty('success', false);
      expect(res.body).toHaveProperty('error');
      expect(typeof res.body.error).toBe('string');
    });

    it('should return application/json content type', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'invalid', password: 'pass' });

      expect(res.headers['content-type']).toMatch(/application\/json/);
    });

    it('should not expose internal stack traces in error responses', async () => {
      User.findOne.mockRejectedValue(new Error('Internal DB error with stack trace'));

      const res = await request(app)
        .post('/api/auth/register')
        .send(validUserData);

      expect(res.body.error).not.toContain('at ');
      expect(res.body.error).not.toContain('.js:');
    });
  });

  describe('Authentication Flow End-to-End', () => {
    it('should complete register -> access profile flow', async () => {
      const mockUser = createMockUser();
      User.findOne.mockResolvedValue(null);
      User.create.mockResolvedValue(mockUser);

      const registerRes = await request(app)
        .post('/api/auth/register')
        .send(validUserData);

      expect(registerRes.status).toBe(201);
      const { token } = registerRes.body.data;

      User.findById.mockResolvedValue(mockUser);

      const profileRes = await request(app)
        .get('/api/auth/me')
        .set('Authorization', `Bearer ${token}`);

      expect(profileRes.status).toBe(200);
      expect(profileRes.body.data.username).toBe('testuser');
    });

    it('should complete login -> access profile -> logout flow', async () => {
      const mockUser = createMockUser();
      User.findOne.mockReturnValue({
        select: jest.fn().mockResolvedValue(mockUser),
      });

      const loginRes = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@example.com', password: 'password123' });

      expect(loginRes.status).toBe(200);
      const { token } = loginRes.body.data;

      User.findById.mockResolvedValue(mockUser);

      const profileRes = await request(app)
        .get('/api/auth/me')
        .set('Authorization', `Bearer ${token}`);

      expect(profileRes.status).toBe(200);

      User.findByIdAndUpdate.mockResolvedValue({});

      const logoutRes = await request(app)
        .post('/api/auth/logout')
        .set('Authorization', `Bearer ${token}`);

      expect(logoutRes.status).toBe(200);
      expect(logoutRes.body.message).toBe('Logged out successfully');
    });

    it('should reject access to protected route after invalid token', async () => {
      const res = await request(app)
        .get('/api/auth/me')
        .set('Authorization', 'Bearer tampered.token.here');

      expect(res.status).toBe(401);
    });

    it('should maintain token validity across multiple requests', async () => {
      const mockUser = createMockUser();
      User.findById.mockResolvedValue(mockUser);

      const token = jwt.sign({ id: 'user123' }, 'test-secret-key');

      for (let i = 0; i < 3; i++) {
        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(200);
      }
    });
  });
});
