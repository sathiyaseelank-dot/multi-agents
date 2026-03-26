const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

jest.mock('bcryptjs', () => ({
  genSalt: jest.fn().mockResolvedValue('salt'),
  hash: jest.fn().mockResolvedValue('hashedpassword'),
  compare: jest.fn().mockResolvedValue(true),
}));

const User = require('../models/User');

describe('User Model', () => {
  describe('Schema Validation', () => {
    it('should require username', async () => {
      const user = new User({ email: 'test@test.com', password: 'password123' });
      const error = user.validateSync();
      expect(error.errors.username).toBeDefined();
      expect(error.errors.username.message).toBe('Username is required');
    });

    it('should require email', async () => {
      const user = new User({ username: 'testuser', password: 'password123' });
      const error = user.validateSync();
      expect(error.errors.email).toBeDefined();
      expect(error.errors.email.message).toBe('Email is required');
    });

    it('should require password', async () => {
      const user = new User({ username: 'testuser', email: 'test@test.com' });
      const error = user.validateSync();
      expect(error.errors.password).toBeDefined();
      expect(error.errors.password.message).toBe('Password is required');
    });

    it('should be valid with all required fields', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });
      const error = user.validateSync();
      expect(error).toBeUndefined();
    });

    it('should reject username shorter than 3 characters', () => {
      const user = new User({
        username: 'ab',
        email: 'test@test.com',
        password: 'password123',
      });
      const error = user.validateSync();
      expect(error.errors.username).toBeDefined();
      expect(error.errors.username.message).toBe('Username must be at least 3 characters');
    });

    it('should reject username longer than 30 characters', () => {
      const user = new User({
        username: 'a'.repeat(31),
        email: 'test@test.com',
        password: 'password123',
      });
      const error = user.validateSync();
      expect(error.errors.username).toBeDefined();
      expect(error.errors.username.message).toBe('Username cannot exceed 30 characters');
    });

    it('should reject password shorter than 6 characters', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: '12345',
      });
      const error = user.validateSync();
      expect(error.errors.password).toBeDefined();
      expect(error.errors.password.message).toBe('Password must be at least 6 characters');
    });

    it('should reject invalid email format', () => {
      const user = new User({
        username: 'testuser',
        email: 'invalidemail',
        password: 'password123',
      });
      const error = user.validateSync();
      expect(error.errors.email).toBeDefined();
      expect(error.errors.email.message).toBe('Please provide a valid email');
    });

    it('should reject email without @ symbol', () => {
      const user = new User({
        username: 'testuser',
        email: 'testtest.com',
        password: 'password123',
      });
      const error = user.validateSync();
      expect(error.errors.email).toBeDefined();
    });

    it('should accept valid email with various TLDs', () => {
      const validEmails = [
        'user@example.com',
        'user.name@example.co.uk',
        'user+tag@example.org',
      ];

      validEmails.forEach((email) => {
        const user = new User({
          username: 'testuser',
          email,
          password: 'password123',
        });
        const error = user.validateSync();
        expect(error).toBeUndefined();
      });
    });

    it('should trim whitespace from username', () => {
      const user = new User({
        username: '  testuser  ',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(user.username).toBe('testuser');
    });

    it('should lowercase email', () => {
      const user = new User({
        username: 'testuser',
        email: 'Test@Test.COM',
        password: 'password123',
      });
      expect(user.email).toBe('test@test.com');
    });
  });

  describe('Default Values', () => {
    it('should set default avatar to null', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(user.avatar).toBeNull();
    });

    it('should set default status to offline', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(user.status).toBe('offline');
    });

    it('should set default lastSeen to current date', () => {
      const before = new Date();
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });
      const after = new Date();
      expect(user.lastSeen).toBeInstanceOf(Date);
      expect(user.lastSeen.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(user.lastSeen.getTime()).toBeLessThanOrEqual(after.getTime());
    });

    it('should have empty conversations array by default', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(user.conversations).toEqual([]);
    });
  });

  describe('Status Enum', () => {
    it('should accept online status', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
        status: 'online',
      });
      expect(user.status).toBe('online');
    });

    it('should accept offline status', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
        status: 'offline',
      });
      expect(user.status).toBe('offline');
    });

    it('should accept away status', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
        status: 'away',
      });
      expect(user.status).toBe('away');
    });

    it('should reject invalid status', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
        status: 'busy',
      });
      const error = user.validateSync();
      expect(error.errors.status).toBeDefined();
    });
  });

  describe('Timestamps', () => {
    it('should have timestamps enabled', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });
      expect(user.schema.options.timestamps).toBe(true);
    });
  });

  describe('Password Hashing (pre-save hook)', () => {
    it('should hash password before saving when password is modified', async () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });

      user.isModified = jest.fn().mockReturnValue(true);
      const next = jest.fn();
      const preSaveHooks = user.schema.s.hooks._pres.get('save');
      const passwordHook = preSaveHooks.find(
        (hook) => hook.fn.toString().includes('bcrypt')
      );
      await passwordHook.fn.call(user, next);

      expect(bcrypt.genSalt).toHaveBeenCalledWith(10);
      expect(bcrypt.hash).toHaveBeenCalledWith('password123', 'salt');
    });

    it('should not hash password when password is not modified', async () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });

      bcrypt.genSalt.mockClear();
      bcrypt.hash.mockClear();

      user.isModified = jest.fn().mockReturnValue(false);
      const next = jest.fn();
      const preSaveHooks = user.schema.s.hooks._pres.get('save');
      const passwordHook = preSaveHooks.find(
        (hook) => hook.fn.toString().includes('bcrypt')
      );
      await passwordHook.fn.call(user, next);

      expect(bcrypt.genSalt).not.toHaveBeenCalled();
      expect(next).toHaveBeenCalled();
    });
  });

  describe('matchPassword method', () => {
    it('should call bcrypt.compare with correct arguments', async () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'hashedpassword',
      });

      const result = await user.matchPassword('password123');

      expect(bcrypt.compare).toHaveBeenCalledWith('password123', 'hashedpassword');
      expect(result).toBe(true);
    });

    it('should return false for wrong password', async () => {
      bcrypt.compare.mockResolvedValueOnce(false);

      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'hashedpassword',
      });

      const result = await user.matchPassword('wrongpassword');

      expect(result).toBe(false);
    });
  });

  describe('toJSON method', () => {
    it('should exclude password from JSON output', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });

      user.toObject = jest.fn().mockReturnValue({
        _id: 'mockId',
        username: 'testuser',
        email: 'test@test.com',
        password: 'hashedpassword',
        status: 'offline',
      });

      const json = user.toJSON();

      expect(json.password).toBeUndefined();
      expect(json.username).toBe('testuser');
      expect(json.email).toBe('test@test.com');
    });

    it('should preserve non-sensitive fields in JSON output', () => {
      const user = new User({
        username: 'testuser',
        email: 'test@test.com',
        password: 'password123',
      });

      user.toObject = jest.fn().mockReturnValue({
        _id: 'mockId',
        username: 'testuser',
        email: 'test@test.com',
        password: 'hashedpassword',
        avatar: 'http://example.com/avatar.png',
        status: 'online',
      });

      const json = user.toJSON();

      expect(json.avatar).toBe('http://example.com/avatar.png');
      expect(json.status).toBe('online');
      expect(json._id).toBe('mockId');
    });
  });

  describe('Conversations reference', () => {
    it('should have conversations as ObjectId array referencing Conversation', () => {
      const conversationPath = User.schema.path('conversations');
      expect(conversationPath).toBeDefined();
      expect(conversationPath.instance).toBe('Array');
    });
  });
});
