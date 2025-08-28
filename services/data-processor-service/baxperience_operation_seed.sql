-- ================================================================
-- INSERTS DE DATOS (sin categorias, subcategorias, pois ni eventos)
-- ================================================================

BEGIN;

-- ========================
-- USUARIOS (12 registros)
-- ========================
INSERT INTO usuarios
(username, email, password_hash, nombre, apellido, fecha_nacimiento, genero, telefono, pais_origen, ciudad_origen, idioma_preferido, tipo_viajero, duracion_viaje_promedio, fecha_registro)
VALUES
('fwatson', 'francisco.watson@example.com', '$2b$12$9n8L1bX9x3d7xH3o6QfRZe0J5i2CqWm1f', 'Francisco', 'Watson', '1993-05-14', 'masculino', '+54 11 5555-1001', 'Argentina', 'Buenos Aires', 'es', 'foodie urbano', 3, NOW() - INTERVAL '90 days'),
('mrodriguez', 'maria.rodriguez@example.com', '$2b$12$ZkV7o3s2k1P9QwE7fT2aHe8uY', 'María', 'Rodríguez', '1988-09-22', 'femenino', '+54 11 5555-1002', 'Argentina', 'La Plata', 'es', 'cultural', 4, NOW() - INTERVAL '60 days'),
('jgarcia', 'juan.garcia@example.com', '$2b$12$A1b2C3d4E5f6G7h8I9j0kLmN', 'Juan', 'García', '1990-01-10', 'masculino', '+54 11 5555-1003', 'Argentina', 'Rosario', 'es', 'fotógrafo', 2, NOW() - INTERVAL '30 days'),
('lmartinez', 'lucia.martinez@example.com', '$2b$12$QwErTyUiOpAsDfGhJk', 'Lucía', 'Martínez', '1995-07-03', 'femenino', '+54 11 5555-1004', 'Argentina', 'Córdoba', 'es', 'aventurera', 5, NOW() - INTERVAL '20 days'),
('psilva', 'pedro.silva@example.com', '$2b$12$MnBvCxZlQaWeRtYp', 'Pedro', 'Silva', '1985-03-28', 'masculino', '+55 11 5555-1005', 'Brasil', 'São Paulo', 'pt', 'gastrónomo', 3, NOW() - INTERVAL '120 days'),
('agomez', 'ana.gomez@example.com', '$2b$12$ZxCvBnMqWeRtYuIo', 'Ana', 'Gómez', '1998-11-12', 'femenino', '+34 91 5555-1006', 'España', 'Madrid', 'es', 'low-cost', 6, NOW() - INTERVAL '45 days'),
('dlopez', 'diego.lopez@example.com', '$2b$12$PlMnOkIjUhYgTgRf', 'Diego', 'López', '2001-06-18', 'masculino', '+54 11 5555-1007', 'Argentina', 'Mar del Plata', 'es', 'nocturno', 2, NOW() - INTERVAL '10 days'),
('cfernandez', 'camila.fernandez@example.com', '$2b$12$XcVbNmAsSdFgHjKl', 'Camila', 'Fernández', '1992-02-05', 'femenino', '+54 11 5555-1008', 'Argentina', 'Mendoza', 'es', 'en pareja', 4, NOW() - INTERVAL '75 days'),
('tnguyen', 'thanh.nguyen@example.com', '$2b$12$R4t5y6u7i8o9p0a1', 'Thanh', 'Nguyen', '1994-04-09', 'otro', '+84 24 5555-1009', 'Vietnam', 'Hanoi', 'en', 'fotógrafo', 3, NOW() - INTERVAL '15 days'),
('sromero', 'sofia.romero@example.com', '$2b$12$HyGtFrDeSwQaZxCv', 'Sofía', 'Romero', '1996-12-01', 'femenino', '+54 11 5555-1010', 'Argentina', 'Bahía Blanca', 'es', 'cultural', 4, NOW() - INTERVAL '5 days'),
('rperalta', 'rodrigo.peralta@example.com', '$2b$12$LoKiJuNhBgVfCdXs', 'Rodrigo', 'Peralta', '1987-08-17', 'masculino', '+54 11 5555-1011', 'Argentina', 'Tandil', 'es', 'gastrónomo', 3, NOW() - INTERVAL '200 days'),
('ealvarez', 'eva.alvarez@example.com', '$2b$12$ZuMxNaBcDeFgHiJk', 'Eva', 'Álvarez', '1999-10-26', 'femenino', '+54 11 5555-1012', 'Argentina', 'Neuquén', 'es', 'solo traveler', 7, NOW() - INTERVAL '2 days');

