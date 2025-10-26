const express = require('express');
const router = express.Router();
const authMiddleware = require('../middleware/auth');
const kafkaService = require('../services/kafkaService');
const logger = require('../utils/logger');

/**
 * Process natural language query
 * POST /api/nlp/process
 */
router.post('/process', authMiddleware, async (req, res) => {
  try {
    const { query } = req.body;
    const userId = req.user.id;

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return res.status(400).json({
        error: 'Query is required and must be a non-empty string'
      });
    }

    try {
      // Enviar solicitud a Kafka y esperar respuesta
      // (el topic nlp-responses ya está suscrito al iniciar el servicio)
      const { requestId, response } = await kafkaService.sendAndWaitForResponse(
        'nlp-requests',
        'nlp_query',
        userId,
        { query: query.trim() },
        10000, // 10 segundos timeout
        'nlp'
      );

      // Verificar si fue exitoso
      if (response.status === 'success') {
        const nlpResult = response.data;
        
        // Buscar POIs basados en los resultados del NLP
        let pois = [];
        try {
          const db = require('../config/database');
          let whereConditions = [];
          let params = [];
          let paramIndex = 1;

          // Filtrar por categoría si fue detectada
          if (nlpResult.entities?.category?.id) {
            whereConditions.push(`p.categoria_id = $${paramIndex++}`);
            params.push(nlpResult.entities.category.id);
          }

          // Filtrar por subcategoría si fue detectada
          if (nlpResult.entities?.subcategory?.id) {
            whereConditions.push(`p.subcategoria_id = $${paramIndex++}`);
            params.push(nlpResult.entities.subcategory.id);
          }

          // Filtrar por barrio si fue detectado
          if (nlpResult.entities?.zone?.name) {
            whereConditions.push(`p.barrio ILIKE $${paramIndex++}`);
            params.push(`%${nlpResult.entities.zone.name}%`);
          }

          const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';

          if (whereClause) {
            const poisQuery = `
              SELECT 
                p.id, p.nombre, p.descripcion, 
                p.latitud, p.longitud, p.direccion, p.barrio,
                p.valoracion_promedio, p.numero_valoraciones,
                p.telefono, p.email, p.web, p.horario,
                p.tipo_cocina, p.tipo_ambiente,
                c.nombre as categoria_nombre,
                s.nombre as subcategoria_nombre
              FROM pois p
              LEFT JOIN categorias c ON p.categoria_id = c.id
              LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
              ${whereClause}
              ORDER BY p.valoracion_promedio DESC, p.nombre ASC
              LIMIT 10
            `;

            const poisResult = await db.query(poisQuery, params);
            
            pois = poisResult.rows.map(poi => ({
              id: poi.id,
              nombre: poi.nombre,
              descripcion: poi.descripcion,
              latitud: parseFloat(poi.latitud),
              longitud: parseFloat(poi.longitud),
              direccion: poi.direccion,
              barrio: poi.barrio,
              valoracionPromedio: parseFloat(poi.valoracion_promedio || 0),
              numeroValoraciones: poi.numero_valoraciones || 0,
              telefono: poi.telefono,
              email: poi.email,
              web: poi.web,
              horario: poi.horario,
              tipoCocina: poi.tipo_cocina,
              tipoAmbiente: poi.tipo_ambiente,
              categoria: {
                nombre: poi.categoria_nombre
              },
              subcategoria: {
                nombre: poi.subcategoria_nombre
              }
            }));

          }
        } catch (dbError) {
          logger.logError('NLP - POI Fetch', dbError);
          // No fallar la request, solo devolver sin POIs
        }

        res.json({
          success: true,
          nlp_result: nlpResult,
          pois: pois,
          total_results: pois.length,
          timestamp: new Date().toISOString()
        });
      } else {
        res.status(500).json({
          error: 'NLP processing failed',
          message: response.error?.message || 'Unknown error'
        });
      }

    } catch (kafkaError) {
      logger.logError('NLP - Kafka', kafkaError);
      
      if (kafkaError.message.includes('Timeout')) {
        return res.status(504).json({
          error: 'NLP service timeout',
          message: 'The request took too long to process'
        });
      }
      
      return res.status(503).json({
        error: 'NLP service temporarily unavailable',
        message: 'Please try again in a moment'
      });
    }

  } catch (error) {
    logger.logError('NLP Process', error);
    
    res.status(500).json({
      error: 'Failed to process query',
      message: error.message
    });
  }
});

/**
 * Get available categories
 * GET /api/nlp/categories
 */
router.get('/categories', authMiddleware, async (req, res) => {
  try {
    const db = require('../config/database');
    const result = await db.query('SELECT id, nombre FROM categorias ORDER BY nombre');
    
    res.json({
      categories: result.rows.map(row => ({
        id: row.id,
        name: row.nombre
      }))
    });
  } catch (error) {
    logger.logError('NLP - Get Categories', error);
    res.status(500).json({
      error: 'Failed to fetch categories'
    });
  }
});

/**
 * Get available barrios
 * GET /api/nlp/barrios
 */
router.get('/barrios', authMiddleware, async (req, res) => {
  try {
    const db = require('../config/database');
    const result = await db.query('SELECT DISTINCT barrio FROM pois WHERE barrio IS NOT NULL ORDER BY barrio');
    
    res.json({
      barrios: result.rows.map(row => row.barrio)
    });
  } catch (error) {
    logger.logError('NLP - Get Barrios', error);
    res.status(500).json({
      error: 'Failed to fetch barrios'
    });
  }
});

/**
 * Health check for NLP service
 * GET /api/nlp/health
 */
router.get('/health', async (req, res) => {
  try {
    // Check if NLP service is running by checking Kafka connection
    const isKafkaConnected = kafkaService.producer !== null;
    
    res.json({
      status: isKafkaConnected ? 'connected' : 'disconnected',
      kafka_connected: isKafkaConnected,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(503).json({
      status: 'disconnected',
      error: error.message
    });
  }
});

module.exports = router;

