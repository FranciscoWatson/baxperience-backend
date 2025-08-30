const db = require('../config/database');

class AuthRepository {
  async findUserByEmail(email) {
    const result = await db.query(
      'SELECT id FROM usuarios WHERE email = $1',
      [email]
    );
    return result.rows[0] || null;
  }

  async findUserByUsername(username) {
    const result = await db.query(
      'SELECT id FROM usuarios WHERE username = $1',
      [username]
    );
    return result.rows[0] || null;
  }

  async createUser(userData) {
    const {
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
    } = userData;

    const result = await db.query(
      `INSERT INTO usuarios (
        email, 
        password_hash, 
        nombre, 
        apellido, 
        username, 
        fecha_nacimiento, 
        pais_origen, 
        ciudad_origen, 
        idioma_preferido, 
        telefono, 
        tipo_viajero, 
        genero,
        fecha_registro, 
        fecha_actualizacion
      ) 
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
      RETURNING id, email, nombre, apellido, username, fecha_nacimiento, pais_origen, ciudad_origen, idioma_preferido, telefono, tipo_viajero, genero, fecha_registro`,
      [email, hashedPassword, nombre, apellido, username, fechaNacimiento, paisOrigen, ciudadOrigen, idiomaPreferido, telefono, tipoViajero, genero]
    );
    
    return result.rows[0];
  }

  async createUserPreferences(userId, preferencias) {
    const preferenciasPromises = preferencias.map(categoriaId => 
      db.query(
        `INSERT INTO preferencias_usuario (usuario_id, categoria_id, le_gusta, fecha_creacion, fecha_actualizacion)
         VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
         RETURNING id, categoria_id, le_gusta`,
        [userId, categoriaId]
      )
    );

    const preferenciasResults = await Promise.all(preferenciasPromises);
    return preferenciasResults.map(result => result.rows[0]);
  }

  async findUserForLogin(email) {
    const result = await db.query(
      'SELECT id, email, password_hash, nombre, apellido, fecha_registro FROM usuarios WHERE email = $1',
      [email]
    );
    return result.rows[0] || null;
  }

  async findUserById(userId) {
    const result = await db.query(
      'SELECT id, email, nombre, apellido, fecha_registro, fecha_actualizacion FROM usuarios WHERE id = $1',
      [userId]
    );
    return result.rows[0] || null;
  }

  async updateUserProfile(userId, profileData) {
    const {
      fechaNacimiento,
      paisOrigen,
      ciudadOrigen,
      idiomaPreferido,
      telefono,
      tipoViajero,
      genero
    } = profileData;

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
    
    return result.rows[0] || null;
  }

  async registerUserWithPreferences(userData, preferencias) {
    const client = await db.getClient();
    
    try {
      await client.query('BEGIN');

      // Check if user already exists
      const existingUser = await client.query(
        'SELECT id FROM usuarios WHERE email = $1',
        [userData.email]
      );

      if (existingUser.rows.length > 0) {
        throw new Error('USER_EMAIL_EXISTS');
      }

      const usernameExists = await client.query(
        'SELECT id FROM usuarios WHERE username = $1',
        [userData.username]
      );

      if (usernameExists.rows.length > 0) {
        throw new Error('USER_USERNAME_EXISTS');
      }

      // Create user
      const {
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
      } = userData;

      const userResult = await client.query(
        `INSERT INTO usuarios (
          email, 
          password_hash, 
          nombre, 
          apellido, 
          username, 
          fecha_nacimiento, 
          pais_origen, 
          ciudad_origen, 
          idioma_preferido, 
          telefono, 
          tipo_viajero, 
          genero,
          fecha_registro, 
          fecha_actualizacion
        ) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
        RETURNING id, email, nombre, apellido, username, fecha_nacimiento, pais_origen, ciudad_origen, idioma_preferido, telefono, tipo_viajero, genero, fecha_registro`,
        [email, hashedPassword, nombre, apellido, username, fechaNacimiento, paisOrigen, ciudadOrigen, idiomaPreferido, telefono, tipoViajero, genero]
      );
      
      const user = userResult.rows[0];

      // Insert user preferences
      const preferenciasPromises = preferencias.map(categoriaId => 
        client.query(
          `INSERT INTO preferencias_usuario (usuario_id, categoria_id, le_gusta, fecha_creacion, fecha_actualizacion)
           VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
           RETURNING id, categoria_id, le_gusta`,
          [user.id, categoriaId]
        )
      );

      const preferenciasResults = await Promise.all(preferenciasPromises);
      const userPreferencias = preferenciasResults.map(result => result.rows[0]);

      await client.query('COMMIT');

      return {
        user,
        preferencias: userPreferencias
      };

    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}

module.exports = new AuthRepository();
