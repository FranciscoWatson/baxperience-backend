const db = require('../config/database');

class ValoracionesController {
  async createValoracion(req, res) {
    try {
      const userId = req.user.userId;
      const { 
        poiId, 
        itinerarioId,
        puntuacionGeneral, 
        puntuacionUbicacion, 
        puntuacionServicio, 
        puntuacionAmbiente, 
        puntuacionAccesibilidad,
        comentario 
      } = req.body;

      // Validate input
      if (!poiId || !puntuacionGeneral) {
        return res.status(400).json({
          error: 'Required fields: poiId, puntuacionGeneral'
        });
      }

      if (puntuacionGeneral < 0 || puntuacionGeneral > 5) {
        return res.status(400).json({
          error: 'puntuacionGeneral must be between 0 and 5'
        });
      }

      // Check if POI exists
      const poiCheck = await db.query('SELECT id FROM pois WHERE id = $1', [poiId]);
      if (poiCheck.rows.length === 0) {
        return res.status(404).json({
          error: 'POI not found'
        });
      }

      // Check if user already rated this POI
      const existingRating = await db.query(
        'SELECT id FROM valoraciones WHERE usuario_id = $1 AND poi_id = $2',
        [userId, poiId]
      );

      if (existingRating.rows.length > 0) {
        return res.status(409).json({
          error: 'You have already rated this POI'
        });
      }

      // Create rating
      const result = await db.query(
        `INSERT INTO valoraciones 
         (usuario_id, poi_id, itinerario_id, puntuacion_general, puntuacion_ubicacion, 
          puntuacion_servicio, puntuacion_ambiente, puntuacion_accesibilidad, comentario)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
         RETURNING id, puntuacion_general, comentario, fecha_creacion`,
        [
          userId, 
          poiId, 
          itinerarioId || null,
          puntuacionGeneral,
          puntuacionUbicacion || null,
          puntuacionServicio || null,
          puntuacionAmbiente || null,
          puntuacionAccesibilidad || null,
          comentario || null
        ]
      );

      const valoracion = result.rows[0];

      res.status(201).json({
        message: 'Rating created successfully',
        valoracion: {
          id: valoracion.id,
          puntuacionGeneral: parseFloat(valoracion.puntuacion_general),
          comentario: valoracion.comentario,
          fechaCreacion: valoracion.fecha_creacion
        }
      });

    } catch (error) {
      console.error('Create rating error:', error);
      res.status(500).json({
        error: 'Internal server error while creating rating'
      });
    }
  }

