const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../config/database');

class AuthController {
  async register(req, res) {
    try {
      const { email, password, nombre, apellido, username } = req.body;

      // Validate input
      if (!email || !password || !nombre || !apellido || !username) {
        return res.status(400).json({
          error: 'All fields are required: email, password, nombre, apellido, username'
        });
      }

      // Check if user already exists
      const existingUser = await db.query(
        'SELECT id FROM usuarios WHERE email = $1',
        [email]
      );

      if (existingUser.rows.length > 0) {
        return res.status(409).json({
          error: 'User already exists with this email'
        });
      }

      const usernameExists = await db.query(
        'SELECT id FROM usuarios WHERE username = $1',
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
        `INSERT INTO usuarios (email, password_hash, nombre, apellido, username, fecha_registro, fecha_actualizacion) 
         VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
         RETURNING id, email, nombre, apellido, username, fecha_registro`,
        [email, hashedPassword, nombre, apellido, username]
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
          nombre: user.nombre,
          apellido: user.apellido,
          username: user.username,
          fechaRegistro: user.fecha_registro
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
        'SELECT id, email, password_hash, nombre, apellido, fecha_registro FROM usuarios WHERE email = $1',
        [email]
      );

      if (result.rows.length === 0) {
        return res.status(401).json({
          error: 'Invalid credentials'
        });
      }

      const user = result.rows[0];

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

      const result = await db.query(
        'SELECT id, email, nombre, apellido, fecha_registro, fecha_actualizacion FROM usuarios WHERE id = $1',
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
        const result = await db.query(
        `UPDATE usuarios SET
            fecha_nacimiento = $1, 
            pais_origen = $2, 
            ciudad_origen = $3,
            idioma_preferido = COALESCE($4, idioma_preferido),
            telefono = $5,
            tipo_viajero = $6,
            genero = $7,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = $8
        RETURNING id, username, email, nombre, apellido, ciudad_origen, idioma_preferido, telefono, tipo_viajero, fecha_nacimiento, pais_origen, genero`,
        [fechaNacimiento, paisOrigen, ciudadOrigen, idiomaPreferido, telefono, tipoViajero, genero, userId]
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
