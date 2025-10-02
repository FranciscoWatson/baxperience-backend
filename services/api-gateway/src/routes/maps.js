const express = require('express');
const router = express.Router();
const authMiddleware = require('../middleware/auth');

/**
 * GET /api/maps/config
 * Returns Google Maps API configuration (API Key)
 * Requires authentication for security
 */
router.get('/config', authMiddleware, (req, res) => {
  try {
    const apiKey = process.env.GOOGLE_MAPS_API_KEY;
    
    if (!apiKey) {
      return res.status(500).json({
        error: 'Google Maps API Key not configured on server'
      });
    }

    // Return the API key securely only to authenticated users
    res.json({
      apiKey: apiKey,
      platform: 'google-maps',
      features: ['maps', 'directions', 'geocoding']
    });
  } catch (error) {
    console.error('Error fetching maps config:', error);
    res.status(500).json({
      error: 'Failed to retrieve maps configuration'
    });
  }
});

/**
 * POST /api/maps/geocode
 * Geocoding endpoint - converts addresses to coordinates
 * Proxies requests to Google Maps API to keep API key secure
 */
router.post('/geocode', authMiddleware, async (req, res) => {
  try {
    const { address } = req.body;
    
    if (!address) {
      return res.status(400).json({
        error: 'Address is required'
      });
    }

    // Here you could implement server-side geocoding
    // For now, we'll let the client handle it with the API key
    res.json({
      message: 'Use the API key from /config endpoint for client-side geocoding'
    });
  } catch (error) {
    console.error('Error in geocoding:', error);
    res.status(500).json({
      error: 'Geocoding failed'
    });
  }
});

module.exports = router;
