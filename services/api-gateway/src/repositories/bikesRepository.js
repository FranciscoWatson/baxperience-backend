const ecobiciDb = require('../config/ecobiciDatabase');

class BikesRepository {
  /**
   * Obtiene las estaciones más cercanas a una ubicación usando fórmula de Haversine
   * @param {number} latitude - Latitud
   * @param {number} longitude - Longitud
   * @param {number} limit - Número máximo de estaciones a retornar
   * @returns {Promise<Array>} Lista de estaciones cercanas
   */
  async getNearbyStations(latitude, longitude, limit) {
    const query = `
      SELECT 
        s.station_id,
        s.name,
        s.lat,
        s.lon,
        s.address,
        s.capacity,
        s.groups as barrios,
        ss.num_bikes_mechanical as bicis_disponibles,
        ss.num_docks_available as docks_disponibles,
        ss.status,
        ss.is_renting,
        ss.is_returning,
        -- Fórmula de Haversine para calcular distancia en km
        (
          6371 * acos(
            cos(radians($1)) * 
            cos(radians(s.lat)) * 
            cos(radians(s.lon) - radians($2)) + 
            sin(radians($1)) * 
            sin(radians(s.lat))
          )
        ) as distancia_km
      FROM stations s
      INNER JOIN (
        -- Subconsulta para obtener el último estado de cada estación
        SELECT DISTINCT ON (station_id)
          station_id,
          num_bikes_mechanical,
          num_docks_available,
          status,
          is_renting,
          is_returning,
          recorded_at
        FROM station_status
        ORDER BY station_id, recorded_at DESC
      ) ss ON s.station_id = ss.station_id
      WHERE 
        ss.status = 'IN_SERVICE'
        AND ss.is_renting = 1
        AND ss.num_bikes_mechanical > 0
      ORDER BY distancia_km ASC
      LIMIT $3
    `;

    const result = await ecobiciDb.query(query, [latitude, longitude, limit]);
    return result.rows;
  }

  /**
   * Obtiene todas las estaciones con paginación
   * @param {number} limit - Elementos por página
   * @param {number} offset - Desplazamiento para paginación
   * @param {boolean} soloConBicis - Filtrar solo estaciones con bicis disponibles
   * @returns {Promise<Array>} Lista de estaciones
   */
  async getStations(limit, offset, soloConBicis = true) {
    let whereClause = "WHERE ss.status = 'IN_SERVICE' AND ss.is_renting = 1";
    if (soloConBicis) {
      whereClause += " AND ss.num_bikes_mechanical > 0";
    }

    const query = `
      SELECT 
        s.station_id,
        s.name,
        s.lat,
        s.lon,
        s.address,
        s.capacity,
        s.groups as barrios,
        ss.num_bikes_mechanical as bicis_disponibles,
        ss.num_docks_available as docks_disponibles,
        ss.status,
        ss.is_renting,
        ss.is_returning
      FROM stations s
      INNER JOIN (
        SELECT DISTINCT ON (station_id)
          station_id,
          num_bikes_mechanical,
          num_docks_available,
          status,
          is_renting,
          is_returning,
          recorded_at
        FROM station_status
        ORDER BY station_id, recorded_at DESC
      ) ss ON s.station_id = ss.station_id
      ${whereClause}
      ORDER BY s.name ASC
      LIMIT $1 OFFSET $2
    `;

    const result = await ecobiciDb.query(query, [limit, offset]);
    return result.rows;
  }

  /**
   * Cuenta el total de estaciones según filtros
   * @param {boolean} soloConBicis - Filtrar solo estaciones con bicis disponibles
   * @returns {Promise<number>} Total de estaciones
   */
  async countStations(soloConBicis = true) {
    let whereClause = "WHERE ss.status = 'IN_SERVICE' AND ss.is_renting = 1";
    if (soloConBicis) {
      whereClause += " AND ss.num_bikes_mechanical > 0";
    }

    const query = `
      SELECT COUNT(*) as total
      FROM stations s
      INNER JOIN (
        SELECT DISTINCT ON (station_id)
          station_id,
          num_bikes_mechanical,
          status,
          is_renting
        FROM station_status
        ORDER BY station_id, recorded_at DESC
      ) ss ON s.station_id = ss.station_id
      ${whereClause}
    `;

    const result = await ecobiciDb.query(query);
    return parseInt(result.rows[0].total);
  }

  /**
   * Obtiene estadísticas generales del sistema EcoBici
   * @returns {Promise<Object>} Objeto con estadísticas
   */
  async getStats() {
    const query = `
      SELECT 
        COUNT(DISTINCT s.station_id) as total_estaciones,
        SUM(CASE WHEN ss.num_bikes_mechanical > 0 THEN 1 ELSE 0 END) as estaciones_con_bicis,
        SUM(ss.num_bikes_mechanical) as total_bicis_disponibles,
        SUM(ss.num_docks_available) as total_docks_disponibles,
        AVG(ss.num_bikes_mechanical) as promedio_bicis_por_estacion
      FROM stations s
      INNER JOIN (
        SELECT DISTINCT ON (station_id)
          station_id,
          num_bikes_mechanical,
          num_docks_available,
          status,
          is_renting
        FROM station_status
        ORDER BY station_id, recorded_at DESC
      ) ss ON s.station_id = ss.station_id
      WHERE ss.status = 'IN_SERVICE' AND ss.is_renting = 1
    `;

    const result = await ecobiciDb.query(query);
    return result.rows[0];
  }

  /**
   * Obtiene los top barrios con más estaciones
   * @param {number} limit - Número de barrios a retornar
   * @returns {Promise<Array>} Lista de barrios con estadísticas
   */
  async getTopBarrios(limit = 10) {
    const query = `
      SELECT 
        unnest(s.groups) as barrio,
        COUNT(*) as cantidad_estaciones,
        SUM(ss.num_bikes_mechanical) as bicis_disponibles
      FROM stations s
      INNER JOIN (
        SELECT DISTINCT ON (station_id)
          station_id,
          num_bikes_mechanical,
          status,
          is_renting
        FROM station_status
        ORDER BY station_id, recorded_at DESC
      ) ss ON s.station_id = ss.station_id
      WHERE ss.status = 'IN_SERVICE' 
        AND ss.is_renting = 1
        AND s.groups IS NOT NULL
      GROUP BY barrio
      ORDER BY cantidad_estaciones DESC
      LIMIT $1
    `;

    const result = await ecobiciDb.query(query, [limit]);
    return result.rows;
  }
}

module.exports = new BikesRepository();


