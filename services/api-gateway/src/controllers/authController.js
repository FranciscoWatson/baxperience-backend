const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const authRepository = require('../repositories/authRepository');

class AuthController {
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
}

module.exports = new AuthController();
