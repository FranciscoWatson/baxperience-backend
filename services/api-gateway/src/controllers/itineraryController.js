const itineraryRepository = require('../repositories/itineraryRepository');
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
      const itineraryData = {
        nombre,
        descripcion,
        fechaInicio,
        fechaFin,
        modoTransportePreferido
      };

      const itinerary = await itineraryRepository.createItinerary(userId, itineraryData);

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

      const itinerarios = await itineraryRepository.getUserItineraries(userId, limite, offset);
      const total = await itineraryRepository.getUserItinerariesCount(userId);

      const totalPaginas = Math.ceil(total / limite);

      const formattedItinerarios = itinerarios.map(itinerary => ({
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
        itinerarios: formattedItinerarios,
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

      const itinerary = await itineraryRepository.getItineraryById(id, userId);

      if (!itinerary) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

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
      const existingItinerary = await itineraryRepository.checkItineraryOwnership(id, userId);

      if (!existingItinerary) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      // Update itinerary
      const updateData = {
        nombre,
        descripcion,
        fechaInicio,
        fechaFin,
        modoTransportePreferido
      };

      const itinerary = await itineraryRepository.updateItinerary(id, userId, updateData);

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

      const deletedItinerary = await itineraryRepository.deleteItinerary(id, userId);

      if (!deletedItinerary) {
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
      const itineraryCheck = await itineraryRepository.checkItineraryOwnership(itinerarioId, userId);

      if (!itineraryCheck) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      // Add activity
      const activityData = {
        tipoActividad,
        poiId,
        eventoId,
        diaVisita,
        ordenEnDia,
        horaInicioPlanificada,
        horaFinPlanificada,
        tiempoEstimadoMinutos,
        notasPlanificacion
      };

      const activity = await itineraryRepository.addActivityToItinerary(itinerarioId, activityData);

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
      const itineraryCheck = await itineraryRepository.checkItineraryOwnership(itinerarioId, userId);

      if (!itineraryCheck) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      const activities = await itineraryRepository.getItineraryActivities(itinerarioId);

      const formattedActivities = activities.map(activity => ({
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
        actividades: formattedActivities
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
