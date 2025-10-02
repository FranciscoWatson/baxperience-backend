const bikesRepository = require('../repositories/bikesRepository');

class BikesController {
  /**
   * Obtiene las 3 estaciones de EcoBici más cercanas a una ubicación
   * GET /api/bikes/nearby?lat=-34.6037&lon=-58.3816
   */
  async getNearbyStations(req, res) {
    try {
      const { lat, lon, limit = 3 } = req.query;

      // Validar parámetros
      if (!lat || !lon) {
        return res.status(400).json({
          error: 'Se requieren los parámetros lat y lon'
        });
      }

      const latitude = parseFloat(lat);
      const longitude = parseFloat(lon);

      // Validar que sean números válidos
      if (isNaN(latitude) || isNaN(longitude)) {
        return res.status(400).json({
          error: 'Los parámetros lat y lon deben ser números válidos'
        });
      }

      // Validar rangos válidos para Buenos Aires
      if (latitude < -35 || latitude > -34 || longitude < -59 || longitude > -58) {
        return res.status(400).json({
          error: 'Las coordenadas están fuera del rango de Buenos Aires'
        });
      }

      const maxLimit = parseInt(limit) > 10 ? 10 : parseInt(limit);

      // Obtener estaciones desde el repository
      const stations = await bikesRepository.getNearbyStations(latitude, longitude, maxLimit);

      if (stations.length === 0) {
        return res.status(404).json({
          message: 'No se encontraron estaciones disponibles cerca de tu ubicación',
          estaciones: []
        });
      }

      // Formatear respuesta
      const estaciones = stations.map(station => ({
        stationId: station.station_id,
        nombre: station.name,
        ubicacion: {
          latitud: parseFloat(station.lat),
          longitud: parseFloat(station.lon),
          direccion: station.address,
          barrios: station.barrios || []
        },
        disponibilidad: {
          bicisDisponibles: station.bicis_disponibles,
          docksDisponibles: station.docks_disponibles,
          capacidadTotal: station.capacity
        },
        estado: {
          enServicio: station.status === 'IN_SERVICE',
          permitePrestamo: station.is_renting === 1,
          permiteDevolucion: station.is_returning === 1
        },
        distanciaKm: parseFloat(station.distancia_km.toFixed(2))
      }));

      res.status(200).json({
        ubicacionConsulta: {
          latitud: latitude,
          longitud: longitude
        },
        cantidadEncontrada: estaciones.length,
        estaciones
      });

    } catch (error) {
      console.error('Get nearby stations error:', error);
      res.status(500).json({
        error: 'Error interno al buscar estaciones cercanas'
      });
    }
  }

  /**
   * Obtiene todas las estaciones disponibles (con paginación)
   * GET /api/bikes/stations?pagina=1&limite=20
   */
  async getStations(req, res) {
    try {
      const { pagina = 1, limite = 20, conBicis = 'true' } = req.query;

      const offset = (parseInt(pagina) - 1) * parseInt(limite);
      const soloConBicis = conBicis === 'true';

      // Obtener estaciones desde el repository
      const [stations, total] = await Promise.all([
        bikesRepository.getStations(parseInt(limite), offset, soloConBicis),
        bikesRepository.countStations(soloConBicis)
      ]);

      const totalPaginas = Math.ceil(total / parseInt(limite));

      const estaciones = stations.map(station => ({
        stationId: station.station_id,
        nombre: station.name,
        ubicacion: {
          latitud: parseFloat(station.lat),
          longitud: parseFloat(station.lon),
          direccion: station.address,
          barrios: station.barrios || []
        },
        disponibilidad: {
          bicisDisponibles: station.bicis_disponibles,
          docksDisponibles: station.docks_disponibles,
          capacidadTotal: station.capacity
        },
        estado: {
          enServicio: station.status === 'IN_SERVICE',
          permitePrestamo: station.is_renting === 1,
          permiteDevolucion: station.is_returning === 1
        }
      }));

      res.status(200).json({
        estaciones,
        paginacion: {
          pagina: parseInt(pagina),
          limite: parseInt(limite),
          total,
          totalPaginas
        }
      });

    } catch (error) {
      console.error('Get stations error:', error);
      res.status(500).json({
        error: 'Error interno al obtener las estaciones'
      });
    }
  }

  /**
   * Obtiene estadísticas generales del sistema de EcoBici
   * GET /api/bikes/stats
   */
  async getStats(req, res) {
    try {
      // Obtener estadísticas y top barrios desde el repository
      const [stats, topBarriosData] = await Promise.all([
        bikesRepository.getStats(),
        bikesRepository.getTopBarrios(10)
      ]);

      const topBarrios = topBarriosData.map(b => ({
        barrio: b.barrio,
        cantidadEstaciones: parseInt(b.cantidad_estaciones),
        bicisDisponibles: parseInt(b.bicis_disponibles)
      }));

      res.status(200).json({
        estadisticas: {
          totalEstaciones: parseInt(stats.total_estaciones),
          estacionesConBicis: parseInt(stats.estaciones_con_bicis),
          totalBicisDisponibles: parseInt(stats.total_bicis_disponibles),
          totalDocksDisponibles: parseInt(stats.total_docks_disponibles),
          promedioBicisPorEstacion: parseFloat(parseFloat(stats.promedio_bicis_por_estacion).toFixed(1))
        },
        topBarrios
      });

    } catch (error) {
      console.error('Get stats error:', error);
      res.status(500).json({
        error: 'Error interno al obtener estadísticas'
      });
    }
  }
}

module.exports = new BikesController();

