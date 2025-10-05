const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const authRepository = require('../repositories/authRepository');
const verificationCodeRepository = require('../repositories/verificationCodeRepository');
const emailService = require('../services/emailService');
const cloudinaryService = require('../services/cloudinaryService');

class AuthController {
  /**
   * Step 1: Request registration code (send email)
   */
  async requestRegistrationCode(req, res) {
    try {
      const { email, nombre } = req.body;

      if (!email) {
        return res.status(400).json({
          error: 'Email is required'
        });
      }

      // Check if user already exists
      const existingUser = await authRepository.findUserForLogin(email);
      if (existingUser) {
        return res.status(409).json({
          error: 'User already exists with this email'
        });
      }

      // Check rate limiting - no more than 1 code per minute
      const recentCode = await verificationCodeRepository.getRecentCode(email, 'registration');
      if (recentCode) {
        const timeSinceLastCode = Date.now() - new Date(recentCode.created_at).getTime();
        const oneMinute = 60 * 1000;
        if (timeSinceLastCode < oneMinute) {
          return res.status(429).json({
            error: 'Please wait before requesting a new code',
            retryAfter: Math.ceil((oneMinute - timeSinceLastCode) / 1000)
          });
        }
      }

      // Invalidate previous codes
      await verificationCodeRepository.invalidatePreviousCodes(email, 'registration');

      // Create new verification code
      const ipAddress = req.ip || req.connection.remoteAddress;
      const verification = await verificationCodeRepository.createCode(email, 'registration', ipAddress);

      // Send email
      await emailService.sendRegistrationCode(email, verification.code, nombre || 'there');

      res.status(200).json({
        message: 'Verification code sent to your email',
        expiresIn: process.env.VERIFICATION_CODE_EXPIRY_MINUTES || 15
      });

    } catch (error) {
      console.error('Request registration code error:', error);
      res.status(500).json({
        error: 'Failed to send verification code'
      });
    }
  }

  /**
   * Step 2: Verify registration code
   */
  async verifyRegistrationCode(req, res) {
    try {
      const { email, code } = req.body;

      if (!email || !code) {
        return res.status(400).json({
          error: 'Email and code are required'
        });
      }

      const verification = await verificationCodeRepository.verifyCode(email, code, 'registration');

      if (!verification.valid) {
        return res.status(400).json({
          error: verification.error
        });
      }

      res.status(200).json({
        message: 'Code verified successfully',
        verified: true
      });

    } catch (error) {
      console.error('Verify registration code error:', error);
      res.status(500).json({
        error: 'Failed to verify code'
      });
    }
  }

