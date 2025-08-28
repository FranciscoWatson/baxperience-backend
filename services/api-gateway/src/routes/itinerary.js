const express = require('express');
const router = express.Router();
const itineraryController = require('../controllers/itineraryController');
const authMiddleware = require('../middleware/auth');

// All itinerary routes require authentication
router.use(authMiddleware);

// Itinerary CRUD operations
router.post('/', itineraryController.createItinerary);
router.get('/', itineraryController.getUserItineraries);
router.get('/:id', itineraryController.getItineraryById);
router.put('/:id', itineraryController.updateItinerary);
router.delete('/:id', itineraryController.deleteItinerary);

// Itinerary activities
router.post('/:itinerarioId/actividades', itineraryController.addActivityToItinerary);
router.get('/:itinerarioId/actividades', itineraryController.getItineraryActivities);

module.exports = router;
