const db = require('../config/database');

class PoisController {
  async getPois(req, res) {
    try {
      const { 
        categoriaId, 
        subcategoriaId, 
        barrio, 
        latitud, 
        longitud, 
        radio = 5, 
        pagina = 1, 
        limite = 20,
        ordenPor = 'valoracion_promedio'
      } = req.query;

      const offset = (pagina - 1) * limite;
      let whereConditions = [];
      let params = [];
      let paramIndex = 1;

      // Filtros
      if (categoriaId) {
        whereConditions.push(`p.categoria_id = $${paramIndex++}`);
        params.push(categoriaId);
      }

      if (subcategoriaId) {
        whereConditions.push(`p.subcategoria_id = $${paramIndex++}`);
        params.push(subcategoriaId);
      }

      if (barrio) {
        whereConditions.push(`p.barrio ILIKE $${paramIndex++}`);
        params.push(`%${barrio}%`);
      }

      // Filtro geográfico
      if (latitud && longitud) {
        whereConditions.push(`
          calcular_distancia_km(p.latitud, p.longitud, $${paramIndex++}, $${paramIndex++}) <= $${paramIndex++}
        `);
        params.push(latitud, longitud, radio);
      }

      const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';

      // Validar orden
      const validOrderBy = ['valoracion_promedio', 'numero_valoraciones', 'nombre', 'fecha_creacion'];
      const orderBy = validOrderBy.includes(ordenPor) ? ordenPor : 'valoracion_promedio';

      const query = `
        SELECT 
          p.id, p.nombre, p.descripcion, 
          p.latitud, p.longitud, p.direccion, p.barrio,
          p.valoracion_promedio, p.numero_valoraciones,
          p.telefono, p.email, p.web, p.horario,
          p.tipo_cocina, p.tipo_ambiente,
          c.nombre as categoria_nombre,
          s.nombre as subcategoria_nombre
        FROM pois p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
        ${whereClause}
        ORDER BY p.${orderBy} DESC, p.nombre ASC
        LIMIT $${paramIndex++} OFFSET $${paramIndex++}
      `;

      params.push(limite, offset);

      const result = await db.query(query, params);

      // Contar total
      const countQuery = `
        SELECT COUNT(*) 
        FROM pois p
        ${whereClause}
      `;
      const countParams = params.slice(0, -2); // Remove limit and offset
      const countResult = await db.query(countQuery, countParams);

      const total = parseInt(countResult.rows[0].count);
      const totalPaginas = Math.ceil(total / limite);

      const pois = result.rows.map(poi => ({
        id: poi.id,
        nombre: poi.nombre,
        descripcion: poi.descripcion,
        latitud: parseFloat(poi.latitud),
        longitud: parseFloat(poi.longitud),
        direccion: poi.direccion,
        barrio: poi.barrio,
        valoracionPromedio: parseFloat(poi.valoracion_promedio || 0),
        numeroValoraciones: poi.numero_valoraciones || 0,
        telefono: poi.telefono,
        email: poi.email,
        web: poi.web,
        horario: poi.horario,
        tipoCocina: poi.tipo_cocina,
        tipoAmbiente: poi.tipo_ambiente,
        categoria: {
          nombre: poi.categoria_nombre
        },
        subcategoria: {
          nombre: poi.subcategoria_nombre
        }
      }));

      res.status(200).json({
        pois,
        paginacion: {
          pagina: parseInt(pagina),
          limite: parseInt(limite),
          total,
          totalPaginas
        }
      });

    } catch (error) {
      console.error('Get POIs error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching POIs'
      });
    }
  }

  async getPoiById(req, res) {
    try {
      const { id } = req.params;

      const result = await db.query(`
        SELECT 
          p.*, 
          c.nombre as categoria_nombre, c.descripcion as categoria_descripcion,
          s.nombre as subcategoria_nombre, s.descripcion as subcategoria_descripcion
        FROM pois p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
        WHERE p.id = $1
      `, [id]);

      if (result.rows.length === 0) {
        return res.status(404).json({
          error: 'POI not found'
        });
      }

      const poi = result.rows[0];

      res.status(200).json({
        poi: {
          id: poi.id,
          nombre: poi.nombre,
          descripcion: poi.descripcion,
          latitud: parseFloat(poi.latitud),
          longitud: parseFloat(poi.longitud),
          direccion: poi.direccion,
          calle: poi.calle,
          altura: poi.altura,
          barrio: poi.barrio,
          comuna: poi.comuna,
          telefono: poi.telefono,
          codigoArea: poi.codigo_area,
          email: poi.email,
          web: poi.web,
          tipoCocina: poi.tipo_cocina,
          tipoAmbiente: poi.tipo_ambiente,
          horario: poi.horario,
          material: poi.material,
          autor: poi.autor,
          denominacionSimboliza: poi.denominacion_simboliza,
          valoracionPromedio: parseFloat(poi.valoracion_promedio || 0),
          numeroValoraciones: poi.numero_valoraciones || 0,
          categoria: {
            id: poi.categoria_id,
            nombre: poi.categoria_nombre,
            descripcion: poi.categoria_descripcion
          },
          subcategoria: poi.subcategoria_id ? {
            id: poi.subcategoria_id,
            nombre: poi.subcategoria_nombre,
            descripcion: poi.subcategoria_descripcion
          } : null,
          fechaCreacion: poi.fecha_creacion,
          fechaActualizacion: poi.fecha_actualizacion
        }
      });

    } catch (error) {
      console.error('Get POI by ID error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching POI'
      });
    }
  }

  async getCategorias(req, res) {
    try {
      const result = await db.query(`
        SELECT 
          c.id, c.nombre, c.descripcion,
          COUNT(p.id) as total_pois
        FROM categorias c
        LEFT JOIN pois p ON c.id = p.categoria_id
        GROUP BY c.id, c.nombre, c.descripcion
        ORDER BY c.nombre
      `);

      const categorias = result.rows.map(categoria => ({
        id: categoria.id,
        nombre: categoria.nombre,
        descripcion: categoria.descripcion,
        totalPois: parseInt(categoria.total_pois || 0)
      }));

      res.status(200).json({
        categorias
      });

    } catch (error) {
      console.error('Get categories error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching categories'
      });
    }
  }

  async getSubcategorias(req, res) {
    try {
      const { categoriaId } = req.query;

      let query = `
        SELECT 
          s.id, s.nombre, s.descripcion, s.categoria_id,
          c.nombre as categoria_nombre,
          COUNT(p.id) as total_pois
        FROM subcategorias s
        LEFT JOIN categorias c ON s.categoria_id = c.id
        LEFT JOIN pois p ON s.id = p.subcategoria_id
      `;

      let params = [];
      if (categoriaId) {
        query += ' WHERE s.categoria_id = $1';
        params.push(categoriaId);
      }

      query += `
        GROUP BY s.id, s.nombre, s.descripcion, s.categoria_id, c.nombre
        ORDER BY c.nombre, s.nombre
      `;

      const result = await db.query(query, params);

      const subcategorias = result.rows.map(subcategoria => ({
        id: subcategoria.id,
        nombre: subcategoria.nombre,
        descripcion: subcategoria.descripcion,
        categoriaId: subcategoria.categoria_id,
        categoriaNombre: subcategoria.categoria_nombre,
        totalPois: parseInt(subcategoria.total_pois || 0)
      }));

      res.status(200).json({
        subcategorias
      });

    } catch (error) {
      console.error('Get subcategories error:', error);
      res.status(500).json({
        error: 'Internal server error while fetching subcategories'
      });
    }
  }
}

module.exports = new PoisController();
