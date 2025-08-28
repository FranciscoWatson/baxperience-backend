const express = require('express');
const router = express.Router();
const poisController = require('../controllers/poisController');

// Public routes for POIs (no authentication required for browsing)
router.get('/', poisController.getPois);
router.get('/categorias', poisController.getCategorias);
router.get('/subcategorias', poisController.getSubcategorias);
router.get('/:id', poisController.getPoiById);

module.exports = router;
