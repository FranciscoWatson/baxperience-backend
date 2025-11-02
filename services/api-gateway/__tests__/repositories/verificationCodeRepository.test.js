const verificationCodeRepository = require('../../src/repositories/verificationCodeRepository');
const pool = require('../../src/config/database');

jest.mock('../../src/config/database');

describe('VerificationCodeRepository', () => {
  let mockQuery;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockQuery = jest.fn();
    pool.query = mockQuery;
  });

  describe('generateCode', () => {
    it('should generate 6-digit code by default', () => {
      const code = verificationCodeRepository.generateCode();

      expect(code).toHaveLength(6);
      expect(code).toMatch(/^\d{6}$/);
    });

    it('should generate code of specified length', () => {
      const code = verificationCodeRepository.generateCode(8);

      expect(code).toHaveLength(8);
      expect(code).toMatch(/^\d{8}$/);
    });

    it('should generate numeric codes only', () => {
      const code = verificationCodeRepository.generateCode(10);

      expect(code).toMatch(/^\d+$/);
    });

    it('should generate different codes on consecutive calls', () => {
      const code1 = verificationCodeRepository.generateCode();
      const code2 = verificationCodeRepository.generateCode();

      // Very unlikely to be the same
      expect(code1).not.toBe(code2);
    });

    it('should handle edge case of length 1', () => {
      const code = verificationCodeRepository.generateCode(1);

      expect(code).toHaveLength(1);
      expect(code).toMatch(/^\d$/);
    });

    it('should generate codes in valid range', () => {
      for (let i = 0; i < 100; i++) {
        const code = verificationCodeRepository.generateCode(6);
        const codeNum = parseInt(code, 10);
        
        expect(codeNum).toBeGreaterThanOrEqual(0);
        expect(codeNum).toBeLessThan(1000000);
      }
    });
  });

  describe('createCode', () => {
    it('should create verification code successfully', async () => {
      const mockCode = {
        id: 1,
        email: 'test@example.com',
        code: '123456',
        type: 'registration',
        created_at: new Date()
      };

      mockQuery.mockResolvedValue({ rows: [mockCode] });

      const result = await verificationCodeRepository.createCode(
        'test@example.com',
        'registration',
        '127.0.0.1'
      );

      expect(result).toEqual(mockCode);
      expect(mockQuery).toHaveBeenCalled();
    });

    it('should include ip_address in query', async () => {
      mockQuery.mockResolvedValue({ rows: [{}] });

      await verificationCodeRepository.createCode(
        'test@example.com',
        'registration',
        '192.168.1.1'
      );

      const queryArgs = mockQuery.mock.calls[0][1];
      expect(queryArgs).toContain('192.168.1.1');
    });

    it('should use correct expiry time from environment', async () => {
      mockQuery.mockResolvedValue({ rows: [{}] });

      await verificationCodeRepository.createCode(
        'test@example.com',
        'registration'
      );

      const query = mockQuery.mock.calls[0][0];
      const expiryMinutes = process.env.VERIFICATION_CODE_EXPIRY_MINUTES || '15';
      expect(query).toContain(`${expiryMinutes} minutes`);
    });

    it('should handle database errors', async () => {
      mockQuery.mockRejectedValue(new Error('Database error'));

      await expect(
        verificationCodeRepository.createCode('test@example.com', 'registration')
      ).rejects.toThrow('Database error');
    });

    it('should work without ip_address', async () => {
      mockQuery.mockResolvedValue({ rows: [{ id: 1 }] });

      const result = await verificationCodeRepository.createCode(
        'test@example.com',
        'registration'
      );

      expect(result).toBeDefined();
      expect(mockQuery).toHaveBeenCalled();
    });

    it('should generate unique codes for different types', async () => {
      mockQuery.mockResolvedValue({ rows: [{ id: 1 }] });

      await verificationCodeRepository.createCode('test@example.com', 'registration');
      await verificationCodeRepository.createCode('test@example.com', 'password_reset');

      expect(mockQuery).toHaveBeenCalledTimes(2);
    });
  });

  describe('verifyCode', () => {
    it('should verify valid code successfully', async () => {
      const mockCodeData = {
        id: 1,
        email: 'test@example.com',
        code: '123456',
        type: 'registration'
      };

      mockQuery
        .mockResolvedValueOnce({ rows: [mockCodeData] }) // SELECT query
        .mockResolvedValueOnce({ rows: [] }); // UPDATE query

      const result = await verificationCodeRepository.verifyCode(
        'test@example.com',
        '123456',
        'registration'
      );

      expect(result).toEqual({
        valid: true,
        data: mockCodeData
      });
      expect(mockQuery).toHaveBeenCalledTimes(2); // SELECT + UPDATE
    });

    it('should return invalid for non-existent code', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      const result = await verificationCodeRepository.verifyCode(
        'test@example.com',
        'invalid',
        'registration'
      );

      expect(result).toEqual({
        valid: false,
        error: 'Invalid or expired code'
      });
    });

    it('should mark code as used after verification', async () => {
      const mockCodeData = { id: 5 };
      mockQuery
        .mockResolvedValueOnce({ rows: [mockCodeData] })
        .mockResolvedValueOnce({ rows: [] });

      await verificationCodeRepository.verifyCode(
        'test@example.com',
        '123456',
        'registration'
      );

      const updateQuery = mockQuery.mock.calls[1][0];
      expect(updateQuery).toContain('UPDATE verification_codes');
      expect(updateQuery).toContain('is_used = TRUE');
    });

    it('should query for non-used and non-expired codes', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await verificationCodeRepository.verifyCode(
        'test@example.com',
        '123456',
        'registration'
      );

      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('is_used = FALSE');
      expect(query).toContain('expires_at > NOW()');
    });

    it('should handle database errors', async () => {
      mockQuery.mockRejectedValue(new Error('Database error'));

      await expect(
        verificationCodeRepository.verifyCode('test@example.com', '123456', 'registration')
      ).rejects.toThrow('Database error');
    });

    it('should use most recent code when multiple exist', async () => {
      mockQuery.mockResolvedValue({ rows: [{ id: 1 }] });

      await verificationCodeRepository.verifyCode(
        'test@example.com',
        '123456',
        'registration'
      );

      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('ORDER BY created_at DESC');
      expect(query).toContain('LIMIT 1');
    });
  });

  describe('markCodeAsUsed', () => {
    it('should mark code as used', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await verificationCodeRepository.markCodeAsUsed(1);

      expect(mockQuery).toHaveBeenCalled();
      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('UPDATE verification_codes');
      expect(query).toContain('is_used = TRUE');
      expect(query).toContain('used_at = NOW()');
    });

    it('should use correct code ID', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await verificationCodeRepository.markCodeAsUsed(42);

      const queryArgs = mockQuery.mock.calls[0][1];
      expect(queryArgs).toContain(42);
    });

    it('should handle database errors', async () => {
      mockQuery.mockRejectedValue(new Error('Database error'));

      await expect(
        verificationCodeRepository.markCodeAsUsed(1)
      ).rejects.toThrow('Database error');
    });
  });

  describe('invalidatePreviousCodes', () => {
    it('should invalidate all previous codes', async () => {
      mockQuery.mockResolvedValue({ rowCount: 3 });

      const result = await verificationCodeRepository.invalidatePreviousCodes(
        'test@example.com',
        'registration'
      );

      expect(result).toBe(3);
      expect(mockQuery).toHaveBeenCalled();
    });

    it('should only invalidate unused codes', async () => {
      mockQuery.mockResolvedValue({ rowCount: 2 });

      await verificationCodeRepository.invalidatePreviousCodes(
        'test@example.com',
        'registration'
      );

      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('is_used = FALSE');
    });

    it('should filter by email and type', async () => {
      mockQuery.mockResolvedValue({ rowCount: 1 });

      await verificationCodeRepository.invalidatePreviousCodes(
        'test@example.com',
        'password_reset'
      );

      const queryArgs = mockQuery.mock.calls[0][1];
      expect(queryArgs).toContain('test@example.com');
      expect(queryArgs).toContain('password_reset');
    });

    it('should return 0 if no codes to invalidate', async () => {
      mockQuery.mockResolvedValue({ rowCount: 0 });

      const result = await verificationCodeRepository.invalidatePreviousCodes(
        'test@example.com',
        'registration'
      );

      expect(result).toBe(0);
    });

    it('should handle database errors', async () => {
      mockQuery.mockRejectedValue(new Error('Database error'));

      await expect(
        verificationCodeRepository.invalidatePreviousCodes('test@example.com', 'registration')
      ).rejects.toThrow('Database error');
    });
  });

  describe('getRecentCode', () => {
    it('should get most recent code', async () => {
      const mockCode = {
        id: 1,
        email: 'test@example.com',
        code: '123456',
        created_at: new Date()
      };

      mockQuery.mockResolvedValue({ rows: [mockCode] });

      const result = await verificationCodeRepository.getRecentCode(
        'test@example.com',
        'registration'
      );

      expect(result).toEqual(mockCode);
    });

    it('should return null if no codes exist', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      const result = await verificationCodeRepository.getRecentCode(
        'test@example.com',
        'registration'
      );

      expect(result).toBeNull();
    });

    it('should order by created_at DESC', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await verificationCodeRepository.getRecentCode(
        'test@example.com',
        'registration'
      );

      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('ORDER BY created_at DESC');
    });

    it('should limit to 1 result', async () => {
      mockQuery.mockResolvedValue({ rows: [] });

      await verificationCodeRepository.getRecentCode(
        'test@example.com',
        'registration'
      );

      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('LIMIT 1');
    });

    it('should handle database errors', async () => {
      mockQuery.mockRejectedValue(new Error('Database error'));

      await expect(
        verificationCodeRepository.getRecentCode('test@example.com', 'registration')
      ).rejects.toThrow('Database error');
    });
  });

  describe('cleanupExpiredCodes', () => {
    it('should delete expired codes', async () => {
      mockQuery.mockResolvedValue({ rowCount: 5 });

      const result = await verificationCodeRepository.cleanupExpiredCodes();

      expect(result).toBe(5);
      expect(mockQuery).toHaveBeenCalled();
    });

    it('should only delete expired and unused codes', async () => {
      mockQuery.mockResolvedValue({ rowCount: 3 });

      await verificationCodeRepository.cleanupExpiredCodes();

      const query = mockQuery.mock.calls[0][0];
      expect(query).toContain('DELETE FROM verification_codes');
      expect(query).toContain('expires_at < NOW()');
      expect(query).toContain('is_used = FALSE');
    });

    it('should return 0 if no codes to cleanup', async () => {
      mockQuery.mockResolvedValue({ rowCount: 0 });

      const result = await verificationCodeRepository.cleanupExpiredCodes();

      expect(result).toBe(0);
    });

    it('should handle database errors', async () => {
      mockQuery.mockRejectedValue(new Error('Database error'));

      await expect(
        verificationCodeRepository.cleanupExpiredCodes()
      ).rejects.toThrow('Database error');
    });
  });

  describe('Integration scenarios', () => {
    it('should handle complete verification flow', async () => {
      // Create code
      mockQuery.mockResolvedValueOnce({
        rows: [{ id: 1, code: '123456' }]
      });

      const created = await verificationCodeRepository.createCode(
        'test@example.com',
        'registration'
      );

      // Verify code
      mockQuery
        .mockResolvedValueOnce({ rows: [created] })
        .mockResolvedValueOnce({ rows: [] });

      const verified = await verificationCodeRepository.verifyCode(
        'test@example.com',
        created.code,
        'registration'
      );

      expect(verified.valid).toBe(true);
    });

    it('should handle rate limiting scenario', async () => {
      // Get recent code
      mockQuery.mockResolvedValueOnce({
        rows: [{
          id: 1,
          created_at: new Date()
        }]
      });

      const recent = await verificationCodeRepository.getRecentCode(
        'test@example.com',
        'registration'
      );

      expect(recent).toBeDefined();
      expect(recent.created_at).toBeDefined();
    });

    it('should handle invalidation before creating new code', async () => {
      // Invalidate previous
      mockQuery.mockResolvedValueOnce({ rowCount: 2 });
      
      await verificationCodeRepository.invalidatePreviousCodes(
        'test@example.com',
        'registration'
      );

      // Create new
      mockQuery.mockResolvedValueOnce({
        rows: [{ id: 3, code: '654321' }]
      });

      const created = await verificationCodeRepository.createCode(
        'test@example.com',
        'registration'
      );

      expect(created).toBeDefined();
      expect(mockQuery).toHaveBeenCalledTimes(2);
    });
  });

  describe('Edge cases', () => {
    it('should handle special characters in email', async () => {
      mockQuery.mockResolvedValue({ rows: [{ id: 1 }] });

      await verificationCodeRepository.createCode(
        'test+tag@example.com',
        'registration'
      );

      const queryArgs = mockQuery.mock.calls[0][1];
      expect(queryArgs).toContain('test+tag@example.com');
    });

    it('should handle very long email addresses', async () => {
      const longEmail = 'a'.repeat(100) + '@example.com';
      mockQuery.mockResolvedValue({ rows: [{ id: 1 }] });

      await verificationCodeRepository.createCode(longEmail, 'registration');

      expect(mockQuery).toHaveBeenCalled();
    });

    it('should handle concurrent code generation', () => {
      const codes = [];
      for (let i = 0; i < 100; i++) {
        codes.push(verificationCodeRepository.generateCode());
      }

      const uniqueCodes = new Set(codes);
      // Most should be unique (allow some duplicates due to randomness)
      expect(uniqueCodes.size).toBeGreaterThan(90);
    });
  });
});
