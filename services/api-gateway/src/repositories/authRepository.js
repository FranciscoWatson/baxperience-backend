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
    // Filtrar cualquier valor nulo o indefinido
    const validPreferencias = preferencias.filter(categoriaId => 
      categoriaId !== null && categoriaId !== undefined && categoriaId !== ''
    );
    
    if (validPreferencias.length === 0) {
      return []; // No hay preferencias válidas para insertar
    }
    
    // Log para depuración
    console.log('Creating user preferences for userId:', userId);
    console.log('Valid preferencias:', validPreferencias);
    
    const preferenciasPromises = validPreferencias.map(categoriaId => {
      // Convertir explícitamente a entero
      const catId = parseInt(categoriaId, 10);
      
      // Verificar que sea un número válido
      if (isNaN(catId)) {
        console.error('Invalid category ID:', categoriaId);
        return Promise.resolve({ rows: [{ id: null, categoria_id: null, le_gusta: true }] });
      }
      
      console.log('Inserting preference:', catId, 'for user:', userId);
      
      return db.query(
        `INSERT INTO preferencias_usuario (usuario_id, categoria_id, le_gusta, fecha_creacion, fecha_actualizacion)
         VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
         RETURNING id, categoria_id, le_gusta`,
        [userId, catId]
      );
    });

    const preferenciasResults = await Promise.all(preferenciasPromises);
    // Filtrar los resultados nulos (de preferencias inválidas)
    return preferenciasResults
      .filter(result => result.rows && result.rows.length > 0 && result.rows[0].categoria_id !== null)
      .map(result => result.rows[0]);
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
      // Filtrar cualquier valor nulo o indefinido
      const validPreferencias = preferencias.filter(categoriaId => 
        categoriaId !== null && categoriaId !== undefined && categoriaId !== ''
      );
      
      console.log('Valid preferencias in registerUserWithPreferences:', validPreferencias);
      
      if (validPreferencias.length === 0) {
        console.warn('No valid preferences found for user:', user.id);
      }
      
      const preferenciasPromises = validPreferencias.map(categoriaId => {
        // Convertir explícitamente a entero
        const catId = parseInt(categoriaId, 10);
        
        // Verificar que sea un número válido
        if (isNaN(catId)) {
          console.error('Invalid category ID in registerUserWithPreferences:', categoriaId);
          return Promise.resolve({ rows: [] });
        }
        
        console.log('Inserting preference in registerUserWithPreferences:', catId, 'for user:', user.id);
        
        return client.query(
          `INSERT INTO preferencias_usuario (usuario_id, categoria_id, le_gusta, fecha_creacion, fecha_actualizacion)
           VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
           RETURNING id, categoria_id, le_gusta`,
          [user.id, catId]
        );
      });

      const preferenciasResults = await Promise.all(preferenciasPromises);
      const userPreferencias = preferenciasResults
        .filter(result => result.rows && result.rows.length > 0)
        .map(result => result.rows[0]);

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

  /**
   * Update user password
   */
  async updatePassword(userId, hashedPassword) {
    const query = `
      UPDATE usuarios
      SET password_hash = $1,
          fecha_actualizacion = CURRENT_TIMESTAMP
      WHERE id = $2
      RETURNING id, email
    `;
    
    try {
      const result = await db.query(query, [hashedPassword, userId]);
      return result.rows[0];
    } catch (error) {
      console.error('Error updating password:', error);
      throw error;
    }
  }

  /**
   * Get complete user profile with all fields
   */
  async getUserProfile(userId) {
    const query = `
      SELECT 
        id,
        username,
        email,
        nombre,
        apellido,
        fecha_nacimiento,
        genero,
        telefono,
        pais_origen,
        ciudad_origen,
        idioma_preferido,
        tipo_viajero,
        duracion_viaje_promedio,
        profile_image_url,
        fecha_registro,
        fecha_actualizacion
      FROM usuarios
      WHERE id = $1
    `;
    
    try {
      const result = await db.query(query, [userId]);
      return result.rows[0] || null;
    } catch (error) {
      console.error('Error getting user profile:', error);
      throw error;
    }
  }

  /**
   * Update user profile information
   */
  async updateUserInfo(userId, userData) {
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
    } = userData;

    const query = `
      UPDATE usuarios
      SET 
        nombre = COALESCE($1, nombre),
        apellido = COALESCE($2, apellido),
        fecha_nacimiento = COALESCE($3, fecha_nacimiento),
        genero = COALESCE($4, genero),
        telefono = COALESCE($5, telefono),
        pais_origen = COALESCE($6, pais_origen),
        ciudad_origen = COALESCE($7, ciudad_origen),
        idioma_preferido = COALESCE($8, idioma_preferido),
        tipo_viajero = COALESCE($9, tipo_viajero),
        duracion_viaje_promedio = COALESCE($10, duracion_viaje_promedio),
        fecha_actualizacion = CURRENT_TIMESTAMP
      WHERE id = $11
      RETURNING 
        id,
        username,
        email,
        nombre,
        apellido,
        fecha_nacimiento,
        genero,
        telefono,
        pais_origen,
        ciudad_origen,
        idioma_preferido,
        tipo_viajero,
        duracion_viaje_promedio,
        profile_image_url,
        fecha_actualizacion
    `;

    try {
      const result = await db.query(query, [
        nombre,
        apellido,
        fecha_nacimiento,
        genero,
        telefono,
        pais_origen,
        ciudad_origen,
        idioma_preferido,
        tipo_viajero,
        duracion_viaje_promedio,
        userId
      ]);
      return result.rows[0] || null;
    } catch (error) {
      console.error('Error updating user info:', error);
      throw error;
    }
  }

  /**
   * Update user profile image URL
   */
  async updateProfileImage(userId, imageUrl) {
    const query = `
      UPDATE usuarios
      SET 
        profile_image_url = $1,
        fecha_actualizacion = CURRENT_TIMESTAMP
      WHERE id = $2
      RETURNING 
        id,
        username,
        email,
        nombre,
        apellido,
        profile_image_url,
        fecha_actualizacion
    `;

    try {
      const result = await db.query(query, [imageUrl, userId]);
      return result.rows[0] || null;
    } catch (error) {
      console.error('Error updating profile image:', error);
      throw error;
    }
  }
}

module.exports = new AuthRepository();
