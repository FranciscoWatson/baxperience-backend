const authMiddleware = require('../../src/middleware/auth');
const jwt = require('jsonwebtoken');

jest.mock('jsonwebtoken');

describe('Auth Middleware', () => {
  let req, res, next;

  beforeEach(() => {
    jest.clearAllMocks();

    req = {
      header: jest.fn()
    };

    res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis()
    };

    next = jest.fn();
  });

  describe('Token validation', () => {
    it('should call next() with valid token', () => {
      const mockDecoded = {
        userId: 1,
        email: 'test@example.com'
      };

      req.header.mockReturnValue('Bearer valid_token');
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith('valid_token', process.env.JWT_SECRET);
      expect(req.user).toEqual(mockDecoded);
      expect(next).toHaveBeenCalled();
      expect(res.status).not.toHaveBeenCalled();
    });

    it('should handle token without Bearer prefix', () => {
      const mockDecoded = {
        userId: 1,
        email: 'test@example.com'
      };

      req.header.mockReturnValue('valid_token');
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith('valid_token', process.env.JWT_SECRET);
      expect(req.user).toEqual(mockDecoded);
      expect(next).toHaveBeenCalled();
    });

    it('should return 401 if no token provided', () => {
      req.header.mockReturnValue(undefined);

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Access denied. No token provided.'
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should handle Authorization header with only "Bearer"', () => {
      req.header.mockReturnValue('Bearer');
      jwt.verify.mockImplementation(() => {
        throw new Error('jwt must be provided');
      });

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid token.'
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 if token is invalid', () => {
      req.header.mockReturnValue('Bearer invalid_token');
      jwt.verify.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid token.'
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 if token is expired', () => {
      req.header.mockReturnValue('Bearer expired_token');
      jwt.verify.mockImplementation(() => {
        const error = new Error('Token expired');
        error.name = 'TokenExpiredError';
        throw error;
      });

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid token.'
      });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 if token has invalid signature', () => {
      req.header.mockReturnValue('Bearer malformed_token');
      jwt.verify.mockImplementation(() => {
        const error = new Error('Invalid signature');
        error.name = 'JsonWebTokenError';
        throw error;
      });

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid token.'
      });
      expect(next).not.toHaveBeenCalled();
    });
  });

  describe('Token extraction', () => {
    it('should extract token correctly from Authorization header with Bearer', () => {
      const mockDecoded = { userId: 1 };
      req.header.mockReturnValue('Bearer test_token_12345');
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith('test_token_12345', process.env.JWT_SECRET);
      expect(next).toHaveBeenCalled();
    });

    it('should handle multiple spaces after Bearer', () => {
      const mockDecoded = { userId: 1 };
      req.header.mockReturnValue('Bearer   test_token');
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith('  test_token', process.env.JWT_SECRET);
    });
  });

  describe('User data attachment', () => {
    it('should attach decoded user data to request object', () => {
      const mockDecoded = {
        userId: 123,
        email: 'user@example.com',
        role: 'user',
        iat: 1234567890,
        exp: 1234571490
      };

      req.header.mockReturnValue('Bearer valid_token');
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(req.user).toEqual(mockDecoded);
      expect(req.user.userId).toBe(123);
      expect(req.user.email).toBe('user@example.com');
    });

    it('should not modify request object if token is invalid', () => {
      req.header.mockReturnValue('Bearer invalid_token');
      jwt.verify.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      authMiddleware(req, res, next);

      expect(req.user).toBeUndefined();
    });
  });

  describe('Edge cases', () => {
    it('should handle null Authorization header', () => {
      req.header.mockReturnValue(null);

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Access denied. No token provided.'
      });
    });

    it('should handle very long tokens', () => {
      const longToken = 'a'.repeat(2000);
      const mockDecoded = { userId: 1 };
      
      req.header.mockReturnValue(`Bearer ${longToken}`);
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith(longToken, process.env.JWT_SECRET);
      expect(next).toHaveBeenCalled();
    });

    it('should handle tokens with special characters', () => {
      const specialToken = 'token.with.dots-and_underscores';
      const mockDecoded = { userId: 1 };
      
      req.header.mockReturnValue(`Bearer ${specialToken}`);
      jwt.verify.mockReturnValue(mockDecoded);

      authMiddleware(req, res, next);

      expect(jwt.verify).toHaveBeenCalledWith(specialToken, process.env.JWT_SECRET);
      expect(next).toHaveBeenCalled();
    });
  });

  describe('Response format', () => {
    it('should return consistent error format for missing token', () => {
      req.header.mockReturnValue(undefined);

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.any(String)
        })
      );
    });

    it('should return consistent error format for invalid token', () => {
      req.header.mockReturnValue('Bearer invalid_token');
      jwt.verify.mockImplementation(() => {
        throw new Error('Invalid');
      });

      authMiddleware(req, res, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.any(String)
        })
      );
    });
  });
});