-- =====================================
-- PREFERENCIAS_USUARIO (3–4 por usuario)
-- Categorías existentes: 1=Museos, 2=Gastronomía, 3=Monumentos,
-- 4=Lugares Históricos, 5=Entretenimiento, 6=Eventos
-- =====================================
INSERT INTO preferencias_usuario (usuario_id, categoria_id, le_gusta)
VALUES
(1,1,TRUE),(1,2,TRUE),(1,5,TRUE),
(2,1,TRUE),(2,4,TRUE),(2,5,TRUE),
(3,2,TRUE),(3,3,TRUE),(3,5,TRUE),
(4,1,TRUE),(4,2,TRUE),(4,6,TRUE),
(5,2,TRUE),(5,5,TRUE),(5,1,FALSE),
(6,1,TRUE),(6,4,TRUE),(6,2,TRUE),
(7,5,TRUE),(7,2,TRUE),(7,6,TRUE),
(8,1,TRUE),(8,3,TRUE),(8,4,TRUE),
(9,1,TRUE),(9,2,TRUE),(9,5,TRUE),
(10,1,TRUE),(10,5,TRUE),(10,6,TRUE),
(11,2,TRUE),(11,5,TRUE),(11,3,FALSE),
(12,1,TRUE),(12,4,TRUE),(12,2,TRUE),(12,6,TRUE);

-- =========================
-- ITINERARIOS (18 registros)
-- Fechas 2025, CABA aprox.
-- =========================
INSERT INTO itinerarios
(usuario_id, nombre, descripcion, fecha_inicio, fecha_fin, modo_transporte_preferido, estado,
 ubicacion_latitud, ubicacion_longitud, ubicacion_direccion,
 distancia_total_km, tiempo_estimado_horas, valoracion_itinerario, comentarios_itinerario, recomendaria, fecha_creacion)
VALUES
(1, 'Fin de semana cultural', 'Recorrido por museos y cafés notables', '2025-03-08', '2025-03-09', 'subte', 'completado',
 -34.603722, -58.381592, 'Microcentro, CABA', 11.40, 6.50, 4.50, 'Muy bien planificado', TRUE, NOW() - INTERVAL '170 days'),
(1, 'Sabores porteños', 'Parrillas y pizzerías clásicas', '2025-05-17', '2025-05-18', 'a pie', 'completado',
 -34.608300, -58.371200, 'San Nicolás, CABA', 7.80, 5.20, 4.20, 'Excelente comida', TRUE, NOW() - INTERVAL '100 days'),
(2, 'Historia en el casco histórico', 'Monumentos y lugares históricos', '2025-04-12', '2025-04-13', 'colectivo', 'completado',
 -34.615803, -58.373596, 'Monserrat, CABA', 9.10, 6.00, 4.60, 'Muy completo', TRUE, NOW() - INTERVAL '140 days'),
(2, 'Teatros & Centros culturales', 'Obras y actividades culturales', '2025-06-20', '2025-06-22', 'subte', 'completado',
 -34.603000, -58.400000, 'Balvanera, CABA', 12.70, 8.30, 4.80, 'Imperdible', TRUE, NOW() - INTERVAL '65 days'),
(3, 'Circuito fotográfico', 'Puntos con buenas vistas y arte público', '2025-02-15', '2025-02-16', 'bicicleta', 'completado',
 -34.603100, -58.377200, 'Puerto Madero, CABA', 15.30, 7.10, 4.10, 'Buenas locaciones', TRUE, NOW() - INTERVAL '190 days'),
