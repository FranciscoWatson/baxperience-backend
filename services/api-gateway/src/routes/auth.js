const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const authMiddleware = require('../middleware/auth');

// Public routes - Registration flow with verification
router.post('/register/request-code', authController.requestRegistrationCode);
router.post('/register/verify-code', authController.verifyRegistrationCode);
router.post('/register', authController.register);

// Public routes - Login
router.post('/login', authController.login);

// Public routes - Password reset flow with verification
router.post('/password/forgot', authController.requestPasswordReset);
router.post('/password/verify-code', authController.verifyPasswordResetCode);
router.post('/password/reset', authController.resetPassword);

// Protected routes
router.get('/profile', authMiddleware, authController.getProfile);
router.post('/profile/setup', authMiddleware, authController.setupProfile);

module.exports = router;
