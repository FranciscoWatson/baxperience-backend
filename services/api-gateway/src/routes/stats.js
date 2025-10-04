const express = require('express');
const router = express.Router();
const statsController = require('../controllers/statsController');
const authMiddleware = require('../middleware/auth');

// Get user statistics
router.get('/user', authMiddleware, statsController.getUserStats);

module.exports = router;
