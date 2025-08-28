const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../config/database');

class AuthController {
  async register(req, res) {
    try {
      const { email, password, firstName, lastName, username } = req.body;

      // Validate input
      if (!email || !password || !firstName || !lastName || !username) {
        return res.status(400).json({
          error: 'All fields are required: email, password, firstName, lastName, username'
        });
      }

      // Check if user already exists
      const existingUser = await db.query(
        'SELECT id FROM users WHERE email = $1',
        [email]
      );

      if (existingUser.rows.length > 0) {
        return res.status(409).json({
          error: 'User already exists with this email'
        });
      }

      const usernameExists = await db.query(
        'SELECT id FROM users WHERE username = $1',
        [username]
      );

      if (usernameExists.rows.length > 0) {
        return res.status(409).json({
          error: 'Username already exists'
        });
      }

      // Hash password
      const saltRounds = 12;
      const hashedPassword = await bcrypt.hash(password, saltRounds);

      // Create user
      const result = await db.query(
        `INSERT INTO users (email, password, first_name, last_name, username, created_at, updated_at) 
         VALUES ($1, $2, $3, $4, $5, NOW(), NOW()) 
         RETURNING id, email, first_name, last_name, username, created_at`,
        [email, hashedPassword, firstName, lastName, username]
      );

      const user = result.rows[0];

      // Generate JWT token
      const token = jwt.sign(
        { 
          userId: user.id, 
          email: user.email 
        },
        process.env.JWT_SECRET,
        { expiresIn: process.env.JWT_EXPIRES_IN }
      );

      res.status(201).json({
        message: 'User registered successfully',
        user: {
          id: user.id,
          email: user.email,
          firstName: user.first_name,
          lastName: user.last_name,
          username: user.username,
          createdAt: user.created_at
        },
        token
      });

    } catch (error) {
      console.error('Registration error:', error);
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
      const result = await db.query(
        'SELECT id, email, password, first_name, last_name, created_at FROM users WHERE email = $1',
        [email]
      );

      if (result.rows.length === 0) {
        return res.status(401).json({
          error: 'Invalid credentials'
        });
      }

      const user = result.rows[0];

      // Verify password
      const isValidPassword = await bcrypt.compare(password, user.password);

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
          firstName: user.first_name,
          lastName: user.last_name,
          createdAt: user.created_at
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

      const result = await db.query(
        'SELECT id, email, first_name, last_name, created_at, updated_at FROM users WHERE id = $1',
        [userId]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'User not found'
        });
      }

      const user = result.rows[0];

      res.status(200).json({
        user: {
          id: user.id,
          email: user.email,
          firstName: user.first_name,
          lastName: user.last_name,
          createdAt: user.created_at,
          updatedAt: user.updated_at
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
        const { fecha_nacimiento, pais_origen, ciudad_origen, idioma_preferido, telefono, tipo_viajero } = req.body;

        // Validate required fields for basic functionality
        if ( !ciudad_origen || !telefono || !tipo_viajero || !fecha_nacimiento || !pais_origen || !idioma_preferido ) {
        return res.status(400).json({
            error: 'Required fields: ciudad_origen, telefono, tipo_viajero, fecha_nacimiento, pais_origen, idioma_preferido'
        });
        }

        // Update user profile
        const result = await db.query(
        `UPDATE usuarios SET
            fecha_nacimiento = $1, 
            pais_origen = $2, 
            ciudad_origen = $3,
            idioma_preferido = COALESCE($4, idioma_preferido),
            telefono = $5,
            tipo_viajero = $6,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = $7
        RETURNING id, username, email, nombre, apellido, ciudad_origen, idioma_preferido`,
        [fecha_nacimiento, pais_origen, ciudad_origen, idioma_preferido, telefono, tipo_viajero, userId]
        );

        if (result.rows.length === 0) {
        return res.status(404).json({
            error: 'User not found'
        });
        }

        const user = result.rows[0];

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
            fechaNacimiento: user.fecha_nacimiento
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
