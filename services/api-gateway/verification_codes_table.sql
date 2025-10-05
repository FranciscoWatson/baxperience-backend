-- Tabla para códigos de verificación (registro y recuperación de contraseña)
CREATE TABLE verification_codes (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('registration', 'password_reset')),
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    ip_address VARCHAR(45),
    
    -- Índices para mejorar el rendimiento
    INDEX idx_email_type (email, type),
    INDEX idx_code (code),
    INDEX idx_expires_at (expires_at)
);

-- Índice compuesto para búsquedas frecuentes
CREATE INDEX idx_email_code_type ON verification_codes(email, code, type, is_used);

-- Trigger para limpiar códigos expirados automáticamente (opcional)
-- Esto se puede ejecutar como un cron job también
DELIMITER $$
CREATE EVENT IF NOT EXISTS cleanup_expired_codes
ON SCHEDULE EVERY 1 HOUR
DO
BEGIN
    DELETE FROM verification_codes 
    WHERE expires_at < NOW() 
    AND is_used = FALSE;
END$$
DELIMITER ;
