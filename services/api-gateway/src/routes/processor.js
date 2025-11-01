const express = require('express');
const router = express.Router();
const logger = require('../utils/logger');
const kafkaService = require('../services/kafkaService');

/**
 * POST /api/processor/nearby-pois
 * Buscar POIs cercanos a una ubicación específica (vía eventos Kafka)
 * 
 * Body:
 * {
 *   "latitud_origen": number,
 *   "longitud_origen": number,
 *   "radio_km": number (opcional, default: 1),
 *   "limite": number (opcional, default: 10)
 * }
 */
router.post('/nearby-pois', async (req, res) => {
  try {
    const { latitud_origen, longitud_origen, radio_km, limite, categorias } = req.body;

    // Validar parámetros requeridos
    if (latitud_origen === undefined || longitud_origen === undefined) {
      return res.status(400).json({
        error: 'latitud_origen y longitud_origen son requeridos'
      });
    }

    logger.logInfo('Nearby POIs Request (Kafka)', {
      latitud_origen,
      longitud_origen,
      radio_km: radio_km || 1,
      limite: limite || 10,
      categorias: categorias || []
    });

    // Construir datos de la solicitud
    const requestData = {
      latitud_origen,
      longitud_origen,
      radio_km: radio_km || 1,
      limite: limite || 10
    };

    // Agregar categorías si se proporcionan
    if (categorias && Array.isArray(categorias) && categorias.length > 0) {
      requestData.categorias = categorias;
    }

    // Enviar solicitud a través de Kafka y esperar respuesta
    const { requestId, response } = await kafkaService.sendNearbyPoisRequestAndWait(requestData, 30000);

    if (response.status === 'success') {
      logger.logInfo('Nearby POIs Response', {
        requestId,
        total: response.data.total,
        radius: response.data.radio_km
      });

      res.status(200).json(response.data);
    } else {
      logger.logError('Error response from processor', { requestId, error: response.error });
      res.status(500).json({
        error: response.error || 'Error procesando solicitud',
        message: 'No se pudieron obtener los POIs cercanos',
        request_id: requestId
      });
    }

  } catch (error) {
    logger.logError('Error in nearby-pois endpoint', error);

    // Manejar timeout
    if (error.message.includes('Timeout')) {
      return res.status(504).json({
        error: 'Timeout',
        message: 'La solicitud tardó demasiado tiempo en procesarse'
      });
    }

    // Error genérico
    res.status(500).json({
      error: 'Error interno del servidor',
      message: process.env.NODE_ENV === 'production' 
        ? 'No se pudieron obtener los POIs cercanos' 
        : error.message
    });
  }
});

module.exports = router;
