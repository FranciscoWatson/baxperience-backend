const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const authMiddleware = require('../middleware/auth');

// Public routes
router.post('/register', authController.register);
router.post('/login', authController.login);


// Protected routes
router.get('/profile', authMiddleware, authController.getProfile);
router.post('/profile/setup', authMiddleware, authController.setupProfile);

module.exports = router;
