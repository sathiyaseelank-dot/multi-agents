const mongoose = require('mongoose');
const Session = require('../models/Session');

describe('Session Model', () => {
  describe('Schema Validation', () => {
    it('should require user reference', () => {
      const session = new Session({
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      const error = session.validateSync();
      expect(error.errors.user).toBeDefined();
    });

    it('should require token', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        expiresAt: new Date(Date.now() + 3600000),
      });
      const error = session.validateSync();
      expect(error.errors.token).toBeDefined();
    });

    it('should require expiresAt', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
      });
      const error = session.validateSync();
      expect(error.errors.expiresAt).toBeDefined();
    });

    it('should be valid with all required fields', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      const error = session.validateSync();
      expect(error).toBeUndefined();
    });

    it('should accept user as ObjectId', () => {
      const userId = new mongoose.Types.ObjectId();
      const session = new Session({
        user: userId,
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      expect(session.user).toEqual(userId);
    });

    it('should accept token as string', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test',
        expiresAt: new Date(Date.now() + 3600000),
      });
      expect(session.token).toBe('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test');
    });

    it('should accept expiresAt as Date', () => {
      const expiry = new Date(Date.now() + 3600000);
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: expiry,
      });
      expect(session.expiresAt).toEqual(expiry);
    });
  });

  describe('Default Values', () => {
    it('should set deviceInfo to Unknown by default', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      expect(session.deviceInfo).toBe('Unknown');
    });

    it('should set isRevoked to false by default', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      expect(session.isRevoked).toBe(false);
    });

    it('should set ipAddress to undefined by default', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      expect(session.ipAddress).toBeUndefined();
    });

    it('should set userAgent to undefined by default', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });
      expect(session.userAgent).toBeUndefined();
    });
  });

  describe('Optional Fields', () => {
    it('should accept custom deviceInfo', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
        deviceInfo: 'Chrome on Windows',
      });
      expect(session.deviceInfo).toBe('Chrome on Windows');
    });

    it('should accept ipAddress', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
        ipAddress: '192.168.1.1',
      });
      expect(session.ipAddress).toBe('192.168.1.1');
    });

    it('should accept IPv6 ipAddress', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
        ipAddress: '::1',
      });
      expect(session.ipAddress).toBe('::1');
    });

    it('should accept userAgent string', () => {
      const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
        userAgent: ua,
      });
      expect(session.userAgent).toBe(ua);
    });

    it('should accept isRevoked as true', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
        isRevoked: true,
      });
      expect(session.isRevoked).toBe(true);
    });
  });

  describe('Timestamps', () => {
    it('should have timestamps enabled', () => {
      expect(Session.schema.options.timestamps).toBe(true);
    });
  });

  describe('Indexes', () => {
    it('should have TTL index on expiresAt', () => {
      const indexes = Session.schema.indexes();
      const hasTTLIndex = indexes.some(
        (idx) => idx[0].expiresAt === 1 && idx[1] && idx[1].expireAfterSeconds === 0
      );
      expect(hasTTLIndex).toBe(true);
    });

    it('should have index on user', () => {
      const indexes = Session.schema.indexes();
      const hasUserIndex = indexes.some((idx) => idx[0].user === 1);
      expect(hasUserIndex).toBe(true);
    });

    it('should have index on token', () => {
      const indexes = Session.schema.indexes();
      const hasTokenIndex = indexes.some((idx) => idx[0].token === 1);
      expect(hasTokenIndex).toBe(true);
    });
  });

  describe('Unique Constraints', () => {
    it('should have unique constraint on token', () => {
      const tokenPath = Session.schema.path('token');
      expect(tokenPath.options.unique).toBe(true);
    });
  });

  describe('User Reference', () => {
    it('should reference User model in user field', () => {
      const userPath = Session.schema.path('user');
      expect(userPath.options.ref).toBe('User');
    });

    it('should store ObjectId in user field', () => {
      const userPath = Session.schema.path('user');
      expect(userPath.instance).toBe('ObjectId');
    });
  });

  describe('Session Revocation', () => {
    it('should allow marking session as revoked', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
      });

      session.isRevoked = true;
      expect(session.isRevoked).toBe(true);
    });

    it('should allow creating session then revoking it', () => {
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: new Date(Date.now() + 3600000),
        isRevoked: false,
      });

      expect(session.isRevoked).toBe(false);
      session.isRevoked = true;
      expect(session.isRevoked).toBe(true);
    });
  });

  describe('Session Expiration', () => {
    it('should store future expiration date', () => {
      const futureDate = new Date(Date.now() + 86400000);
      const session = new Session({
        user: new mongoose.Types.ObjectId(),
        token: 'jwt-token-string',
        expiresAt: futureDate,
      });
      expect(session.expiresAt.getTime()).toBe(futureDate.getTime());
    });

    it('should accept various expiration durations', () => {
      const durations = [
        new Date(Date.now() + 3600000),
        new Date(Date.now() + 86400000),
        new Date(Date.now() + 604800000),
      ];

      durations.forEach((expiresAt) => {
        const session = new Session({
          user: new mongoose.Types.ObjectId(),
          token: `token-${expiresAt.getTime()}`,
          expiresAt,
        });
        const error = session.validateSync();
        expect(error).toBeUndefined();
      });
    });
  });
});
