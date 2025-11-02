const authController = require('../../src/controllers/authController');
const authRepository = require('../../src/repositories/authRepository');
const verificationCodeRepository = require('../../src/repositories/verificationCodeRepository');
const emailService = require('../../src/services/emailService');
const cloudinaryService = require('../../src/services/cloudinaryService');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

// Mock all dependencies
jest.mock('../../src/repositories/authRepository');
jest.mock('../../src/repositories/verificationCodeRepository');
jest.mock('../../src/services/emailService');
jest.mock('../../src/services/cloudinaryService');
jest.mock('../../src/utils/logger');
jest.mock('bcrypt');
jest.mock('jsonwebtoken');

describe('AuthController', () => {
  let req, res;

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();
    
    // Mock request and response objects
    req = {
      body: {},
      user: {},
      ip: '127.0.0.1',
      connection: { remoteAddress: '127.0.0.1' },
      file: null
    };

    res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis()
    };
  });

  describe('requestRegistrationCode', () => {
    it('should send verification code successfully', async () => {
      req.body = { email: 'test@example.com', nombre: 'Test User' };
      
      authRepository.findUserForLogin.mockResolvedValue(null);
      verificationCodeRepository.getRecentCode.mockResolvedValue(null);
      verificationCodeRepository.invalidatePreviousCodes.mockResolvedValue();
      verificationCodeRepository.createCode.mockResolvedValue({
        code: '123456',
        email: 'test@example.com'
      });
      emailService.sendRegistrationCode.mockResolvedValue({ success: true });

      await authController.requestRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.any(String),
          expiresIn: expect.any(String)
        })
      );
      expect(emailService.sendRegistrationCode).toHaveBeenCalled();
    });

    it('should return error if email is missing', async () => {
      req.body = {};

      await authController.requestRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Email is required'
      });
    });

    it('should return error if user already exists', async () => {
      req.body = { email: 'existing@example.com' };
      
      authRepository.findUserForLogin.mockResolvedValue({ id: 1 });

      await authController.requestRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(409);
      expect(res.json).toHaveBeenCalledWith({
        error: 'User already exists with this email'
      });
    });

    it('should enforce rate limiting', async () => {
      req.body = { email: 'test@example.com' };
      
      authRepository.findUserForLogin.mockResolvedValue(null);
      verificationCodeRepository.getRecentCode.mockResolvedValue({
        created_at: new Date()
      });

      await authController.requestRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(429);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.stringContaining('wait'),
          retryAfter: expect.any(Number)
        })
      );
    });
  });

  describe('verifyRegistrationCode', () => {
    it('should verify code successfully', async () => {
      req.body = { email: 'test@example.com', code: '123456' };
      
      verificationCodeRepository.verifyCode.mockResolvedValue({
        valid: true
      });

      await authController.verifyRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        message: 'Code verified successfully',
        verified: true
      });
    });

    it('should return error if email or code is missing', async () => {
      req.body = { email: 'test@example.com' };

      await authController.verifyRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Email and code are required'
      });
    });

    it('should return error if code is invalid', async () => {
      req.body = { email: 'test@example.com', code: 'invalid' };
      
      verificationCodeRepository.verifyCode.mockResolvedValue({
        valid: false,
        error: 'Invalid or expired code'
      });

      await authController.verifyRegistrationCode(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid or expired code'
      });
    });
  });

  describe('register', () => {
    it('should register user successfully with all required fields', async () => {
      req.body = {
        email: 'new@example.com',
        password: 'password123',
        nombre: 'John',
        apellido: 'Doe',
        username: 'johndoe',
        fechaNacimiento: '1990-01-01',
        paisOrigen: 'Argentina',
        ciudadOrigen: 'Buenos Aires',
        idiomaPreferido: 'es',
        telefono: '+5491123456789',
        tipoViajero: 'aventurero',
        genero: 'masculino',
        preferencias: [1, 2, 3]
      };

      bcrypt.hash.mockResolvedValue('hashed_password');
      authRepository.registerUserWithPreferences.mockResolvedValue({
        user: {
          id: 1,
          email: 'new@example.com',
          nombre: 'John',
          apellido: 'Doe',
          username: 'johndoe'
        },
        preferencias: [
          { categoria_id: 1 },
          { categoria_id: 2 },
          { categoria_id: 3 }
        ]
      });
      jwt.sign.mockReturnValue('mock_token');

      await authController.register(req, res);

      expect(bcrypt.hash).toHaveBeenCalledWith('password123', 12);
      expect(res.status).toHaveBeenCalledWith(201);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'User registered successfully',
          user: expect.any(Object),
          token: 'mock_token'
        })
      );
    });

    it('should return error if required fields are missing', async () => {
      req.body = {
        email: 'test@example.com',
        password: 'password123'
      };

      await authController.register(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.stringContaining('required')
        })
      );
    });

    it('should return error if preferences are missing', async () => {
      req.body = {
        email: 'new@example.com',
        password: 'password123',
        nombre: 'John',
        apellido: 'Doe',
        username: 'johndoe',
        fechaNacimiento: '1990-01-01',
        paisOrigen: 'Argentina',
        ciudadOrigen: 'Buenos Aires',
        idiomaPreferido: 'es',
        telefono: '+5491123456789',
        tipoViajero: 'aventurero',
        genero: 'masculino',
        preferencias: []
      };

      await authController.register(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'At least one preference category is required'
      });
    });

    it('should handle duplicate email error', async () => {
      req.body = {
        email: 'existing@example.com',
        password: 'password123',
        nombre: 'John',
        apellido: 'Doe',
        username: 'johndoe',
        fechaNacimiento: '1990-01-01',
        paisOrigen: 'Argentina',
        ciudadOrigen: 'Buenos Aires',
        idiomaPreferido: 'es',
        telefono: '+5491123456789',
        tipoViajero: 'aventurero',
        genero: 'masculino',
        preferencias: [1, 2]
      };

      bcrypt.hash.mockResolvedValue('hashed_password');
      authRepository.registerUserWithPreferences.mockRejectedValue(
        new Error('USER_EMAIL_EXISTS')
      );

      await authController.register(req, res);

      expect(res.status).toHaveBeenCalledWith(409);
      expect(res.json).toHaveBeenCalledWith({
        error: 'User already exists with this email'
      });
    });

    it('should handle duplicate username error', async () => {
      req.body = {
        email: 'new@example.com',
        password: 'password123',
        nombre: 'John',
        apellido: 'Doe',
        username: 'existinguser',
        fechaNacimiento: '1990-01-01',
        paisOrigen: 'Argentina',
        ciudadOrigen: 'Buenos Aires',
        idiomaPreferido: 'es',
        telefono: '+5491123456789',
        tipoViajero: 'aventurero',
        genero: 'masculino',
        preferencias: [1, 2]
      };

      bcrypt.hash.mockResolvedValue('hashed_password');
      authRepository.registerUserWithPreferences.mockRejectedValue(
        new Error('USER_USERNAME_EXISTS')
      );

      await authController.register(req, res);

      expect(res.status).toHaveBeenCalledWith(409);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Username already exists'
      });
    });
  });

  describe('login', () => {
    it('should login successfully with valid credentials', async () => {
      req.body = {
        email: 'test@example.com',
        password: 'password123'
      };

      authRepository.findUserForLogin.mockResolvedValue({
        id: 1,
        email: 'test@example.com',
        password_hash: 'hashed_password',
        nombre: 'John',
        apellido: 'Doe'
      });
      bcrypt.compare.mockResolvedValue(true);
      jwt.sign.mockReturnValue('mock_token');

      await authController.login(req, res);

      expect(bcrypt.compare).toHaveBeenCalledWith('password123', 'hashed_password');
      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Login successful',
          user: expect.any(Object),
          token: 'mock_token'
        })
      );
    });

    it('should return error if email or password is missing', async () => {
      req.body = { email: 'test@example.com' };

      await authController.login(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Email and password are required'
      });
    });

    it('should return error if user not found', async () => {
      req.body = {
        email: 'nonexistent@example.com',
        password: 'password123'
      };

      authRepository.findUserForLogin.mockResolvedValue(null);

      await authController.login(req, res);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid credentials'
      });
    });

    it('should return error if password is invalid', async () => {
      req.body = {
        email: 'test@example.com',
        password: 'wrongpassword'
      };

      authRepository.findUserForLogin.mockResolvedValue({
        id: 1,
        password_hash: 'hashed_password'
      });
      bcrypt.compare.mockResolvedValue(false);

      await authController.login(req, res);

      expect(res.status).toHaveBeenCalledWith(401);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid credentials'
      });
    });
  });

  describe('getProfile', () => {
    it('should get user profile successfully', async () => {
      req.user = { userId: 1 };

      authRepository.findUserById.mockResolvedValue({
        id: 1,
        email: 'test@example.com',
        nombre: 'John',
        apellido: 'Doe'
      });

      await authController.getProfile(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        user: expect.objectContaining({
          id: 1,
          email: 'test@example.com'
        })
      });
    });

    it('should return error if user not found', async () => {
      req.user = { userId: 999 };

      authRepository.findUserById.mockResolvedValue(null);

      await authController.getProfile(req, res);

      expect(res.status).toHaveBeenCalledWith(404);
      expect(res.json).toHaveBeenCalledWith({
        error: 'User not found'
      });
    });
  });

  describe('requestPasswordReset', () => {
    it('should send password reset code for existing user', async () => {
      req.body = { email: 'test@example.com' };

      authRepository.findUserForLogin.mockResolvedValue({
        id: 1,
        email: 'test@example.com',
        nombre: 'John'
      });
      verificationCodeRepository.getRecentCode.mockResolvedValue(null);
      verificationCodeRepository.invalidatePreviousCodes.mockResolvedValue();
      verificationCodeRepository.createCode.mockResolvedValue({
        code: '123456'
      });
      emailService.sendPasswordResetCode.mockResolvedValue({ success: true });

      await authController.requestPasswordReset(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('email')
        })
      );
      expect(emailService.sendPasswordResetCode).toHaveBeenCalled();
    });

    it('should return generic message for non-existent user (security)', async () => {
      req.body = { email: 'nonexistent@example.com' };

      authRepository.findUserForLogin.mockResolvedValue(null);

      await authController.requestPasswordReset(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('email')
        })
      );
      expect(emailService.sendPasswordResetCode).not.toHaveBeenCalled();
    });

    it('should enforce rate limiting', async () => {
      req.body = { email: 'test@example.com' };

      authRepository.findUserForLogin.mockResolvedValue({
        id: 1,
        email: 'test@example.com'
      });
      verificationCodeRepository.getRecentCode.mockResolvedValue({
        created_at: new Date()
      });

      await authController.requestPasswordReset(req, res);

      expect(res.status).toHaveBeenCalledWith(429);
    });
  });

  describe('verifyPasswordResetCode', () => {
    it('should verify reset code successfully', async () => {
      req.body = { email: 'test@example.com', code: '123456' };

      authRepository.findUserForLogin.mockResolvedValue({
        id: 1,
        email: 'test@example.com'
      });
      verificationCodeRepository.verifyCode.mockResolvedValue({
        valid: true,
        data: { id: 1 }
      });
      jwt.sign.mockReturnValue('reset_token');

      await authController.verifyPasswordResetCode(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          verified: true,
          resetToken: 'reset_token'
        })
      );
    });

    it('should return error if user not found', async () => {
      req.body = { email: 'test@example.com', code: '123456' };

      authRepository.findUserForLogin.mockResolvedValue(null);

      await authController.verifyPasswordResetCode(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid code'
      });
    });
  });

  describe('resetPassword', () => {
    it('should reset password successfully', async () => {
      req.body = {
        resetToken: 'valid_token',
        newPassword: 'newpassword123'
      };

      jwt.verify.mockReturnValue({
        email: 'test@example.com',
        purpose: 'password_reset'
      });
      authRepository.findUserForLogin.mockResolvedValue({
        id: 1,
        email: 'test@example.com'
      });
      bcrypt.hash.mockResolvedValue('new_hashed_password');
      authRepository.updatePassword.mockResolvedValue({ id: 1 });

      await authController.resetPassword(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        message: 'Password reset successfully'
      });
    });

    it('should return error if password is too short', async () => {
      req.body = {
        resetToken: 'valid_token',
        newPassword: 'short'
      };

      await authController.resetPassword(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.stringContaining('6 characters')
        })
      );
    });

    it('should return error if token is invalid', async () => {
      req.body = {
        resetToken: 'invalid_token',
        newPassword: 'newpassword123'
      };

      jwt.verify.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      await authController.resetPassword(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Invalid or expired reset token'
      });
    });
  });

  describe('getProfileInfo', () => {
    it('should get complete profile info successfully', async () => {
      req.user = { userId: 1 };

      authRepository.getUserProfile.mockResolvedValue({
        id: 1,
        email: 'test@example.com',
        nombre: 'John',
        apellido: 'Doe',
        username: 'johndoe',
        telefono: '+5491123456789'
      });

      await authController.getProfileInfo(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 1,
          email: 'test@example.com'
        })
      );
    });
  });

  describe('updateProfileInfo', () => {
    it('should update profile info successfully', async () => {
      req.user = { userId: 1 };
      req.body = {
        nombre: 'Jane',
        apellido: 'Smith'
      };

      authRepository.updateUserInfo.mockResolvedValue({
        id: 1,
        nombre: 'Jane',
        apellido: 'Smith',
        username: 'janesmith',
        email: 'jane@example.com'
      });

      await authController.updateProfileInfo(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Profile updated successfully',
          profile: expect.any(Object)
        })
      );
    });

    it('should return error if no fields provided', async () => {
      req.user = { userId: 1 };
      req.body = {};

      await authController.updateProfileInfo(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.stringContaining('At least one field')
        })
      );
    });

    it('should validate age if fecha_nacimiento is provided', async () => {
      req.user = { userId: 1 };
      req.body = {
        fecha_nacimiento: new Date().toISOString() // Too young
      };

      await authController.updateProfileInfo(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.stringContaining('13 years old')
        })
      );
    });
  });

  describe('uploadProfileImage', () => {
    it('should upload profile image successfully', async () => {
      req.user = { userId: 1 };
      req.file = {
        buffer: Buffer.from('fake-image'),
        mimetype: 'image/jpeg',
        size: 1024000
      };

      cloudinaryService.validateImage.mockReturnValue(true);
      authRepository.getUserProfile.mockResolvedValue({
        id: 1,
        profile_image_url: null
      });
      cloudinaryService.uploadProfileImage.mockResolvedValue('https://cloudinary.com/image.jpg');
      authRepository.updateProfileImage.mockResolvedValue({
        id: 1,
        username: 'johndoe',
        email: 'john@example.com',
        nombre: 'John',
        apellido: 'Doe',
        profile_image_url: 'https://cloudinary.com/image.jpg'
      });

      await authController.uploadProfileImage(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Profile image updated successfully',
          profile_image_url: 'https://cloudinary.com/image.jpg'
        })
      );
    });

    it('should return error if no file provided', async () => {
      req.user = { userId: 1 };
      req.file = null;

      await authController.uploadProfileImage(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'No image file provided'
      });
    });

    it('should return error if image validation fails', async () => {
      req.user = { userId: 1 };
      req.file = {
        buffer: Buffer.from('fake-image'),
        mimetype: 'image/jpeg',
        size: 10000000 // Too large
      };

      cloudinaryService.validateImage.mockImplementation(() => {
        throw new Error('Image too large');
      });

      await authController.uploadProfileImage(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Image too large'
      });
    });

    it('should delete old image before uploading new one', async () => {
      req.user = { userId: 1 };
      req.file = {
        buffer: Buffer.from('fake-image'),
        mimetype: 'image/jpeg',
        size: 1024000
      };

      cloudinaryService.validateImage.mockReturnValue(true);
      authRepository.getUserProfile.mockResolvedValue({
        id: 1,
        profile_image_url: 'https://cloudinary.com/old-image.jpg'
      });
      cloudinaryService.deleteProfileImage.mockResolvedValue(true);
      cloudinaryService.uploadProfileImage.mockResolvedValue('https://cloudinary.com/new-image.jpg');
      authRepository.updateProfileImage.mockResolvedValue({
        id: 1,
        username: 'johndoe',
        email: 'john@example.com',
        nombre: 'John',
        apellido: 'Doe',
        profile_image_url: 'https://cloudinary.com/new-image.jpg'
      });

      await authController.uploadProfileImage(req, res);

      expect(cloudinaryService.deleteProfileImage).toHaveBeenCalledWith(
        'https://cloudinary.com/old-image.jpg'
      );
      expect(res.status).toHaveBeenCalledWith(200);
    });
  });

  describe('deleteProfileImage', () => {
    it('should delete profile image successfully', async () => {
      req.user = { userId: 1 };

      authRepository.getUserProfile.mockResolvedValue({
        id: 1,
        profile_image_url: 'https://cloudinary.com/image.jpg'
      });
      cloudinaryService.deleteProfileImage.mockResolvedValue(true);
      authRepository.updateProfileImage.mockResolvedValue({
        id: 1,
        username: 'johndoe',
        email: 'john@example.com',
        nome: 'John',
        apellido: 'Doe',
        profile_image_url: null
      });

      await authController.deleteProfileImage(req, res);

      expect(cloudinaryService.deleteProfileImage).toHaveBeenCalled();
      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Profile image deleted successfully'
        })
      );
    });

    it('should return error if no profile image exists', async () => {
      req.user = { userId: 1 };

      authRepository.getUserProfile.mockResolvedValue({
        id: 1,
        profile_image_url: null
      });

      await authController.deleteProfileImage(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'No profile image to delete'
      });
    });
  });

  describe('getCategories', () => {
    it('should get all categories successfully', async () => {
      const mockCategories = [
        { id: 1, nombre: 'Gastronomía', descripcion: 'Restaurants' },
        { id: 2, nombre: 'Cultura', descripcion: 'Museums' }
      ];

      authRepository.getAllCategories.mockResolvedValue(mockCategories);

      await authController.getCategories(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        categories: mockCategories
      });
    });
  });

  describe('getUserPreferences', () => {
    it('should get user preferences successfully', async () => {
      req.user = { userId: 1 };

      const mockPreferences = [
        { preferencia_id: 1, categoria_id: 1, categoria_nombre: 'Gastronomía', le_gusta: true },
        { preferencia_id: 2, categoria_id: 2, categoria_nombre: 'Cultura', le_gusta: true }
      ];

      authRepository.getUserPreferences.mockResolvedValue(mockPreferences);

      await authController.getUserPreferences(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        preferences: mockPreferences
      });
    });
  });

  describe('updateUserPreferences', () => {
    it('should update user preferences successfully', async () => {
      req.user = { userId: 1 };
      req.body = {
        preferencias: [
          { categoria_id: 1, le_gusta: true },
          { categoria_id: 2, le_gusta: true }
        ]
      };

      const updatedPreferences = [
        { preferencia_id: 1, categoria_id: 1, le_gusta: true },
        { preferencia_id: 2, categoria_id: 2, le_gusta: true }
      ];

      authRepository.updateUserPreferences.mockResolvedValue(updatedPreferences);

      await authController.updateUserPreferences(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          message: 'Preferences updated successfully',
          preferences: updatedPreferences
        })
      );
    });

    it('should return error if preferencias is not an array', async () => {
      req.user = { userId: 1 };
      req.body = {
        preferencias: 'not-an-array'
      };

      await authController.updateUserPreferences(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'Preferences must be an array'
      });
    });

    it('should return error if no valid preferences provided', async () => {
      req.user = { userId: 1 };
      req.body = {
        preferencias: [
          { categoria_id: null },
          { categoria_id: undefined }
        ]
      };

      await authController.updateUserPreferences(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        error: 'At least one valid preference must be provided'
      });
    });
  });

  describe('setupProfile', () => {
    it('should setup profile successfully', async () => {
      req.user = { userId: 1 };
      req.body = {
        fechaNacimiento: '1990-01-01',
        paisOrigen: 'Argentina',
        ciudadOrigen: 'Buenos Aires',
        idiomaPreferido: 'es',
        telefono: '+5491123456789',
        tipoViajero: 'aventurero',
        genero: 'masculino'
      };

      authRepository.updateUserProfile.mockResolvedValue({
        id: 1,
        username: 'johndoe',
        email: 'john@example.com',
        nombre: 'John',
        apellido: 'Doe',
        pais_origen: 'Argentina',
        ciudad_origen: 'Buenos Aires',
        idioma_preferido: 'es',
        telefono: '+5491123456789',
        tipo_viajero: 'aventurero',
        fecha_nacimiento: '1990-01-01',
        genero: 'masculino'
      });

      await authController.setupProfile(req, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Profile setup completed successfully',
          user: expect.any(Object)
        })
      );
    });

    it('should return error if required fields are missing', async () => {
      req.user = { userId: 1 };
      req.body = {
        fechaNacimiento: '1990-01-01'
      };

      await authController.setupProfile(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.stringContaining('Required fields')
        })
      );
    });
  });
});