  async updateValoracion(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;
      const { 
        puntuacionGeneral, 
        puntuacionUbicacion, 
        puntuacionServicio, 
        puntuacionAmbiente, 
        puntuacionAccesibilidad,
        comentario 
      } = req.body;

      // Check if rating exists and belongs to user
      const existingRating = await db.query(
        'SELECT id FROM valoraciones WHERE id = $1 AND usuario_id = $2',
        [id, userId]
      );

      if (existingRating.rows.length === 0) {
        return res.status(404).json({
          error: 'Rating not found'
        });
      }

      // Update rating
      const result = await db.query(
        `UPDATE valoraciones 
         SET puntuacion_general = COALESCE($1, puntuacion_general),
             puntuacion_ubicacion = COALESCE($2, puntuacion_ubicacion),
             puntuacion_servicio = COALESCE($3, puntuacion_servicio),
             puntuacion_ambiente = COALESCE($4, puntuacion_ambiente),
             puntuacion_accesibilidad = COALESCE($5, puntuacion_accesibilidad),
             comentario = COALESCE($6, comentario),
             fecha_actualizacion = CURRENT_TIMESTAMP
         WHERE id = $7 AND usuario_id = $8
         RETURNING id, puntuacion_general, puntuacion_ubicacion, puntuacion_servicio, 
                   puntuacion_ambiente, puntuacion_accesibilidad, comentario, fecha_actualizacion`,
        [
          puntuacionGeneral || null,
          puntuacionUbicacion || null,
          puntuacionServicio || null,
          puntuacionAmbiente || null,
          puntuacionAccesibilidad || null,
          comentario || null,
          id,
          userId
        ]
      );

      const valoracion = result.rows[0];

      res.status(200).json({
        message: 'Rating updated successfully',
        valoracion: {
          id: valoracion.id,
          puntuacionGeneral: parseFloat(valoracion.puntuacion_general),
          puntuacionUbicacion: valoracion.puntuacion_ubicacion ? parseFloat(valoracion.puntuacion_ubicacion) : null,
          puntuacionServicio: valoracion.puntuacion_servicio ? parseFloat(valoracion.puntuacion_servicio) : null,
          puntuacionAmbiente: valoracion.puntuacion_ambiente ? parseFloat(valoracion.puntuacion_ambiente) : null,
          puntuacionAccesibilidad: valoracion.puntuacion_accesibilidad ? parseFloat(valoracion.puntuacion_accesibilidad) : null,
          comentario: valoracion.comentario,
          fechaActualizacion: valoracion.fecha_actualizacion
        }
      });

    } catch (error) {
      console.error('Update rating error:', error);
      res.status(500).json({
        error: 'Internal server error while updating rating'
      });
    }
  }

  async getValoracionesByPoi(req, res) {
    try {
      const { poiId } = req.params;
      const { pagina = 1, limite = 10 } = req.query;

      const offset = (pagina - 1) * limite;

      const result = await db.query(
        `SELECT 
          v.id, v.puntuacion_general, v.puntuacion_ubicacion, v.puntuacion_servicio,
          v.puntuacion_ambiente, v.puntuacion_accesibilidad, v.comentario, v.fecha_creacion,
          u.username, u.nombre, u.apellido
         FROM valoraciones v
         JOIN usuarios u ON v.usuario_id = u.id
         WHERE v.poi_id = $1
         ORDER BY v.fecha_creacion DESC
         LIMIT $2 OFFSET $3`,
        [poiId, limite, offset]
      );

      const countResult = await db.query(
        'SELECT COUNT(*) FROM valoraciones WHERE poi_id = $1',
        [poiId]
      );

      const total = parseInt(countResult.rows[0].count);
      const totalPaginas = Math.ceil(total / limite);

      const valoraciones = result.rows.map(val => ({
        id: val.id,
        puntuacionGeneral: parseFloat(val.puntuacion_general),
        puntuacionUbicacion: val.puntuacion_ubicacion ? parseFloat(val.puntuacion_ubicacion) : null,
        puntuacionServicio: val.puntuacion_servicio ? parseFloat(val.puntuacion_servicio) : null,
        puntuacionAmbiente: val.puntuacion_ambiente ? parseFloat(val.puntuacion_ambiente) : null,
        puntuacionAccesibilidad: val.puntuacion_accesibilidad ? parseFloat(val.puntuacion_accesibilidad) : null,
        comentario: val.comentario,
        fechaCreacion: val.fecha_creacion,
        usuario: {
          username: val.username,
          nombre: val.nombre,
          apellido: val.apellido
        }
      }));

      res.status(200).json({
        valoraciones,
        paginacion: {
          pagina: parseInt(pagina),
          limite: parseInt(limite),
          total,
          totalPaginas
        }
      });

    } catch (error) {
      console.error('Get ratings by POI error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching ratings'
      });
    }
  }

  async getUserValoraciones(req, res) {
    try {
      const userId = req.user.userId;
      const { pagina = 1, limite = 10 } = req.query;

      const offset = (pagina - 1) * limite;

      const result = await db.query(
        `SELECT 
          v.id, v.puntuacion_general, v.comentario, v.fecha_creacion, v.fecha_actualizacion,
          p.id as poi_id, p.nombre as poi_nombre, p.direccion as poi_direccion
         FROM valoraciones v
         JOIN pois p ON v.poi_id = p.id
         WHERE v.usuario_id = $1
         ORDER BY v.fecha_creacion DESC
         LIMIT $2 OFFSET $3`,
        [userId, limite, offset]
      );

      const countResult = await db.query(
        'SELECT COUNT(*) FROM valoraciones WHERE usuario_id = $1',
        [userId]
      );

      const total = parseInt(countResult.rows[0].count);
      const totalPaginas = Math.ceil(total / limite);

      const valoraciones = result.rows.map(val => ({
        id: val.id,
        puntuacionGeneral: parseFloat(val.puntuacion_general),
        comentario: val.comentario,
        fechaCreacion: val.fecha_creacion,
        fechaActualizacion: val.fecha_actualizacion,
        poi: {
          id: val.poi_id,
          nombre: val.poi_nombre,
          direccion: val.poi_direccion
        }
      }));

      res.status(200).json({
        valoraciones,
        paginacion: {
          pagina: parseInt(pagina),
          limite: parseInt(limite),
          total,
          totalPaginas
        }
      });

    } catch (error) {
      console.error('Get user ratings error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching user ratings'
      });
    }
  }
}

module.exports = new ValoracionesController();