(3, 'Noche porteña', 'Bares y música en vivo', '2025-07-11', '2025-07-12', 'a pie', 'planificado',
 -34.597000, -58.435000, 'Palermo, CABA', 6.20, 4.00, NULL, NULL, NULL, NOW() - INTERVAL '45 days'),
(4, 'Museos imperdibles', 'Selección curada de museos', '2025-03-29', '2025-03-30', 'subte', 'completado',
 -34.588900, -58.397400, 'Recoleta, CABA', 8.90, 5.60, 4.70, 'Exposiciones top', TRUE, NOW() - INTERVAL '155 days'),
(4, 'Agenda de eventos', 'Eventos destacados del mes', '2025-08-15', '2025-08-17', 'colectivo', 'en curso',
 -34.620000, -58.440000, 'Villa Crespo, CABA', 10.50, 7.00, NULL, NULL, NULL, NOW() - INTERVAL '12 days'),
(5, 'Giro gastronómico', 'Cortes y bodegones', '2025-05-01', '2025-05-02', 'taxi', 'completado',
 -34.641000, -58.364000, 'La Boca, CABA', 9.40, 5.10, 4.30, 'Volvería', TRUE, NOW() - INTERVAL '115 days'),
(6, 'Arte y memoria', 'Historia y sitios de memoria', '2025-04-26', '2025-04-27', 'subte', 'completado',
 -34.603700, -58.420000, 'Almagro, CABA', 7.60, 5.00, 4.60, 'Muy emotivo', TRUE, NOW() - INTERVAL '130 days'),
(6, 'Low-cost BA', 'Planes gratuitos/low-cost', '2025-06-07', '2025-06-08', 'a pie', 'completado',
 -34.621000, -58.381000, 'Constitución, CABA', 5.80, 4.20, 4.10, 'Rinde mucho', TRUE, NOW() - INTERVAL '80 days'),
(7, 'After office & shows', 'Bares con música y stand-up', '2025-07-18', '2025-07-19', 'colectivo', 'completado',
 -34.589000, -58.430000, 'Palermo Soho, CABA', 6.90, 4.40, 4.00, 'Buen ambiente', TRUE, NOW() - INTERVAL '38 days'),
(8, 'Paseo en Recoleta', 'Museos, plazas y cafés', '2025-03-22', '2025-03-23', 'a pie', 'completado',
 -34.588200, -58.396600, 'Recoleta, CABA', 4.70, 3.40, 4.80, 'Hermoso barrio', TRUE, NOW() - INTERVAL '160 days'),
(9, 'Clásicos BA', 'Imprescindibles en 48h', '2025-05-24', '2025-05-25', 'subte', 'completado',
 -34.603800, -58.381700, 'Microcentro, CABA', 10.20, 6.30, 4.50, 'Muy completo', TRUE, NOW() - INTERVAL '90 days'),
(10, 'Cartelera activa', 'Teatros y centros culturales', '2025-08-01', '2025-08-03', 'subte', 'completado',
 -34.603900, -58.420500, 'Abasto, CABA', 9.90, 7.10, 4.60, 'Excelentes obras', TRUE, NOW() - INTERVAL '26 days'),
(11, 'Ruta bodegonera', 'Bodegones y vermuterías', '2025-06-28', '2025-06-29', 'a pie', 'completado',
 -34.611000, -58.380000, 'San Telmo, CABA', 7.30, 4.80, 4.20, 'Atención 10 puntos', TRUE, NOW() - INTERVAL '55 days'),
(12, 'BA en solitario', 'Recorrido variado de 3 días', '2025-07-04', '2025-07-06', 'bicicleta', 'completado',
 -34.599000, -58.420000, 'Palermo, CABA', 13.40, 8.20, 4.70, 'Me encantó', TRUE, NOW() - INTERVAL '49 days'),
(12, 'Agenda de agosto', 'Sumando eventos y POIs', '2025-08-16', '2025-08-18', 'colectivo', 'en curso',
 -34.603000, -58.381000, 'Microcentro, CABA', 8.10, 6.10, NULL, NULL, NULL, NOW() - INTERVAL '11 days');