  /**
   * Step 3: Complete registration (after code verification)
   */
  async register(req, res) {
    try {
      const { 
        email, 
        password, 
        nombre, 
        apellido, 
        username, 
        fechaNacimiento, 
        paisOrigen, 
        ciudadOrigen, 
        idiomaPreferido, 
        telefono, 
        tipoViajero, 
        genero
      } = req.body;
      
      // Extraer preferencias y permitir que sea modificable
      let preferencias = req.body.preferencias;

      // Validate basic input
      if (!email || !password || !nombre || !apellido || !username) {
        return res.status(400).json({
          error: 'All fields are required: email, password, nombre, apellido, username'
        });
      }

      // Validate profile fields
      if (!ciudadOrigen || !telefono || !tipoViajero || !fechaNacimiento || !paisOrigen || !idiomaPreferido || !genero) {
        return res.status(400).json({
          error: 'Required profile fields: ciudadOrigen, telefono, tipoViajero, fechaNacimiento, paisOrigen, idiomaPreferido, genero'
        });
      }

      // Validate preferences
      if (!preferencias || !Array.isArray(preferencias) || preferencias.length === 0) {
        return res.status(400).json({
          error: 'At least one preference category is required'
        });
      }
      
      // Validate each preference is a valid number
      const validPreferencias = preferencias
        .filter(p => p !== null && p !== undefined && p !== '')
        .map(p => {
          const parsed = parseInt(p, 10);
          return isNaN(parsed) ? null : parsed;
        })
        .filter(p => p !== null);
      
      if (validPreferencias.length === 0) {
        return res.status(400).json({
          error: 'No valid preference categories found. Please provide numeric category IDs.'
        });
      }
      
      console.log('Controller: Received preferences:', preferencias);
      console.log('Controller: Valid preferences after parsing:', validPreferencias);
      
      // Replace the original array with the validated one
      preferencias = validPreferencias;

      // Hash password
      const saltRounds = 12;
      const hashedPassword = await bcrypt.hash(password, saltRounds);

      // Create user with all profile data and preferences
      const userData = {
        email,
        hashedPassword,
        nombre,
        apellido,
        username,
        fechaNacimiento,
        paisOrigen,
        ciudadOrigen,
        idiomaPreferido,
        telefono,
        tipoViajero,
        genero
      };

      const result = await authRepository.registerUserWithPreferences(userData, preferencias);

      // Generate JWT token
      const token = jwt.sign(
        { 
          userId: result.user.id, 
          email: result.user.email 
        },
        process.env.JWT_SECRET,
        { expiresIn: process.env.JWT_EXPIRES_IN }
      );

      res.status(201).json({
        message: 'User registered successfully',
        user: {
          id: result.user.id,
          email: result.user.email,
          nombre: result.user.nombre,
          apellido: result.user.apellido,
          username: result.user.username,
          fechaNacimiento: result.user.fecha_nacimiento,
          paisOrigen: result.user.pais_origen,
          ciudadOrigen: result.user.ciudad_origen,
          idiomaPreferido: result.user.idioma_preferido,
          telefono: result.user.telefono,
          tipoViajero: result.user.tipo_viajero,
          genero: result.user.genero,
          fechaRegistro: result.user.fecha_registro,
          preferencias: result.preferencias
        },
        token
      });

    } catch (error) {
      console.error('Registration error:', error);
      
      if (error.message === 'USER_EMAIL_EXISTS') {
        return res.status(409).json({
          error: 'User already exists with this email'
        });
      }
      
      if (error.message === 'USER_USERNAME_EXISTS') {
        return res.status(409).json({
          error: 'Username already exists'
        });
      }
      
      res.status(500).json({
        error: 'Internal server error during registration'
      });
    }
  }

  async login(req, res) {
    try {
      const { email, password } = req.body;

      // Validate input
      if (!email || !password) {
        return res.status(400).json({
          error: 'Email and password are required'
        });
      }

      // Find user
      const user = await authRepository.findUserForLogin(email);

      if (!user) {
        return res.status(401).json({
          error: 'Invalid credentials'
        });
      }

      // Verify password
      const isValidPassword = await bcrypt.compare(password, user.password_hash);

      if (!isValidPassword) {
        return res.status(401).json({
          error: 'Invalid credentials'
        });
      }

      // Generate JWT token
      const token = jwt.sign(
        { 
          userId: user.id, 
          email: user.email 
        },
        process.env.JWT_SECRET,
        { expiresIn: process.env.JWT_EXPIRES_IN }
      );

      res.status(200).json({
        message: 'Login successful',
        user: {
          id: user.id,
          email: user.email,
          nombre: user.nombre,
          apellido: user.apellido,
          fechaRegistro: user.fecha_registro
        },
        token
      });

    } catch (error) {
      console.error('Login error:', error);
      res.status(500).json({
        error: 'Internal server error during login'
      });
    }
  }

