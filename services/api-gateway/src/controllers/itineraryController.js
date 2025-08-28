const db = require('../config/database');

class ItineraryController {
  async createItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { name, description, preferences } = req.body;

      // Validate input
      if (!name) {
        return res.status(400).json({
          error: 'Itinerary name is required'
        });
      }

      // Create itinerary
      const result = await db.query(
        `INSERT INTO itineraries (user_id, name, description, preferences, status, created_at, updated_at) 
         VALUES ($1, $2, $3, $4, 'pending', NOW(), NOW()) 
         RETURNING id, name, description, preferences, status, created_at`,
        [userId, name, description || null, JSON.stringify(preferences || {})]
      );

      const itinerary = result.rows[0];

      res.status(201).json({
        message: 'Itinerary created successfully',
        itinerary: {
          id: itinerary.id,
          name: itinerary.name,
          description: itinerary.description,
          preferences: JSON.parse(itinerary.preferences || '{}'),
          status: itinerary.status,
          createdAt: itinerary.created_at
        }
      });

    } catch (error) {
      console.error('Create itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while creating itinerary'
      });
    }
  }

  async getUserItineraries(req, res) {
    try {
      const userId = req.user.userId;
      const { page = 1, limit = 10 } = req.query;

      const offset = (page - 1) * limit;

      const result = await db.query(
        `SELECT id, name, description, preferences, status, created_at, updated_at 
         FROM itineraries 
         WHERE user_id = $1 
         ORDER BY created_at DESC 
         LIMIT $2 OFFSET $3`,
        [userId, limit, offset]
      );

      const countResult = await db.query(
        'SELECT COUNT(*) FROM itineraries WHERE user_id = $1',
        [userId]
      );

      const total = parseInt(countResult.rows[0].count);
      const totalPages = Math.ceil(total / limit);

      const itineraries = result.rows.map(itinerary => ({
        id: itinerary.id,
        name: itinerary.name,
        description: itinerary.description,
        preferences: JSON.parse(itinerary.preferences || '{}'),
        status: itinerary.status,
        createdAt: itinerary.created_at,
        updatedAt: itinerary.updated_at
      }));

      res.status(200).json({
        itineraries,
        pagination: {
          page: parseInt(page),
          limit: parseInt(limit),
          total,
          totalPages
        }
      });

    } catch (error) {
      console.error('Get user itineraries error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching itineraries'
      });
    }
  }

  async getItineraryById(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;

      const result = await db.query(
        `SELECT id, name, description, preferences, status, created_at, updated_at 
         FROM itineraries 
         WHERE id = $1 AND user_id = $2`,
        [id, userId]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      const itinerary = result.rows[0];

      res.status(200).json({
        itinerary: {
          id: itinerary.id,
          name: itinerary.name,
          description: itinerary.description,
          preferences: JSON.parse(itinerary.preferences || '{}'),
          status: itinerary.status,
          createdAt: itinerary.created_at,
          updatedAt: itinerary.updated_at
        }
      });

    } catch (error) {
      console.error('Get itinerary by ID error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching itinerary'
      });
    }
  }

  async updateItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;
      const { name, description, preferences } = req.body;

      // Check if itinerary exists and belongs to user
      const existingResult = await db.query(
        'SELECT id FROM itineraries WHERE id = $1 AND user_id = $2',
        [id, userId]
      );

      if (existingResult.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      // Update itinerary
      const result = await db.query(
        `UPDATE itineraries 
         SET name = COALESCE($1, name), 
             description = COALESCE($2, description), 
             preferences = COALESCE($3, preferences), 
             updated_at = NOW() 
         WHERE id = $4 AND user_id = $5 
         RETURNING id, name, description, preferences, status, created_at, updated_at`,
        [
          name || null,
          description || null,
          preferences ? JSON.stringify(preferences) : null,
          id,
          userId
        ]
      );

      const itinerary = result.rows[0];

      res.status(200).json({
        message: 'Itinerary updated successfully',
        itinerary: {
          id: itinerary.id,
          name: itinerary.name,
          description: itinerary.description,
          preferences: JSON.parse(itinerary.preferences || '{}'),
          status: itinerary.status,
          createdAt: itinerary.created_at,
          updatedAt: itinerary.updated_at
        }
      });

    } catch (error) {
      console.error('Update itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while updating itinerary'
      });
    }
  }

  async deleteItinerary(req, res) {
    try {
      const userId = req.user.userId;
      const { id } = req.params;

      const result = await db.query(
        'DELETE FROM itineraries WHERE id = $1 AND user_id = $2 RETURNING id',
        [id, userId]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'Itinerary not found'
        });
      }

      res.status(200).json({
        message: 'Itinerary deleted successfully'
      });

    } catch (error) {
      console.error('Delete itinerary error:', error);
      res.status(500).json({
        error: 'Internal server error while deleting itinerary'
      });
    }
  }
}

module.exports = new ItineraryController();
