const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const authMiddleware = require('../middleware/auth');
const upload = require('../middleware/upload');

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

// Public routes - Categories (needed for registration and profile setup)
router.get('/categories', authController.getCategories);

// Protected routes - Profile
router.get('/profile', authMiddleware, authController.getProfile);
router.post('/profile/setup', authMiddleware, authController.setupProfile);

// Protected routes - Profile Settings
router.get('/profile/info', authMiddleware, authController.getProfileInfo);
router.put('/profile/info', authMiddleware, authController.updateProfileInfo);

// Protected routes - Profile Image
router.post('/profile/image', authMiddleware, upload.single('image'), authController.uploadProfileImage);
router.delete('/profile/image', authMiddleware, authController.deleteProfileImage);

// Protected routes - User Preferences
router.get('/profile/preferences', authMiddleware, authController.getUserPreferences);
router.put('/profile/preferences', authMiddleware, authController.updateUserPreferences);

module.exports = router;
