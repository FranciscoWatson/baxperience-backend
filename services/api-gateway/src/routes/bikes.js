const express = require('express');
const router = express.Router();
const bikesController = require('../controllers/bikesController');
// const auth = require('../middleware/auth'); // Descomenta si requiere autenticación

/**
 * @route   GET /api/bikes/nearby
 * @desc    Obtiene las estaciones más cercanas a una ubicación
 * @query   lat (required) - Latitud
 * @query   lon (required) - Longitud  
 * @query   limit (optional) - Número de estaciones a retornar (default: 3, max: 10)
 * @access  Public
 * @example GET /api/bikes/nearby?lat=-34.6037&lon=-58.3816&limit=3
 */
router.get('/nearby', bikesController.getNearbyStations);

/**
 * @route   GET /api/bikes/stations
 * @desc    Obtiene todas las estaciones con paginación
 * @query   pagina (optional) - Número de página (default: 1)
 * @query   limite (optional) - Elementos por página (default: 20)
 * @query   conBicis (optional) - Filtrar solo con bicis disponibles (default: 'true')
 * @access  Public
 * @example GET /api/bikes/stations?pagina=1&limite=20&conBicis=true
 */
router.get('/stations', bikesController.getStations);

/**
 * @route   GET /api/bikes/stats
 * @desc    Obtiene estadísticas generales del sistema EcoBici
 * @access  Public
 * @example GET /api/bikes/stats
 */
router.get('/stats', bikesController.getStats);

module.exports = router;


