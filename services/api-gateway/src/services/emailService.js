const nodemailer = require('nodemailer');

/**
 * Email Service
 * Handles sending emails with professional templates
 */
class EmailService {
  constructor() {
    this.transporter = nodemailer.createTransport({
      host: process.env.EMAIL_HOST,
      port: parseInt(process.env.EMAIL_PORT || '587'),
      secure: process.env.EMAIL_SECURE === 'true',
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_PASSWORD,
      },
    });

    this.fromEmail = {
      name: process.env.EMAIL_FROM_NAME || 'BAXperience',
      address: process.env.EMAIL_FROM_ADDRESS || process.env.EMAIL_USER,
    };
  }

  /**
   * Initialize and verify email service
   */
  async initialize() {
    try {
      await this.transporter.verify();
      console.log('✅ Email service is ready');
      return true;
    } catch (error) {
      console.error('❌ Email service error:', error);
      return false;
    }
  }

  /**
   * Send registration verification code
   */
  async sendRegistrationCode(email, code, userName) {
    const subject = 'Verify Your BAXperience Account';
    const html = this.getRegistrationTemplate(code, userName);
    const text = `Hello ${userName || ''}!\n\nThank you for signing up for BAXperience. Your verification code is: ${code}\n\nThis code expires in ${process.env.VERIFICATION_CODE_EXPIRY_MINUTES || 15} minutes.\n\nIf you didn't create a BAXperience account, you can ignore this email.\n\nBest regards,\nThe BAXperience Team`;
    
    return this.sendEmail(email, subject, html, text);
  }

  /**
   * Send password reset verification code
   */
  async sendPasswordResetCode(email, code, userName) {
    const subject = 'Reset Your BAXperience Password';
    const html = this.getPasswordResetTemplate(code, userName);
    const text = `Hello ${userName || ''}!\n\nWe received a request to reset your BAXperience password. Your verification code is: ${code}\n\nThis code expires in ${process.env.VERIFICATION_CODE_EXPIRY_MINUTES || 15} minutes.\n\nIf you didn't request this, you can ignore this email. Your password will remain unchanged.\n\nBest regards,\nThe BAXperience Team`;
    
    return this.sendEmail(email, subject, html, text);
  }

  /**
   * Generic send email method
   */
  async sendEmail(to, subject, html, text) {
    try {
      const mailOptions = {
        from: `"${this.fromEmail.name}" <${this.fromEmail.address}>`,
        to,
        subject,
        html,
        text,
      };

      const info = await this.transporter.sendMail(mailOptions);
      console.log('✅ Email sent:', info.messageId);
      return { success: true, messageId: info.messageId };
    } catch (error) {
      console.error('❌ Error sending email:', error);
      throw new Error('Failed to send email');
    }
  }

  /**
   * Registration email template
   */
  getRegistrationTemplate(code, userName) {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Account</title>
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;background-color:#f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(27,59,111,0.15);">
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#1B3B6F 0%,#2C5EAD 100%);padding:50px 30px;text-align:center;color:white;">
                            <h1 style="margin:0 0 12px 0;font-size:32px;font-weight:700;letter-spacing:0.5px;color:white;">Welcome to BAXperience!</h1>
                            <p style="margin:0;font-size:16px;opacity:0.95;color:white;">Your journey to incredible experiences starts here</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding:50px 40px;">
                            <p style="margin:0 0 20px 0;font-size:20px;color:#1B3B6F;font-weight:600;">Hello ${userName || ''}! 👋</p>
                            
                            <p style="margin:0 0 30px 0;font-size:16px;color:#4A4A4A;line-height:1.8;">
                                Thank you for signing up for <strong>BAXperience</strong>. We're excited to help you discover amazing experiences and create unforgettable memories in Buenos Aires.
                            </p>
                            
                            <p style="margin:0 0 30px 0;font-size:16px;color:#4A4A4A;line-height:1.8;">
                                To complete your registration and verify your email address, please enter the following verification code in the app:
                            </p>
                            
                            <!-- Code Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin:40px 0;">
                                <tr>
                                    <td style="background:linear-gradient(135deg,#f5f5f5 0%,#ffffff 100%);border:3px solid #1B3B6F;border-radius:16px;padding:40px;text-align:center;">
                                        <p style="margin:0 0 15px 0;font-size:14px;color:#1B3B6F;text-transform:uppercase;letter-spacing:2px;font-weight:600;">Your Verification Code</p>
                                        <p style="margin:0 0 20px 0;font-size:48px;font-weight:800;color:#1B3B6F;letter-spacing:12px;font-family:'Courier New',monospace;text-shadow:2px 2px 4px rgba(27,59,111,0.1);">${code}</p>
                                        <p style="margin:0;font-size:14px;color:#9E9E9E;font-style:italic;">⏱ This code expires in ${process.env.VERIFICATION_CODE_EXPIRY_MINUTES || 15} minutes</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Info Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin:30px 0;">
                                <tr>
                                    <td style="background:#E3F2FD;border-left:4px solid #2C5EAD;padding:20px;border-radius:8px;">
                                        <p style="margin:0;font-size:14px;color:#1B3B6F;line-height:1.6;">
                                            <strong>🔒 Security Notice:</strong> If you didn't create a BAXperience account, you can ignore this email or contact our support team immediately.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin:30px 0 0 0;font-size:16px;color:#4A4A4A;line-height:1.8;">
                                Once verified, you'll be able to explore personalized itineraries, discover hidden gems, and experience Buenos Aires like never before!
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background:#1B3B6F;padding:40px 30px;text-align:center;color:white;">
                            <p style="margin:0 0 8px 0;font-size:24px;font-weight:700;letter-spacing:1px;">BAXperience</p>
                            <p style="margin:0 0 25px 0;font-size:14px;opacity:0.9;font-style:italic;">Discover. Experience. Remember.</p>
                            <p style="margin:20px 0 0 0;padding-top:20px;border-top:1px solid rgba(255,255,255,0.2);font-size:12px;opacity:0.7;">
                                This is an automated message, please do not reply to this email.<br>
                                If you need help, contact us at support@baxperience.com
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    `;
  }

  /**
   * Password reset email template
   */
  getPasswordResetTemplate(code, userName) {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;background-color:#f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(27,59,111,0.15);">
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#1B3B6F 0%,#2C5EAD 100%);padding:50px 30px;text-align:center;color:white;">
                            <h1 style="margin:0 0 12px 0;font-size:32px;font-weight:700;letter-spacing:0.5px;color:white;">🔐 Password Reset Request</h1>
                            <p style="margin:0;font-size:16px;opacity:0.95;color:white;">We're here to help you get back to exploring</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding:50px 40px;">
                            <p style="margin:0 0 20px 0;font-size:20px;color:#1B3B6F;font-weight:600;">Hello ${userName || ''}! 👋</p>
                            
                            <p style="margin:0 0 30px 0;font-size:16px;color:#4A4A4A;line-height:1.8;">
                                We received a request to reset the password for your <strong>BAXperience</strong> account. Don't worry, we're here to help!
                            </p>
                            
                            <p style="margin:0 0 30px 0;font-size:16px;color:#4A4A4A;line-height:1.8;">
                                To reset your password, please enter the following verification code in the app:
                            </p>
                            
                            <!-- Code Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin:40px 0;">
                                <tr>
                                    <td style="background:linear-gradient(135deg,#f5f5f5 0%,#ffffff 100%);border:3px solid #1B3B6F;border-radius:16px;padding:40px;text-align:center;">
                                        <p style="margin:0 0 15px 0;font-size:14px;color:#1B3B6F;text-transform:uppercase;letter-spacing:2px;font-weight:600;">Your Verification Code</p>
                                        <p style="margin:0 0 20px 0;font-size:48px;font-weight:800;color:#1B3B6F;letter-spacing:12px;font-family:'Courier New',monospace;text-shadow:2px 2px 4px rgba(27,59,111,0.1);">${code}</p>
                                        <p style="margin:0;font-size:14px;color:#9E9E9E;font-style:italic;">⏱ This code expires in ${process.env.VERIFICATION_CODE_EXPIRY_MINUTES || 15} minutes</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Alert Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin:30px 0;">
                                <tr>
                                    <td style="background:#FFEBEE;border-left:4px solid #D32F2F;padding:20px;border-radius:8px;">
                                        <p style="margin:0;font-size:14px;color:#C62828;line-height:1.6;">
                                            <strong>⚠️ Important:</strong> If you didn't request a password reset, you can ignore this email and make sure your account is secure. Your password will not be changed.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Info Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin:30px 0;">
                                <tr>
                                    <td style="background:#E3F2FD;border-left:4px solid #2C5EAD;padding:20px;border-radius:8px;">
                                        <p style="margin:0;font-size:14px;color:#1B3B6F;line-height:1.6;">
                                            <strong>💡 Security Tip:</strong> After resetting your password, make sure to use a unique and strong password that you don't use on other sites. Consider using a password manager for better security.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin:30px 0 0 0;font-size:16px;color:#4A4A4A;line-height:1.8;">
                                Once you've reset your password, you'll be able to continue exploring amazing experiences in Buenos Aires!
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background:#1B3B6F;padding:40px 30px;text-align:center;color:white;">
                            <p style="margin:0 0 8px 0;font-size:24px;font-weight:700;letter-spacing:1px;">BAXperience</p>
                            <p style="margin:0 0 25px 0;font-size:14px;opacity:0.9;font-style:italic;">Discover. Experience. Remember.</p>
                            <p style="margin:20px 0 0 0;padding-top:20px;border-top:1px solid rgba(255,255,255,0.2);font-size:12px;opacity:0.7;">
                                This is an automated message, please do not reply to this email.<br>
                                If you need help, contact us at support@baxperience.com
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    `;
  }
}

module.exports = new EmailService();
