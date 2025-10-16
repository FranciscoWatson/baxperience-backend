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
    const { 
      nombre, 
      descripcion, 
      fechaInicio, 
      fechaFin, 
      modoTransportePreferido, 
      estado,
      valoracionItinerario,
      comentariosItinerario,
      recomendaria
    } = updateData;
    
    const result = await db.query(
      `UPDATE itinerarios 
       SET nombre = COALESCE($1, nombre), 
           descripcion = COALESCE($2, descripcion), 
           fecha_inicio = COALESCE($3, fecha_inicio),
           fecha_fin = COALESCE($4, fecha_fin),
           modo_transporte_preferido = COALESCE($5, modo_transporte_preferido),
           estado = COALESCE($6, estado),
           valoracion_itinerario = COALESCE($7, valoracion_itinerario),
           comentarios_itinerario = COALESCE($8, comentarios_itinerario),
           recomendaria = COALESCE($9, recomendaria),
           fecha_actualizacion = CURRENT_TIMESTAMP
       WHERE id = $10 AND usuario_id = $11 
       RETURNING id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, 
                 valoracion_itinerario, comentarios_itinerario, recomendaria, fecha_creacion, fecha_actualizacion`,
      [
        nombre || null,
        descripcion || null,
        fechaInicio || null,
        fechaFin || null,
        modoTransportePreferido || null,
        estado || null,
        valoracionItinerario !== undefined ? valoracionItinerario : null,
        comentariosItinerario || null,
        recomendaria !== undefined ? recomendaria : null,
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

  async getUserItinerariesWithActivities(userId, limite = 20, offset = 0) {
    try {
      // Get itineraries
      const itinerariesResult = await db.query(
        `SELECT 
          i.id, 
          i.nombre, 
          i.descripcion, 
          i.fecha_inicio, 
          i.fecha_fin, 
          i.modo_transporte_preferido, 
          i.estado, 
          i.ubicacion_latitud,
          i.ubicacion_longitud,
          i.ubicacion_direccion,
          i.tiempo_estimado_horas,
          i.fecha_creacion, 
          i.fecha_actualizacion
        FROM itinerarios i
        WHERE i.usuario_id = $1 
        ORDER BY i.fecha_creacion DESC 
        LIMIT $2 OFFSET $3`,
        [userId, limite, offset]
      );

      const itineraries = itinerariesResult.rows;

      if (itineraries.length === 0) {
        return [];
      }

      // Get all activities for these itineraries
      const itineraryIds = itineraries.map(it => it.id);
      const activitiesResult = await db.query(
        `SELECT 
          ai.id as actividad_id,
          ai.itinerario_id,
          ai.tipo_actividad,
          ai.poi_id,
          ai.evento_id,
          ai.dia_visita,
          ai.orden_en_dia,
          ai.hora_inicio_planificada,
          ai.hora_fin_planificada,
          ai.tiempo_estimado_minutos,
          ai.notas_planificacion,
          ai.fue_realizada as actividad_estado,
          -- POI data
          p.nombre as poi_nombre,
          p.categoria_id as poi_categoria_id,
          c.nombre as poi_categoria,
          s.nombre as poi_subcategoria,
          p.barrio as poi_barrio,
          p.latitud as poi_latitud,
          p.longitud as poi_longitud,
          p.valoracion_promedio as poi_valoracion,
          p.numero_valoraciones as poi_numero_valoraciones,
          -- Event data
          e.nombre as evento_nombre,
          e.ubicacion_especifica as evento_lugar,
          e.fecha_inicio as evento_fecha_inicio,
          e.fecha_fin as evento_fecha_fin,
          e.latitud as evento_latitud,
          e.longitud as evento_longitud,
          e.categoria_evento as evento_categoria
        FROM itinerario_actividades ai
        LEFT JOIN pois p ON ai.poi_id = p.id
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
        LEFT JOIN eventos e ON ai.evento_id = e.id
        WHERE ai.itinerario_id = ANY($1)
        ORDER BY ai.itinerario_id, ai.dia_visita, ai.orden_en_dia`,
        [itineraryIds]
      );

      // Group activities by itinerary and day
      const activitiesByItinerary = {};
      activitiesResult.rows.forEach(activity => {
        if (!activitiesByItinerary[activity.itinerario_id]) {
          activitiesByItinerary[activity.itinerario_id] = {};
        }
        
        const day = activity.dia_visita;
        if (!activitiesByItinerary[activity.itinerario_id][day]) {
          activitiesByItinerary[activity.itinerario_id][day] = [];
        }

        // Format activity data
        const formattedActivity = {
          id: activity.actividad_id,
          tipo_actividad: activity.tipo_actividad,
          dia_visita: activity.dia_visita,
          orden_en_dia: activity.orden_en_dia,
          hora_inicio_planificada: activity.hora_inicio_planificada,
          hora_fin_planificada: activity.hora_fin_planificada,
          tiempo_estimado_minutos: activity.tiempo_estimado_minutos,
          notas_planificacion: activity.notas_planificacion,
          estado: activity.actividad_estado
        };

        // Add POI or Event details
        if (activity.tipo_actividad === 'poi' && activity.poi_id) {
          formattedActivity.poi = {
            id: activity.poi_id,
            nombre: activity.poi_nombre,
            categoria: activity.poi_categoria,
            categoria_id: activity.poi_categoria_id,
            subcategoria: activity.poi_subcategoria,
            barrio: activity.poi_barrio,
            latitud: parseFloat(activity.poi_latitud),
            longitud: parseFloat(activity.poi_longitud),
            valoracion_promedio: parseFloat(activity.poi_valoracion) || 0,
            numero_valoraciones: parseInt(activity.poi_numero_valoraciones) || 0
          };
        } else if (activity.tipo_actividad === 'evento' && activity.evento_id) {
          formattedActivity.evento = {
            id: activity.evento_id,
            nombre: activity.evento_nombre,
            lugar: activity.evento_lugar,
            fecha_inicio: activity.evento_fecha_inicio,
            fecha_fin: activity.evento_fecha_fin,
            latitud: activity.evento_latitud ? parseFloat(activity.evento_latitud) : null,
            longitud: activity.evento_longitud ? parseFloat(activity.evento_longitud) : null,
            categoria: activity.evento_categoria
          };
        }

        activitiesByItinerary[activity.itinerario_id][day].push(formattedActivity);
      });

      // Attach activities to itineraries
      const result = itineraries.map(itinerary => {
        const activities = activitiesByItinerary[itinerary.id] || {};
        const days = Object.keys(activities).sort((a, b) => parseInt(a) - parseInt(b));
        
        // Calculate total days
        const startDate = new Date(itinerary.fecha_inicio);
        const endDate = new Date(itinerary.fecha_fin);
        const totalDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;

        // Count total activities
        const totalActivities = Object.values(activities).reduce((sum, dayActivities) => sum + dayActivities.length, 0);

        return {
          id: itinerary.id,
          nombre: itinerary.nombre,
          descripcion: itinerary.descripcion,
          fecha_inicio: itinerary.fecha_inicio,
          fecha_fin: itinerary.fecha_fin,
          total_dias: totalDays,
          modo_transporte_preferido: itinerary.modo_transporte_preferido,
          estado: itinerary.estado,
          ubicacion_origen: {
            latitud: itinerary.ubicacion_latitud,
            longitud: itinerary.ubicacion_longitud,
            direccion: itinerary.ubicacion_direccion
          },
          tiempo_estimado_horas: itinerary.tiempo_estimado_horas,
          fecha_creacion: itinerary.fecha_creacion,
          fecha_actualizacion: itinerary.fecha_actualizacion,
          total_actividades: totalActivities,
          actividades_por_dia: activities,
          dias_con_actividades: days.map(d => parseInt(d))
        };
      });

      return result;
    } catch (error) {
      console.error('Error getting user itineraries with activities:', error);
      throw error;
    }
  }
}

module.exports = new ItineraryRepository();
