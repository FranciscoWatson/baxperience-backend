const pool = require('../config/database');

/**
 * Verification Code Repository
 * Handles database operations for verification codes
 */
class VerificationCodeRepository {
  /**
   * Generate a random verification code
   */
  generateCode(length = 6) {
    const digits = '0123456789';
    let code = '';
    for (let i = 0; i < length; i++) {
      code += digits[Math.floor(Math.random() * digits.length)];
    }
    return code;
  }

  /**
   * Create a new verification code
   */
  async createCode(email, type, ipAddress = null) {
    const code = this.generateCode(
      parseInt(process.env.VERIFICATION_CODE_LENGTH || '6')
    );
    
    const expiryMinutes = parseInt(
      process.env.VERIFICATION_CODE_EXPIRY_MINUTES || '15'
    );
    
    const query = `
      INSERT INTO verification_codes 
      (email, code, type, expires_at, ip_address)
      VALUES ($1, $2, $3, NOW() + INTERVAL '${expiryMinutes} minutes', $4)
      RETURNING *
    `;
    
    try {
      const result = await pool.query(query, [email, code, type, ipAddress]);
      console.log(`✅ Verification code created for ${email} (${type})`);
      return result.rows[0];
    } catch (error) {
      console.error('❌ Error creating verification code:', error);
      throw error;
    }
  }

  /**
   * Verify a code
   */
  async verifyCode(email, code, type) {
    const query = `
      SELECT * FROM verification_codes
      WHERE email = $1 
        AND code = $2 
        AND type = $3
        AND is_used = FALSE
        AND expires_at > NOW()
      ORDER BY created_at DESC
      LIMIT 1
    `;
    
    try {
      const result = await pool.query(query, [email, code, type]);
      
      if (result.rows.length === 0) {
        return { valid: false, error: 'Invalid or expired code' };
      }
      
      // Mark code as used
      await this.markCodeAsUsed(result.rows[0].id);
      
      console.log(`✅ Code verified for ${email} (${type})`);
      return { valid: true, data: result.rows[0] };
    } catch (error) {
      console.error('❌ Error verifying code:', error);
      throw error;
    }
  }

  /**
   * Mark a code as used
   */
  async markCodeAsUsed(codeId) {
    const query = `
      UPDATE verification_codes
      SET is_used = TRUE, used_at = NOW()
      WHERE id = $1
    `;
    
    try {
      await pool.query(query, [codeId]);
      console.log(`✅ Code ${codeId} marked as used`);
    } catch (error) {
      console.error('❌ Error marking code as used:', error);
      throw error;
    }
  }

  /**
   * Invalidate all previous codes for an email and type
   */
  async invalidatePreviousCodes(email, type) {
    const query = `
      UPDATE verification_codes
      SET is_used = TRUE
      WHERE email = $1 
        AND type = $2
        AND is_used = FALSE
    `;
    
    try {
      const result = await pool.query(query, [email, type]);
      console.log(`✅ Invalidated ${result.rowCount} previous codes for ${email}`);
      return result.rowCount;
    } catch (error) {
      console.error('❌ Error invalidating codes:', error);
      throw error;
    }
  }

  /**
   * Get recent code for email (for rate limiting)
   */
  async getRecentCode(email, type) {
    const query = `
      SELECT * FROM verification_codes
      WHERE email = $1 
        AND type = $2
      ORDER BY created_at DESC
      LIMIT 1
    `;
    
    try {
      const result = await pool.query(query, [email, type]);
      return result.rows[0] || null;
    } catch (error) {
      console.error('❌ Error getting recent code:', error);
      throw error;
    }
  }

  /**
   * Clean up expired codes (can be run as a cron job)
   */
  async cleanupExpiredCodes() {
    const query = `
      DELETE FROM verification_codes
      WHERE expires_at < NOW()
        AND is_used = FALSE
    `;
    
    try {
      const result = await pool.query(query);
      console.log(`🧹 Cleaned up ${result.rowCount} expired codes`);
      return result.rowCount;
    } catch (error) {
      console.error('❌ Error cleaning up expired codes:', error);
      throw error;
    }
  }
}

module.exports = new VerificationCodeRepository();
