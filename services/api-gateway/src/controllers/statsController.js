const db = require('../config/database');

class StatsController {
  /**
   * Get user statistics
   * GET /api/stats/user
   */
  async getUserStats(req, res) {
    try {
      const userId = req.user.userId;
      
      console.log(`📊 Fetching stats for user ${userId}`);

      // 1. Itinerarios completados
      const completedItinerariesResult = await db.query(
        `SELECT COUNT(*) as count 
         FROM itinerarios 
         WHERE usuario_id = $1 AND estado = 'completado'`,
        [userId]
      );
      const completedItineraries = parseInt(completedItinerariesResult.rows[0].count);

      // 2. Actividades realizadas (de itinerarios completados)
      const completedActivitiesResult = await db.query(
        `SELECT COUNT(DISTINCT ia.id) as count
         FROM itinerario_actividades ia
         INNER JOIN itinerarios i ON ia.itinerario_id = i.id
         WHERE i.usuario_id = $1 AND i.estado = 'completado'`,
        [userId]
      );
      const completedActivities = parseInt(completedActivitiesResult.rows[0].count);

      // 3. Días viajados (suma de días de todos los itinerarios completados)
      const traveledDaysResult = await db.query(
        `SELECT COALESCE(SUM(fecha_fin - fecha_inicio + 1), 0) as total_days
         FROM itinerarios
         WHERE usuario_id = $1 AND estado = 'completado'`,
        [userId]
      );
      const traveledDays = parseInt(traveledDaysResult.rows[0].total_days) || 0;

      const stats = {
        completedItineraries,
        completedActivities,
        traveledDays
      };

      console.log(`✅ User stats:`, stats);

      res.status(200).json({
        success: true,
        stats
      });
    } catch (error) {
      console.error('❌ Error fetching user stats:', error);
      res.status(500).json({
        success: false,
        message: 'Error fetching user statistics',
        error: error.message
      });
    }
  }
}

module.exports = new StatsController();