  async getProfile(req, res) {
    try {
      const userId = req.user.userId;

      const user = await authRepository.findUserById(userId);

      if (!user) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      res.status(200).json({
        user: {
          id: user.id,
          email: user.email,
          nombre: user.nombre,
          apellido: user.apellido,
          fechaRegistro: user.fecha_registro,
          fechaActualizacion: user.fecha_actualizacion
        }
      });

    } catch (error) {
      console.error('Get profile error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching profile'
      });
    }
  }

  async setupProfile(req, res) {
    try {
        const userId = req.user.userId;
        const { fechaNacimiento, paisOrigen, ciudadOrigen, idiomaPreferido, telefono, tipoViajero, genero } = req.body;

        // Validate required fields for basic functionality
        if (!ciudadOrigen || !telefono || !tipoViajero || !fechaNacimiento || !paisOrigen || !idiomaPreferido || !genero) {
        return res.status(400).json({
            error: 'Required fields: ciudadOrigen, telefono, tipoViajero, fechaNacimiento, paisOrigen, idiomaPreferido, genero'
        });
        }

        // Update user profile
        const profileData = {
          fechaNacimiento,
          paisOrigen,
          ciudadOrigen,
          idiomaPreferido,
          telefono,
          tipoViajero,
          genero
        };

        const user = await authRepository.updateUserProfile(userId, profileData);

        if (!user) {
          return res.status(404).json({
            error: 'User not found'
          });
        }

        res.status(200).json({
        message: 'Profile setup completed successfully',
        user: {
            id: user.id,
            username: user.username,
            email: user.email,
            nombre: user.nombre,
            apellido: user.apellido,
            paisOrigen: user.pais_origen,
            ciudadOrigen: user.ciudad_origen,
            idiomaPreferido: user.idioma_preferido,
            telefono: user.telefono,
            tipoViajero: user.tipo_viajero,
            fechaNacimiento: user.fecha_nacimiento,
            genero: user.genero
            }
        });

    } catch (error) {
        console.error('Setup profile error:', error);
        res.status(500).json({
        error: 'Internal server error during profile setup'
        });
    }
  }

  /**
   * Forgot Password - Step 1: Request password reset code
   */
  async requestPasswordReset(req, res) {
    try {
      const { email } = req.body;

      if (!email) {
        return res.status(400).json({
          error: 'Email is required'
        });
      }

      // Check if user exists
      const user = await authRepository.findUserForLogin(email);
      
      // For security, don't reveal if user exists or not
      // Always return success message
      
      if (user) {
        // Check rate limiting
        const recentCode = await verificationCodeRepository.getRecentCode(email, 'password_reset');
        if (recentCode) {
          const timeSinceLastCode = Date.now() - new Date(recentCode.created_at).getTime();
          const oneMinute = 60 * 1000;
          if (timeSinceLastCode < oneMinute) {
            return res.status(429).json({
              error: 'Please wait before requesting a new code',
              retryAfter: Math.ceil((oneMinute - timeSinceLastCode) / 1000)
            });
          }
        }

        // Invalidate previous codes
        await verificationCodeRepository.invalidatePreviousCodes(email, 'password_reset');

        // Create new verification code
        const ipAddress = req.ip || req.connection.remoteAddress;
        const verification = await verificationCodeRepository.createCode(email, 'password_reset', ipAddress);

        // Send email
        await emailService.sendPasswordResetCode(
          email, 
          verification.code, 
          user.nombre || 'there'
        );
      }

      // Always return success to prevent email enumeration
      res.status(200).json({
        message: 'If your email is registered, you will receive a password reset code',
        expiresIn: process.env.VERIFICATION_CODE_EXPIRY_MINUTES || 15
      });

    } catch (error) {
      console.error('Request password reset error:', error);
      res.status(500).json({
        error: 'Failed to process password reset request'
      });
    }
  }

  /**
   * Forgot Password - Step 2: Verify reset code
   */
  async verifyPasswordResetCode(req, res) {
    try {
      const { email, code } = req.body;

      if (!email || !code) {
        return res.status(400).json({
          error: 'Email and code are required'
        });
      }

      // Verify user exists
      const user = await authRepository.findUserForLogin(email);
      if (!user) {
        return res.status(400).json({
          error: 'Invalid code'
        });
      }

      const verification = await verificationCodeRepository.verifyCode(email, code, 'password_reset');

      if (!verification.valid) {
        return res.status(400).json({
          error: verification.error
        });
      }

      // Generate a temporary token for password reset
      const resetToken = jwt.sign(
        { 
          email,
          purpose: 'password_reset',
          codeId: verification.data.id
        },
        process.env.JWT_SECRET,
        { expiresIn: '15m' } // Short-lived token
      );

      res.status(200).json({
        message: 'Code verified successfully',
        verified: true,
        resetToken // Use this token to reset password
      });

    } catch (error) {
      console.error('Verify password reset code error:', error);
      res.status(500).json({
        error: 'Failed to verify code'
      });
    }
  }

  /**
   * Forgot Password - Step 3: Reset password
   */
  async resetPassword(req, res) {
    try {
      const { resetToken, newPassword } = req.body;

      if (!resetToken || !newPassword) {
        return res.status(400).json({
          error: 'Reset token and new password are required'
        });
      }

      // Validate password strength
      if (newPassword.length < 6) {
        return res.status(400).json({
          error: 'Password must be at least 6 characters long'
        });
      }

      // Verify reset token
      let decoded;
      try {
        decoded = jwt.verify(resetToken, process.env.JWT_SECRET);
      } catch (error) {
        return res.status(400).json({
          error: 'Invalid or expired reset token'
        });
      }

      if (decoded.purpose !== 'password_reset') {
        return res.status(400).json({
          error: 'Invalid reset token'
        });
      }

      // Find user
      const user = await authRepository.findUserForLogin(decoded.email);
      if (!user) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      // Hash new password
      const saltRounds = 12;
      const hashedPassword = await bcrypt.hash(newPassword, saltRounds);

      // Update password
      await authRepository.updatePassword(user.id, hashedPassword);

      res.status(200).json({
        message: 'Password reset successfully'
      });

    } catch (error) {
      console.error('Reset password error:', error);
      res.status(500).json({
        error: 'Failed to reset password'
      });
    }
  }

  /**
   * Get user profile with complete information
   */
  async getProfileInfo(req, res) {
    try {
      const userId = req.user.userId;

      const profile = await authRepository.getUserProfile(userId);

      if (!profile) {
        return res.status(404).json({
          error: 'User profile not found'
        });
      }

      // Remove sensitive data
      const profileData = {
        id: profile.id,
        username: profile.username,
        email: profile.email,
        nombre: profile.nombre,
        apellido: profile.apellido,
        fecha_nacimiento: profile.fecha_nacimiento,
        genero: profile.genero,
        telefono: profile.telefono,
        pais_origen: profile.pais_origen,
        ciudad_origen: profile.ciudad_origen,
        idioma_preferido: profile.idioma_preferido,
        tipo_viajero: profile.tipo_viajero,
        duracion_viaje_promedio: profile.duracion_viaje_promedio,
        profile_image_url: profile.profile_image_url,
        fecha_registro: profile.fecha_registro,
        fecha_actualizacion: profile.fecha_actualizacion
      };

      res.status(200).json(profileData);

    } catch (error) {
      console.error('Get profile info error:', error);
      res.status(500).json({
        error: 'Failed to get profile information'
      });
    }
  }

  /**
   * Update user profile information
   */
  async updateProfileInfo(req, res) {
    try {
      const userId = req.user.userId;
      const {
        nombre,
        apellido,
        fecha_nacimiento,
        genero,
        telefono,
        pais_origen,
        ciudad_origen,
        idioma_preferido,
        tipo_viajero,
        duracion_viaje_promedio
      } = req.body;

      // Validate at least one field is being updated
      if (!nombre && !apellido && !fecha_nacimiento && !genero && !telefono && 
          !pais_origen && !ciudad_origen && !idioma_preferido && !tipo_viajero && 
          !duracion_viaje_promedio) {
        return res.status(400).json({
          error: 'At least one field must be provided for update'
        });
      }

      // Validate fecha_nacimiento if provided
      if (fecha_nacimiento) {
        const birthDate = new Date(fecha_nacimiento);
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        
        if (age < 13) {
          return res.status(400).json({
            error: 'User must be at least 13 years old'
          });
        }
      }

      const updatedProfile = await authRepository.updateUserInfo(userId, {
        nombre,
        apellido,
        fecha_nacimiento,
        genero,
        telefono,
        pais_origen,
        ciudad_origen,
        idioma_preferido,
        tipo_viajero,
        duracion_viaje_promedio
      });

      if (!updatedProfile) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      res.status(200).json({
        message: 'Profile updated successfully',
        profile: {
          id: updatedProfile.id,
          username: updatedProfile.username,
          email: updatedProfile.email,
          nombre: updatedProfile.nombre,
          apellido: updatedProfile.apellido,
          fecha_nacimiento: updatedProfile.fecha_nacimiento,
          genero: updatedProfile.genero,
          telefono: updatedProfile.telefono,
          pais_origen: updatedProfile.pais_origen,
          ciudad_origen: updatedProfile.ciudad_origen,
          idioma_preferido: updatedProfile.idioma_preferido,
          tipo_viajero: updatedProfile.tipo_viajero,
          duracion_viaje_promedio: updatedProfile.duracion_viaje_promedio,
          profile_image_url: updatedProfile.profile_image_url,
          fecha_actualizacion: updatedProfile.fecha_actualizacion
        }
      });

    } catch (error) {
      console.error('Update profile info error:', error);
      res.status(500).json({
        error: 'Failed to update profile information'
      });
    }
  }

  /**
   * Upload/Update profile image
   */
  async uploadProfileImage(req, res) {
    try {
      const userId = req.user.userId;

      if (!req.file) {
        return res.status(400).json({
          error: 'No image file provided'
        });
      }

      // Validate image
      try {
        cloudinaryService.validateImage(req.file);
      } catch (validationError) {
        return res.status(400).json({
          error: validationError.message
        });
      }

      // Get current profile to check for existing image
      const currentProfile = await authRepository.getUserProfile(userId);
      
      // Delete old image from Cloudinary if exists
      if (currentProfile && currentProfile.profile_image_url) {
        await cloudinaryService.deleteProfileImage(currentProfile.profile_image_url);
      }

      // Upload new image to Cloudinary
      const imageUrl = await cloudinaryService.uploadProfileImage(req.file.buffer, userId);

      // Update database with new image URL
      const updatedProfile = await authRepository.updateProfileImage(userId, imageUrl);

      if (!updatedProfile) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      res.status(200).json({
        message: 'Profile image updated successfully',
        profile_image_url: updatedProfile.profile_image_url,
        profile: {
          id: updatedProfile.id,
          username: updatedProfile.username,
          email: updatedProfile.email,
          nombre: updatedProfile.nombre,
          apellido: updatedProfile.apellido,
          profile_image_url: updatedProfile.profile_image_url
        }
      });

    } catch (error) {
      console.error('Upload profile image error:', error);
      res.status(500).json({
        error: 'Failed to upload profile image'
      });
    }
  }

  /**
   * Delete profile image
   */
  async deleteProfileImage(req, res) {
    try {
      const userId = req.user.userId;

      // Get current profile
      const currentProfile = await authRepository.getUserProfile(userId);

      if (!currentProfile) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      if (!currentProfile.profile_image_url) {
        return res.status(400).json({
          error: 'No profile image to delete'
        });
      }

      // Delete image from Cloudinary
      await cloudinaryService.deleteProfileImage(currentProfile.profile_image_url);

      // Update database to remove image URL
      const updatedProfile = await authRepository.updateProfileImage(userId, null);

      res.status(200).json({
        message: 'Profile image deleted successfully',
        profile: {
          id: updatedProfile.id,
          username: updatedProfile.username,
          email: updatedProfile.email,
          nombre: updatedProfile.nombre,
          apellido: updatedProfile.apellido,
          profile_image_url: null
        }
      });

    } catch (error) {
      console.error('Delete profile image error:', error);
      res.status(500).json({
        error: 'Failed to delete profile image'
      });
    }
  }
}

module.exports = new AuthController();
