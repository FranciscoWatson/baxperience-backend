const express = require('express');
const router = express.Router();
const valoracionesController = require('../controllers/valoracionesController');
const authMiddleware = require('../middleware/auth');

// Public endpoint (no auth required) for getting ratings by POI
router.get('/poi/:poiId', valoracionesController.getValoracionesByPoi);

// All other rating routes require authentication
router.use(authMiddleware);

// Rating operations
router.post('/', valoracionesController.createValoracion);
router.put('/:id', valoracionesController.updateValoracion);
router.get('/mis-valoraciones', valoracionesController.getUserValoraciones);

module.exports = router;
