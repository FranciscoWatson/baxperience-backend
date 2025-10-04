const itineraryRepository = require('../repositories/itineraryRepository');
const kafkaService = require('../services/kafkaService');
const db = require('../config/database');

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
      const { pagina = 1, limite = 20, con_actividades = 'true' } = req.query;

      const offset = (pagina - 1) * limite;
      
      let itinerarios, total;

      // If con_actividades is true, get full itineraries with activities
      if (con_actividades === 'true') {
        itinerarios = await itineraryRepository.getUserItinerariesWithActivities(userId, limite, offset);
        total = await itineraryRepository.getUserItinerariesCount(userId);
        
        console.log(`📋 Retrieved ${itinerarios.length} itineraries with activities for user ${userId}`);
      } else {
        // Otherwise, just get basic info
        itinerarios = await itineraryRepository.getUserItineraries(userId, limite, offset);
        total = await itineraryRepository.getUserItinerariesCount(userId);
      }

      const totalPaginas = Math.ceil(total / limite);

      res.status(200).json({
        itinerarios: itinerarios,
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
        error: 'Internal server error while fetching itineraries',
        details: error.message
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
      const { nombre, descripcion, fechaInicio, fechaFin, modoTransportePreferido, estado } = req.body;

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
        modoTransportePreferido,
        estado
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
        name,
        fecha_visita,
        fecha_fin,  // NEW: Optional end date for multi-day trips
        hora_inicio, 
        duracion_horas, 
        longitud_origen,
        latitud_origen,
        zona_preferida,
        ubicacion_direccion  // Nueva propiedad para la dirección literal
      } = req.body;

      // Validaciones básicas
      if (!name || !fecha_visita || !hora_inicio || !duracion_horas || longitud_origen === undefined || latitud_origen === undefined) {
        return res.status(400).json({
          error: 'Required fields: name, fecha_visita, hora_inicio, duracion_horas, longitud_origen, latitud_origen'
        });
      }      
      
      // Validar formato de fecha
      const fechaRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (!fechaRegex.test(fecha_visita)) {
        return res.status(400).json({
          error: 'fecha_visita must be in format YYYY-MM-DD'
        });
      }

      // Validar fecha_fin si se proporciona
      const finalEndDate = fecha_fin || fecha_visita;
      if (!fechaRegex.test(finalEndDate)) {
        return res.status(400).json({
          error: 'fecha_fin must be in format YYYY-MM-DD'
        });
      }

      // Calcular número de días
      const startDate = new Date(fecha_visita);
      const endDate = new Date(finalEndDate);
      const daysDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;

      if (daysDiff < 1 || daysDiff > 7) {
        return res.status(400).json({
          error: 'Trip duration must be between 1 and 7 days'
        });
      }

      console.log(`🗓️  Generating ${daysDiff}-day itinerary from ${fecha_visita} to ${finalEndDate}`);
      
      // Validar que fecha_fin no sea anterior a fecha_visita
      if (endDate < startDate) {
        return res.status(400).json({
          error: 'fecha_fin cannot be before fecha_visita'
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

      // Validar coordenadas
      if (typeof longitud_origen !== 'number' || typeof latitud_origen !== 'number') {
        return res.status(400).json({
          error: 'longitud_origen and latitud_origen must be valid numbers'
        });
      }

      // Validar que las coordenadas estén en el rango de Buenos Aires (aproximado)
      if (latitud_origen < -35.0 || latitud_origen > -34.0 || longitud_origen < -59.0 || longitud_origen > -58.0) {
        return res.status(400).json({
          error: 'Coordinates must be within Buenos Aires area'
        });
      }

      // Array para almacenar todas las actividades de todos los días
      const allDaysActivities = [];
      const usedPoiIds = new Set();
      const usedEventIds = new Set();
      let lastRequestId = null;

      try {
        // Generar itinerario para cada día
        for (let dayIndex = 0; dayIndex < daysDiff; dayIndex++) {
          const currentDate = new Date(startDate);
          currentDate.setDate(currentDate.getDate() + dayIndex);
          const currentDateStr = currentDate.toISOString().split('T')[0];

          console.log(`📅 Processing Day ${dayIndex + 1}/${daysDiff} - ${currentDateStr}`);

          // Construir los datos de la solicitud para este día específico
          const excludedPoiArray = Array.from(usedPoiIds);
          const excludedEventArray = Array.from(usedEventIds);
          
          console.log(`🚫 Day ${dayIndex + 1} - Excluding ${excludedPoiArray.length} POIs: [${excludedPoiArray.join(', ')}]`);
          console.log(`🚫 Day ${dayIndex + 1} - Excluding ${excludedEventArray.length} events: [${excludedEventArray.join(', ')}]`);
          
          const requestData = {
            name: `${name} - Day ${dayIndex + 1}`,
            fecha_visita: currentDateStr,
            hora_inicio,
            duracion_horas,
            longitud_origen,
            latitud_origen,
            zona_preferida: zona_preferida || null,
            // Enviar IDs de actividades ya usadas para evitar repetición
            excluded_poi_ids: excludedPoiArray,
            excluded_event_ids: excludedEventArray
          };

          // Enviar solicitud a través de Kafka y esperar respuesta
          const { requestId, response } = await kafkaService.sendItineraryRequestAndWait(userId, requestData, 45000);
          lastRequestId = requestId;

          // Procesar respuesta del día
          if (response.status === 'success') {
            const data = response.data || {};
            const actividades = data.actividades || [];
            
            // Agregar actividades del día al array
            allDaysActivities.push({
              dia: dayIndex + 1,
              fecha: currentDateStr,
              actividades: actividades,
              metadata: {
                processing_time_seconds: data.processing_metadata?.processing_time_seconds,
                timestamp: response.timestamp
              }
            });

            // Registrar POIs y eventos usados para evitar repetición en días siguientes
            actividades.forEach(actividad => {
              // Check item_type to distinguish between POI and event
              if (actividad.item_type === 'evento' && actividad.evento_id) {
                usedEventIds.add(actividad.evento_id);
                console.log(`  📌 Registering event ID: ${actividad.evento_id} - ${actividad.nombre}`);
              } else if (actividad.poi_id) {
                // Everything else is a POI (item_type='poi' or undefined)
                usedPoiIds.add(actividad.poi_id);
                console.log(`  📌 Registering POI ID: ${actividad.poi_id} - ${actividad.nombre}`);
              }
            });

            console.log(`✅ Day ${dayIndex + 1} processed: ${actividades.length} activities added`);
            console.log(`📊 Total used: ${usedPoiIds.size} POIs, ${usedEventIds.size} events`);

          } else if (response.status === 'error') {
            const error = response.error || {};
            
            // Si falla un día, devolver error indicando qué día falló
            return res.status(400).json({
              error: `Error generating itinerary for day ${dayIndex + 1}`,
              message: error.message || 'Unknown error occurred',
              suggestions: error.suggestions || [],
              request_id: requestId,
              failed_day: dayIndex + 1
            });

          } else {
            return res.status(500).json({
              error: `Unexpected response format from itinerary service for day ${dayIndex + 1}`,
              request_id: requestId,
              failed_day: dayIndex + 1
            });
          }
        } // end for loop

        // Todos los días procesados exitosamente
        // Flatten activities for single-day trips for backward compatibility
        const actividades = daysDiff === 1 ? allDaysActivities[0].actividades : [];
        
        res.status(200).json({
          message: 'Itinerary generated successfully',
          request_id: lastRequestId,
          total_days: daysDiff,
          itinerario_propuesto: {
            nombre: name,
            fecha_inicio: fecha_visita,
            fecha_fin: finalEndDate,
            hora_inicio: hora_inicio,
            duracion_horas: duracion_horas,
            ubicacion_origen: {
              latitud: latitud_origen,
              longitud: longitud_origen,
              direccion: ubicacion_direccion || null
            },
            zona_preferida: zona_preferida,
            // Para compatibilidad con itinerarios de 1 día
            actividades: actividades,
            // Nuevo: actividades organizadas por día
            dias: allDaysActivities,
            metadata: {
              total_activities: allDaysActivities.reduce((sum, day) => sum + day.actividades.length, 0),
              unique_pois: usedPoiIds.size,
              unique_events: usedEventIds.size
            }
          }
        });

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

  async confirmItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const {
        nombre,
        descripcion,
        fecha_visita,
        fecha_fin, // NEW: For multi-day itineraries
        hora_inicio,
        duracion_horas,
        ubicacion_origen,
        zona_preferida,
        actividades,
        modo_transporte_preferido
      } = req.body;

      // Validaciones básicas
      if (!nombre || !fecha_visita || !actividades || !Array.isArray(actividades)) {
        return res.status(400).json({
          error: 'Required fields: nombre, fecha_visita, actividades (array)'
        });
      }

      if (actividades.length === 0) {
        return res.status(400).json({
          error: 'At least one activity is required'
        });
      }

      try {
        // Comenzar transacción
        await db.query('BEGIN');

        // Determine end date (use fecha_fin if provided, otherwise same as fecha_visita)
        const finalEndDate = fecha_fin || fecha_visita;
        const totalDays = Math.ceil((new Date(finalEndDate) - new Date(fecha_visita)) / (1000 * 60 * 60 * 24)) + 1;
        
        console.log(`📅 Saving ${totalDays}-day itinerary from ${fecha_visita} to ${finalEndDate}`);

        // 1. Crear el itinerario principal
        const itineraryData = {
          nombre,
          descripcion: descripcion || (totalDays > 1 
            ? `${totalDays}-day itinerary starting ${fecha_visita}` 
            : `Itinerario generado para ${fecha_visita}`),
          fechaInicio: fecha_visita,
          fechaFin: finalEndDate, // Use calculated end date
          modoTransportePreferido: modo_transporte_preferido || 'mixed',
          ubicacionLatitud: ubicacion_origen?.latitud || null,
          ubicacionLongitud: ubicacion_origen?.longitud || null,
          ubicacionDireccion: ubicacion_origen?.direccion || zona_preferida || null, // Usar la dirección literal si está disponible
          tiempoEstimadoHoras: duracion_horas || null
        };

        const itinerary = await itineraryRepository.createItineraryWithLocation(userId, itineraryData);
        console.log(`✅ Itinerary created with ID: ${itinerary.id} (${totalDays} days)`);

        // 2. Agregar todas las actividades
        const actividadesCreadas = [];
        for (let i = 0; i < actividades.length; i++) {
          const actividad = actividades[i];
          
          // Determinar tipo de actividad y validar datos
          let tipoActividad, poiId, eventoId;
          if (actividad.poi_id) {
            tipoActividad = 'poi';
            poiId = actividad.poi_id;
            eventoId = null;
          } else if (actividad.evento_id) {
            tipoActividad = 'evento';
            poiId = null;
            eventoId = actividad.evento_id;
          } else {
            // Si no hay poi_id o evento_id, asumir que es un POI y buscar por nombre
            tipoActividad = 'poi';
            poiId = await itineraryRepository.findPOIByName(actividad.nombre);
            eventoId = null;
          }

          const activityData = {
            tipoActividad,
            poiId,
            eventoId,
            diaVisita: actividad.dia_visita || 1, // Use dia_visita from activity, default to 1
            ordenEnDia: actividad.orden_en_dia || (i + 1), // Use orden_en_dia from activity
            horaInicioPlanificada: actividad.hora_inicio_planificada || actividad.hora_inicio,
            horaFinPlanificada: actividad.hora_fin_planificada || actividad.hora_fin,
            tiempoEstimadoMinutos: actividad.tiempo_estimado_minutos,
            notasPlanificacion: actividad.descripcion || null
          };

          console.log(`  📌 Adding activity: ${actividad.nombre} (Day ${activityData.diaVisita}, Order ${activityData.ordenEnDia})`);

          const actividadCreada = await itineraryRepository.addActivityToItinerary(itinerary.id, activityData);
          actividadesCreadas.push({
            ...actividadCreada,
            actividad_original: actividad
          });
        }

        // Confirmar transacción
        await db.query('COMMIT');

        res.status(201).json({
          message: 'Itinerary confirmed and saved successfully',
          itinerario: {
            id: itinerary.id,
            nombre: itinerary.nombre,
            descripcion: itinerary.descripcion,
            fechaInicio: itinerary.fecha_inicio,
            fechaFin: itinerary.fecha_fin,
            estado: itinerary.estado,
            fechaCreacion: itinerary.fecha_creacion,
            actividades: actividadesCreadas.map(act => ({
              id: act.id,
              nombre: act.actividad_original.nombre,
              tipo: act.actividad_original.tipo,
              horaInicio: act.actividad_original.hora_inicio,
              horaFin: act.actividad_original.hora_fin,
              diaVisita: act.dia_visita,
              ordenEnDia: act.orden_en_dia
            }))
          }
        });

      } catch (dbError) {
        // Rollback en caso de error
        await db.query('ROLLBACK');
        throw dbError;
      }

    } catch (error) {
      console.error('Confirm itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while confirming itinerary',
        details: error.message
      });
    }
  }
}

module.exports = new ItineraryController();
