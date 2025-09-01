const db = require('../config/database');

class ItineraryRepository {
  async createItinerary(userId, itineraryData) {
    const { nombre, descripcion, fechaInicio, fechaFin, modoTransportePreferido } = itineraryData;
    
    const result = await db.query(
      `INSERT INTO itinerarios (usuario_id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion) 
       VALUES ($1, $2, $3, $4, $5, $6, 'planificado', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
       RETURNING id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion`,
      [userId, nombre, descripcion || null, fechaInicio, fechaFin, modoTransportePreferido || null]
    );

    return result.rows[0];
  }

  async getUserItineraries(userId, limite, offset) {
    const result = await db.query(
      `SELECT id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion 
       FROM itinerarios 
       WHERE usuario_id = $1 
       ORDER BY fecha_creacion DESC 
       LIMIT $2 OFFSET $3`,
      [userId, limite, offset]
    );

    return result.rows;
  }

  async getUserItinerariesCount(userId) {
    const result = await db.query(
      'SELECT COUNT(*) FROM itinerarios WHERE usuario_id = $1',
      [userId]
    );

    return parseInt(result.rows[0].count);
  }

  async getItineraryById(itineraryId, userId) {
    const result = await db.query(
      `SELECT id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion 
       FROM itinerarios 
       WHERE id = $1 AND usuario_id = $2`,
      [itineraryId, userId]
    );

    return result.rows[0] || null;
  }

  async updateItinerary(itineraryId, userId, updateData) {
    const { nombre, descripcion, fechaInicio, fechaFin, modoTransportePreferido } = updateData;
    
    const result = await db.query(
      `UPDATE itinerarios 
       SET nombre = COALESCE($1, nombre), 
           descripcion = COALESCE($2, descripcion), 
           fecha_inicio = COALESCE($3, fecha_inicio),
           fecha_fin = COALESCE($4, fecha_fin),
           modo_transporte_preferido = COALESCE($5, modo_transporte_preferido),
           fecha_actualizacion = CURRENT_TIMESTAMP
       WHERE id = $6 AND usuario_id = $7 
       RETURNING id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion`,
      [
        nombre || null,
        descripcion || null,
        fechaInicio || null,
        fechaFin || null,
        modoTransportePreferido || null,
        itineraryId,
        userId
      ]
    );

    return result.rows[0] || null;
  }

  async deleteItinerary(itineraryId, userId) {
    const result = await db.query(
      'DELETE FROM itinerarios WHERE id = $1 AND usuario_id = $2 RETURNING id',
      [itineraryId, userId]
    );

    return result.rows[0] || null;
  }

  async checkItineraryOwnership(itineraryId, userId) {
    const result = await db.query(
      'SELECT id FROM itinerarios WHERE id = $1 AND usuario_id = $2',
      [itineraryId, userId]
    );

    return result.rows[0] || null;
  }

  async addActivityToItinerary(itineraryId, activityData) {
    const {
      tipoActividad,
      poiId,
      eventoId,
      diaVisita,
      ordenEnDia,
      horaInicioPlanificada,
      horaFinPlanificada,
      tiempoEstimadoMinutos,
      notasPlanificacion
    } = activityData;

    const result = await db.query(
      `INSERT INTO itinerario_actividades 
       (itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, 
        hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos, notas_planificacion)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id, tipo_actividad, dia_visita, orden_en_dia, fecha_agregado`,
      [
        itineraryId,
        tipoActividad === 'poi' ? poiId : null,
        tipoActividad === 'evento' ? eventoId : null,
        tipoActividad,
        diaVisita,
        ordenEnDia,
        horaInicioPlanificada || null,
        horaFinPlanificada || null,
        tiempoEstimadoMinutos || null,
        notasPlanificacion || null
      ]
    );

    return result.rows[0];
  }

  async getItineraryActivities(itineraryId) {
    const result = await db.query(
      `SELECT 
        ia.id, ia.tipo_actividad, ia.dia_visita, ia.orden_en_dia,
        ia.hora_inicio_planificada, ia.hora_fin_planificada, ia.tiempo_estimado_minutos,
        ia.hora_inicio_real, ia.hora_fin_real, ia.fue_realizada,
        ia.notas_planificacion, ia.notas_realizacion,
        p.id as poi_id, p.nombre as poi_nombre, p.latitud as poi_latitud, p.longitud as poi_longitud, p.direccion as poi_direccion,
        e.id as evento_id, e.nombre as evento_nombre, e.fecha_inicio as evento_fecha_inicio, e.fecha_fin as evento_fecha_fin
       FROM itinerario_actividades ia
       LEFT JOIN pois p ON ia.poi_id = p.id
       LEFT JOIN eventos e ON ia.evento_id = e.id
       WHERE ia.itinerario_id = $1
       ORDER BY ia.dia_visita, ia.orden_en_dia`,
      [itineraryId]
    );

    return result.rows;
  }

  async createItineraryWithLocation(userId, itineraryData) {
    const { 
      nombre, 
      descripcion, 
      fechaInicio, 
      fechaFin, 
      modoTransportePreferido,
      ubicacionLatitud,
      ubicacionLongitud,
      ubicacionDireccion,
      tiempoEstimadoHoras
    } = itineraryData;
    
    const result = await db.query(
      `INSERT INTO itinerarios (
        usuario_id, nombre, descripcion, fecha_inicio, fecha_fin, 
        modo_transporte_preferido, estado, ubicacion_latitud, ubicacion_longitud, 
        ubicacion_direccion, tiempo_estimado_horas, fecha_creacion, fecha_actualizacion
      ) 
       VALUES ($1, $2, $3, $4, $5, $6, 'planificado', $7, $8, $9, $10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
       RETURNING id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion`,
      [
        userId, 
        nombre, 
        descripcion || null, 
        fechaInicio, 
        fechaFin, 
        modoTransportePreferido || null,
        ubicacionLatitud || null,
        ubicacionLongitud || null,
        ubicacionDireccion || null,
        tiempoEstimadoHoras || null
      ]
    );

    return result.rows[0];
  }

  async findPOIByName(nombre) {
    try {
      const result = await db.query(
        `SELECT id FROM pois WHERE LOWER(nombre) LIKE LOWER($1) LIMIT 1`,
        [`%${nombre}%`]
      );
      
      return result.rows[0]?.id || null;
    } catch (error) {
      console.error('Error finding POI by name:', error);
      return null;
    }
  }
}

module.exports = new ItineraryRepository();