-- ======================================
-- ITINERARIO_ACTIVIDADES (~90 actividades)
-- Usamos poi_id (1–3528) y algunos evento_id (1–174).
-- tipo_actividad fuerza la validez de las columnas set.
-- ======================================
-- Itinerario 1 (usuario 1)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos, notas_planificacion)
VALUES
(1, 125, NULL, 'poi', 1, 1, '10:00', '11:30', 90, 'Museo de arte'),
(1, 820, NULL, 'poi', 1, 2, '12:00', '13:30', 90, 'Café notable'),
(1, NULL, 22, 'evento', 1, 3, '20:00', '22:00', 120, 'Show nocturno'),
(1, 2033, NULL, 'poi', 2, 1, '11:00', '12:30', 90, 'Plaza y monumento'),
(1, 3100, NULL, 'poi', 2, 2, '13:00', '14:30', 90, 'Almuerzo típico');

-- Itinerario 2 (usuario 1)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(2, 456, NULL, 'poi', 1, 1, '11:00', '12:15', 75),
(2, 1502, NULL, 'poi', 1, 2, '12:45', '14:00', 75),
(2, NULL, 87, 'evento', 1, 3, '21:00', '23:00', 120),
(2, 2780, NULL, 'poi', 2, 1, '10:30', '11:30', 60),
(2, 3321, NULL, 'poi', 2, 2, '12:00', '13:00', 60);

-- Itinerario 3 (usuario 2)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos, notas_planificacion)
VALUES
(3, 75, NULL, 'poi', 1, 1, '10:00', '11:30', 90, 'Casco histórico'),
(3, 980, NULL, 'poi', 1, 2, '12:00', '13:00', 60, 'Almuerzo ligero'),
(3, 201, NULL, 'poi', 1, 3, '15:00', '16:00', 60, 'Monumento icónico'),
(3, 1210, NULL, 'poi', 2, 1, '10:30', '11:45', 75, 'Museo'),
(3, NULL, 14, 'evento', 2, 2, '19:00', '21:00', 120, 'Obra de teatro');

-- Itinerario 4 (usuario 2)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(4, 167, NULL, 'poi', 1, 1, '18:00', '19:30', 90),
(4, NULL, 101, 'evento', 2, 1, '20:30', '22:30', 120),
(4, 2440, NULL, 'poi', 3, 1, '11:00', '12:30', 90);

-- Itinerario 5 (usuario 3)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(5, 333, NULL, 'poi', 1, 1, '10:00', '11:15', 75),
(5, 2045, NULL, 'poi', 1, 2, '11:45', '13:00', 75),
(5, 3050, NULL, 'poi', 1, 3, '15:00', '16:15', 75),
(5, NULL, 55, 'evento', 2, 1, '20:00', '22:00', 120);

-- Itinerario 6 (usuario 3)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(6, 2777, NULL, 'poi', 1, 1, '21:00', '23:00', 120),
(6, 1450, NULL, 'poi', 1, 2, '23:15', '23:59', 44);

-- Itinerario 7 (usuario 4)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(7, 112, NULL, 'poi', 1, 1, '10:00', '11:30', 90),
(7, 890, NULL, 'poi', 1, 2, '12:00', '13:00', 60),
(7, 1760, NULL, 'poi', 2, 1, '10:30', '11:30', 60),
(7, 2210, NULL, 'poi', 2, 2, '12:00', '13:00', 60);

-- Itinerario 8 (usuario 4)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(8, NULL, 133, 'evento', 1, 1, '19:00', '21:30', 150),
(8, 315, NULL, 'poi', 2, 1, '11:00', '12:00', 60),
(8, 1888, NULL, 'poi', 2, 2, '12:30', '13:30', 60);

-- Itinerario 9 (usuario 5)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(9, 510, NULL, 'poi', 1, 1, '13:00', '14:30', 90),
(9, 2510, NULL, 'poi', 1, 2, '15:00', '16:30', 90);

