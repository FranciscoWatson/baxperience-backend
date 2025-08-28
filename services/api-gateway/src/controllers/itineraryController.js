const db = require('../config/database');
const kafkaService = require('../services/kafkaService');

class ItineraryController {
  async createItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { nombre, descripcion, fechaInicio, fechaFin, modoTransportePreferido } = req.body;

      // Validate input
      if (!nombre || !fechaInicio || !fechaFin) {
        return res.status(400).json({
          error: 'Required fields: nombre, fechaInicio, fechaFin'
        });
      }

      // Create itinerary
      const result = await db.query(
        `INSERT INTO itinerarios (usuario_id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion) 
         VALUES ($1, $2, $3, $4, $5, $6, 'planificado', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
         RETURNING id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion`,
        [userId, nombre, descripcion || null, fechaInicio, fechaFin, modoTransportePreferido || null]
      );

      const itinerary = result.rows[0];

      res.status(201).json({
        message: 'Itinerary created successfully',
        itinerario: {
          id: itinerary.id,
          nombre: itinerary.nombre,
          descripcion: itinerary.descripcion,
          fechaInicio: itinerary.fecha_inicio,
          fechaFin: itinerary.fecha_fin,
          modoTransportePreferido: itinerary.modo_transporte_preferido,
          estado: itinerary.estado,
          fechaCreacion: itinerary.fecha_creacion
        }
      });

    } catch (error) {
      console.error('Create itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while creating itinerary'
      });
    }
  }

  async getUserItineraries(req, res) {
    try {
      const userId = req.user.userId;
      const { pagina = 1, limite = 10 } = req.query;

      const offset = (pagina - 1) * limite;

      const result = await db.query(
        `SELECT id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion 
         FROM itinerarios 
         WHERE usuario_id = $1 
         ORDER BY fecha_creacion DESC 
         LIMIT $2 OFFSET $3`,
        [userId, limite, offset]
      );

      const countResult = await db.query(
        'SELECT COUNT(*) FROM itinerarios WHERE usuario_id = $1',
        [userId]
      );

      const total = parseInt(countResult.rows[0].count);
      const totalPaginas = Math.ceil(total / limite);

      const itinerarios = result.rows.map(itinerary => ({
        id: itinerary.id,
        nombre: itinerary.nombre,
        descripcion: itinerary.descripcion,
        fechaInicio: itinerary.fecha_inicio,
        fechaFin: itinerary.fecha_fin,
        modoTransportePreferido: itinerary.modo_transporte_preferido,
        estado: itinerary.estado,
        fechaCreacion: itinerary.fecha_creacion,
        fechaActualizacion: itinerary.fecha_actualizacion
      }));

      res.status(200).json({
        itinerarios,
        paginacion: {
          pagina: parseInt(pagina),
          limite: parseInt(limite),
          total,
          totalPaginas
        }
      });

    } catch (error) {
      console.error('Get user itineraries error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching itineraries'
      });
    }
  }

  async getItineraryById(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;

      const result = await db.query(
        `SELECT id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado, fecha_creacion, fecha_actualizacion 
         FROM itinerarios 
         WHERE id = $1 AND usuario_id = $2`,
        [id, userId]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      const itinerary = result.rows[0];

      res.status(200).json({
        itinerario: {
          id: itinerary.id,
          nombre: itinerary.nombre,
          descripcion: itinerary.descripcion,
          fechaInicio: itinerary.fecha_inicio,
          fechaFin: itinerary.fecha_fin,
          modoTransportePreferido: itinerary.modo_transporte_preferido,
          estado: itinerary.estado,
          fechaCreacion: itinerary.fecha_creacion,
          fechaActualizacion: itinerary.fecha_actualizacion
        }
      });

    } catch (error) {
      console.error('Get itinerary by ID error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching itinerary'
      });
    }
  }

  async updateItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;
      const { nombre, descripcion, fechaInicio, fechaFin, modoTransportePreferido } = req.body;

      // Check if itinerary exists and belongs to user
      const existingResult = await db.query(
        'SELECT id FROM itinerarios WHERE id = $1 AND usuario_id = $2',
        [id, userId]
      );

      if (existingResult.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      // Update itinerary
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
          id,
          userId
        ]
      );

      const itinerary = result.rows[0];

      res.status(200).json({
        message: 'Itinerary updated successfully',
        itinerario: {
          id: itinerary.id,
          nombre: itinerary.nombre,
          descripcion: itinerary.descripcion,
          fechaInicio: itinerary.fecha_inicio,
          fechaFin: itinerary.fecha_fin,
          modoTransportePreferido: itinerary.modo_transporte_preferido,
          estado: itinerary.estado,
          fechaCreacion: itinerary.fecha_creacion,
          fechaActualizacion: itinerary.fecha_actualizacion
        }
      });

    } catch (error) {
      console.error('Update itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while updating itinerary'
      });
    }
  }

  async deleteItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;

      const result = await db.query(
        'DELETE FROM itinerarios WHERE id = $1 AND usuario_id = $2 RETURNING id',
        [id, userId]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      res.status(200).json({
        message: 'Itinerary deleted successfully'
      });

    } catch (error) {
      console.error('Delete itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while deleting itinerary'
      });
    }
  }

  async addActivityToItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { itinerarioId } = req.params;
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
      } = req.body;

      // Validate input
      if (!tipoActividad || !diaVisita || !ordenEnDia) {
        return res.status(400).json({
          error: 'Required fields: tipoActividad, diaVisita, ordenEnDia'
        });
      }

      if (tipoActividad === 'poi' && !poiId) {
        return res.status(400).json({
          error: 'poiId is required when tipoActividad is poi'
        });
      }

      if (tipoActividad === 'evento' && !eventoId) {
        return res.status(400).json({
          error: 'eventoId is required when tipoActividad is evento'
        });
      }

      // Verify itinerary belongs to user
      const itineraryCheck = await db.query(
        'SELECT id FROM itinerarios WHERE id = $1 AND usuario_id = $2',
        [itinerarioId, userId]
      );

      if (itineraryCheck.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      // Add activity
      const result = await db.query(
        `INSERT INTO itinerario_actividades 
         (itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, 
          hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos, notas_planificacion)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
         RETURNING id, tipo_actividad, dia_visita, orden_en_dia, fecha_agregado`,
        [
          itinerarioId,
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

      const activity = result.rows[0];

      res.status(201).json({
        message: 'Activity added to itinerary successfully',
        actividad: {
          id: activity.id,
          tipoActividad: activity.tipo_actividad,
          diaVisita: activity.dia_visita,
          ordenEnDia: activity.orden_en_dia,
          fechaAgregado: activity.fecha_agregado
        }
      });

    } catch (error) {
      console.error('Add activity to itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while adding activity to itinerary'
      });
    }
  }

  async getItineraryActivities(req, res) {
    try {
      const userId = req.user.userId;
      const { itinerarioId } = req.params;

      // Verify itinerary belongs to user
      const itineraryCheck = await db.query(
        'SELECT id FROM itinerarios WHERE id = $1 AND usuario_id = $2',
        [itinerarioId, userId]
      );

      if (itineraryCheck.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

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
        [itinerarioId]
      );

      const activities = result.rows.map(activity => ({
        id: activity.id,
        tipoActividad: activity.tipo_actividad,
        diaVisita: activity.dia_visita,
        ordenEnDia: activity.orden_en_dia,
        horaInicioPlanificada: activity.hora_inicio_planificada,
        horaFinPlanificada: activity.hora_fin_planificada,
        tiempoEstimadoMinutos: activity.tiempo_estimado_minutos,
        horaInicioReal: activity.hora_inicio_real,
        horaFinReal: activity.hora_fin_real,
        fueRealizada: activity.fue_realizada,
        notasPlanificacion: activity.notas_planificacion,
        notasRealizacion: activity.notas_realizacion,
        poi: activity.poi_id ? {
          id: activity.poi_id,
          nombre: activity.poi_nombre,
          latitud: parseFloat(activity.poi_latitud),
          longitud: parseFloat(activity.poi_longitud),
          direccion: activity.poi_direccion
        } : null,
        evento: activity.evento_id ? {
          id: activity.evento_id,
          nombre: activity.evento_nombre,
          fechaInicio: activity.evento_fecha_inicio,
          fechaFin: activity.evento_fecha_fin
        } : null
      }));

      res.status(200).json({
        actividades: activities
      });

    } catch (error) {
      console.error('Get itinerary activities error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching itinerary activities'
      });
    }
  }

  async generatePersonalizedItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { 
        fecha_visita, 
        hora_inicio, 
        duracion_horas, 
        categorias_preferidas, 
        zona_preferida, 
        presupuesto 
      } = req.body;

      // Validaciones básicas
      if (!fecha_visita || !hora_inicio || !duracion_horas) {
        return res.status(400).json({
          error: 'Required fields: fecha_visita, hora_inicio, duracion_horas'
        });
      }

      // Validar formato de fecha
      const fechaRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (!fechaRegex.test(fecha_visita)) {
        return res.status(400).json({
          error: 'fecha_visita must be in format YYYY-MM-DD'
        });
      }

      // Validar formato de hora
      const horaRegex = /^\d{2}:\d{2}$/;
      if (!horaRegex.test(hora_inicio)) {
        return res.status(400).json({
          error: 'hora_inicio must be in format HH:MM'
        });
      }

      // Validar duración
      if (duracion_horas < 1 || duracion_horas > 12) {
        return res.status(400).json({
          error: 'duracion_horas must be between 1 and 12'
        });
      }

      // Construir los datos de la solicitud
      const requestData = {
        fecha_visita,
        hora_inicio,
        duracion_horas,
        categorias_preferidas: categorias_preferidas || null,
        zona_preferida: zona_preferida || null,
        presupuesto: presupuesto || null
      };

      try {
        // Enviar solicitud a través de Kafka y esperar respuesta
        const { requestId, response } = await kafkaService.sendItineraryRequestAndWait(userId, requestData, 45000);

        // Procesar respuesta
        if (response.status === 'success') {
          const data = response.data || {};
          
          res.status(200).json({
            message: 'Itinerary generated successfully',
            request_id: requestId,
            itinerario: {
              id: data.itinerario_id,
              actividades: data.actividades || [],
              preferencias_usadas: data.preferencias_usadas || {},
              metadata: {
                processing_time_seconds: data.processing_metadata?.processing_time_seconds,
                timestamp: response.timestamp
              }
            }
          });

        } else if (response.status === 'error') {
          const error = response.error || {};
          
          res.status(400).json({
            error: 'Error generating itinerary',
            message: error.message || 'Unknown error occurred',
            suggestions: error.suggestions || [],
            request_id: requestId
          });

        } else {
          res.status(500).json({
            error: 'Unexpected response format from itinerary service',
            request_id: requestId
          });
        }

      } catch (kafkaError) {
        console.error('Kafka error in generatePersonalizedItinerary:', kafkaError);
        
        if (kafkaError.message.includes('Timeout')) {
          res.status(504).json({
            error: 'Timeout generating itinerary',
            message: 'The itinerary service is taking too long to respond. Please try again later.'
          });
        } else {
          res.status(503).json({
            error: 'Service unavailable',
            message: 'The itinerary service is currently unavailable. Please try again later.'
          });
        }
      }

    } catch (error) {
      console.error('Generate personalized itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while generating personalized itinerary'
      });
    }
  }
}

module.exports = new ItineraryController();
