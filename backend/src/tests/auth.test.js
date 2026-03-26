const jwt = require('jsonwebtoken');
const { protect } = require('../middleware/auth');

jest.mock('jsonwebtoken', () => ({
  verify: jest.fn(),
}));

describe('Auth Middleware (protect)', () => {
  let req, res, next;

  beforeEach(() => {
    req = {
      headers: {},
      user: null,
    };
    res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
    };
    next = jest.fn();
    process.env.JWT_SECRET = 'test-secret';
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Token Extraction', () => {
    it('should reject request with no authorization header', () => {
      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Not authorized, no token provided',
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should reject request with empty authorization header', () => {
      req.headers.authorization = '';

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(next).not.toHaveBeenCalled();
    });

    it('should reject request with non-Bearer authorization', () => {
      req.headers.authorization = 'Basic sometoken';

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(next).not.toHaveBeenCalled();
    });

    it('should extract token from Bearer authorization header', () => {
      req.headers.authorization = 'Bearer valid.jwt.token';
      jwt.verify.mockReturnValue({ id: 'user123' });

      protect(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith('valid.jwt.token', 'test-secret');
    });

    it('should handle Bearer token with extra spaces', () => {
      req.headers.authorization = 'Bearer  token.with.spaces';

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
    });
  });

  describe('Token Verification', () => {
    it('should call next() with valid token', () => {
      req.headers.authorization = 'Bearer valid.jwt.token';
      const decoded = { id: 'user123' };
      jwt.verify.mockReturnValue(decoded);

      protect(req, res, next);

      expect(req.user).toEqual(decoded);
      expect(next).toHaveBeenCalled();
    });

    it('should attach decoded user to req.user', () => {
      req.headers.authorization = 'Bearer valid.jwt.token';
      const decoded = { id: 'user123', username: 'testuser' };
      jwt.verify.mockReturnValue(decoded);

      protect(req, res, next);

      expect(req.user).toEqual(decoded);
      expect(req.user.id).toBe('user123');
    });

    it('should use JWT_SECRET from environment', () => {
      process.env.JWT_SECRET = 'my-custom-secret';
      req.headers.authorization = 'Bearer valid.jwt.token';
      jwt.verify.mockReturnValue({ id: 'user123' });

      protect(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith('valid.jwt.token', 'my-custom-secret');
    });
  });

  describe('Invalid Token Handling', () => {
    it('should reject request with invalid token', () => {
      req.headers.authorization = 'Bearer invalid.token';
      jwt.verify.mockImplementation(() => {
        throw new Error('jwt malformed');
      });

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Not authorized, token invalid',
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should reject request with expired token', () => {
      req.headers.authorization = 'Bearer expired.token';
      jwt.verify.mockImplementation(() => {
        const err = new Error('jwt expired');
        err.name = 'TokenExpiredError';
        throw err;
      });

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Not authorized, token invalid',
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should reject request with token signed with wrong secret', () => {
      req.headers.authorization = 'Bearer wrongsecret.token';
      jwt.verify.mockImplementation(() => {
        throw new Error('invalid signature');
      });

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Not authorized, token invalid',
      });
    });

    it('should not call next() on token verification failure', () => {
      req.headers.authorization = 'Bearer bad.token';
      jwt.verify.mockImplementation(() => {
        throw new Error('any error');
      });

      protect(req, res, next);

      expect(next).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined authorization header', () => {
      req.headers.authorization = undefined;

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(next).not.toHaveBeenCalled();
    });

    it('should handle Bearer with only whitespace token', () => {
      req.headers.authorization = 'Bearer   ';

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(next).not.toHaveBeenCalled();
    });

    it('should handle lowercase bearer prefix', () => {
      req.headers.authorization = 'bearer valid.token';

      protect(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(next).not.toHaveBeenCalled();
    });
  });
});