-- Itinerario 10 (usuario 6)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(10, 1222, NULL, 'poi', 1, 1, '10:00', '11:30', 90),
(10, 2900, NULL, 'poi', 1, 2, '12:00', '13:30', 90),
(10, 310, NULL, 'poi', 2, 1, '10:30', '11:30', 60);

-- Itinerario 11 (usuario 6)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(11, 140, NULL, 'poi', 1, 1, '10:00', '11:00', 60),
(11, 600, NULL, 'poi', 1, 2, '11:30', '12:30', 60);

-- Itinerario 12 (usuario 7)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(12, 1750, NULL, 'poi', 1, 1, '19:00', '20:30', 90),
(12, NULL, 68, 'evento', 1, 2, '21:00', '23:00', 120);

-- Itinerario 13 (usuario 8)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(13, 130, NULL, 'poi', 1, 1, '10:00', '11:00', 60),
(13, 540, NULL, 'poi', 1, 2, '11:30', '12:30', 60),
(13, 980, NULL, 'poi', 1, 3, '16:00', '17:00', 60);

-- Itinerario 14 (usuario 9)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(14, 220, NULL, 'poi', 1, 1, '10:00', '11:30', 90),
(14, 221, NULL, 'poi', 1, 2, '12:00', '13:00', 60),
(14, 222, NULL, 'poi', 2, 1, '10:30', '11:30', 60);

-- Itinerario 15 (usuario 10)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(15, NULL, 142, 'evento', 1, 1, '20:00', '22:30', 150),
(15, 1999, NULL, 'poi', 2, 1, '11:00', '12:00', 60);

-- Itinerario 16 (usuario 11)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(16, 3101, NULL, 'poi', 1, 1, '12:00', '13:30', 90),
(16, 2700, NULL, 'poi', 1, 2, '14:00', '15:30', 90);

-- Itinerario 17 (usuario 12)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(17, 3333, NULL, 'poi', 1, 1, '10:00', '11:30', 90),
(17, 200, NULL, 'poi', 1, 2, '12:00', '13:00', 60),
(17, 1456, NULL, 'poi', 2, 1, '10:30', '12:00', 90);

-- Itinerario 18 (usuario 12)
INSERT INTO itinerario_actividades
(itinerario_id, poi_id, evento_id, tipo_actividad, dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada, tiempo_estimado_minutos)
VALUES
(18, NULL, 12, 'evento', 1, 1, '18:30', '20:30', 120),
(18, 251, NULL, 'poi', 2, 1, '10:30', '11:30', 60),
(18, 145, NULL, 'poi', 2, 2, '12:00', '13:00', 60);

-- ============================
-- VALORACIONES (48 registros)
-- Puntuaciones 0–5 (con decimales), únicas por (usuario_id, poi_id)
-- ============================
INSERT INTO valoraciones
(usuario_id, poi_id, itinerario_id, puntuacion_general, puntuacion_ubicacion, puntuacion_servicio, puntuacion_ambiente, puntuacion_accesibilidad, comentario, fecha_creacion)
VALUES
(1,125,1,4.60,4.80,4.20,4.50,4.30,'Colección excelente', NOW() - INTERVAL '160 days'),
(1,820,1,4.20,4.30,4.10,4.40,4.00,'Café con historia', NOW() - INTERVAL '160 days'),
(1,2033,1,4.10,4.20,3.90,4.00,4.20,'Espacio agradable', NOW() - INTERVAL '159 days'),
(1,3100,1,4.30,4.10,4.20,4.20,4.10,'Muy buena comida', NOW() - INTERVAL '159 days'),

(2,75,3,4.70,4.80,4.50,4.60,4.40,'Casco histórico impecable', NOW() - INTERVAL '140 days'),
(2,980,3,4.10,4.20,4.00,4.10,4.00,'Almuerzo correcto', NOW() - INTERVAL '140 days'),
(2,201,3,4.50,4.60,4.20,4.30,4.40,'Monumento icónico', NOW() - INTERVAL '139 days'),
(2,1210,3,4.60,4.70,4.40,4.50,4.30,'Museo muy completo', NOW() - INTERVAL '139 days'),

