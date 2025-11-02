// Setup file for Jest tests
// Configure environment variables for testing

process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-key-for-testing-only';
process.env.JWT_EXPIRES_IN = '24h';
process.env.VERIFICATION_CODE_EXPIRY_MINUTES = '15';
process.env.RATE_LIMIT_WINDOW_MS = '900000';
process.env.RATE_LIMIT_MAX_REQUESTS = '100';
process.env.CORS_ORIGIN = 'http://localhost:3000';

// Email configuration
process.env.EMAIL_HOST = 'smtp.test.com';
process.env.EMAIL_PORT = '587';
process.env.EMAIL_SECURE = 'false';
process.env.EMAIL_USER = 'test@baxperience.com';
process.env.EMAIL_PASSWORD = 'test-password';
process.env.EMAIL_FROM_NAME = 'BAXperience Test';
process.env.EMAIL_FROM_ADDRESS = 'test@baxperience.com';

// Kafka configuration
process.env.KAFKA_BROKER = 'localhost:9092';

// Cloudinary configuration (mock)
process.env.CLOUDINARY_CLOUD_NAME = 'test-cloud';
process.env.CLOUDINARY_API_KEY = 'test-api-key';
process.env.CLOUDINARY_API_SECRET = 'test-api-secret';

// Suppress console output during tests (optional)
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};