(3,333,5,4.00,4.10,3.90,4.00,4.00,'Buena muestra', NOW() - INTERVAL '185 days'),
(3,2045,5,4.20,4.10,4.20,4.10,4.00,'Atención amable', NOW() - INTERVAL '185 days'),
(3,3050,5,4.30,4.30,4.20,4.20,4.10,'Recomendable', NOW() - INTERVAL '185 days'),
(3,2777,6,3.90,4.00,3.80,4.10,3.80,'Bar con buena música', NOW() - INTERVAL '40 days'),

(4,112,7,4.80,4.90,4.60,4.70,4.60,'Exhibición top', NOW() - INTERVAL '150 days'),
(4,890,7,4.10,4.20,4.10,4.00,4.00,'Café correcto', NOW() - INTERVAL '150 days'),
(4,1760,7,4.40,4.50,4.30,4.30,4.20,'Muy interesante', NOW() - INTERVAL '149 days'),
(4,2210,7,4.00,4.10,3.90,4.00,3.90,'Buen paseo', NOW() - INTERVAL '149 days'),

(5,510,9,4.30,4.40,4.20,4.10,4.00,'Bodegón clásico', NOW() - INTERVAL '110 days'),
(5,2510,9,4.40,4.30,4.40,4.20,4.10,'Parrilla recomendada', NOW() - INTERVAL '110 days'),

(6,1222,10,4.60,4.80,4.40,4.50,4.30,'Sitio de memoria', NOW() - INTERVAL '125 days'),
(6,2900,10,4.10,4.20,4.00,4.10,4.00,'Interesante muestra', NOW() - INTERVAL '125 days'),
(6,310,10,4.00,4.10,4.00,4.00,4.00,'Pequeño pero lindo', NOW() - INTERVAL '124 days'),
(6,140,11,4.20,4.30,4.10,4.10,4.00,'Recomendable', NOW() - INTERVAL '79 days'),

(7,1750,12,4.00,4.10,4.00,4.20,4.00,'Buen ambiente', NOW() - INTERVAL '35 days'),

(8,130,13,4.70,4.80,4.60,4.70,4.50,'Imperdible', NOW() - INTERVAL '158 days'),
(8,540,13,4.20,4.30,4.10,4.20,4.10,'Café tranquilo', NOW() - INTERVAL '158 days'),
(8,980,13,4.30,4.40,4.20,4.20,4.10,'Paseo completo', NOW() - INTERVAL '158 days'),

(9,220,14,4.40,4.50,4.20,4.30,4.20,'Muy lindo', NOW() - INTERVAL '88 days'),
(9,221,14,4.10,4.20,4.00,4.00,4.00,'Ok', NOW() - INTERVAL '88 days'),
(9,222,14,4.00,4.10,4.00,4.00,3.90,'Bien', NOW() - INTERVAL '87 days'),

(10,1999,15,4.50,4.60,4.40,4.50,4.30,'Teatro y cena', NOW() - INTERVAL '24 days'),

(11,3101,16,4.10,4.20,4.00,4.10,4.00,'Sabroso', NOW() - INTERVAL '53 days'),
(11,2700,16,4.20,4.30,4.10,4.10,4.00,'Clásico porteño', NOW() - INTERVAL '53 days'),

(12,3333,17,4.70,4.80,4.60,4.70,4.60,'Top absoluto', NOW() - INTERVAL '47 days'),
(12,200,17,4.30,4.40,4.20,4.20,4.10,'Muy bueno', NOW() - INTERVAL '47 days'),
(12,1456,17,4.40,4.50,4.30,4.30,4.20,'Gran experiencia', NOW() - INTERVAL '46 days'),
(12,251,18,4.00,4.10,3.90,4.00,3.90,'Correcto', NOW() - INTERVAL '9 days'),
(12,145,18,4.10,4.20,4.00,4.00,4.00,'Lindo cierre', NOW() - INTERVAL '9 days');

COMMIT;
