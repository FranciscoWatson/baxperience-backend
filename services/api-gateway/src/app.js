const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const logger = require('./utils/logger');
const requestLogger = require('./middleware/requestLogger');
const authRoutes = require('./routes/auth');
const itineraryRoutes = require('./routes/itinerary');
const poisRoutes = require('./routes/pois');
const valoracionesRoutes = require('./routes/valoraciones');
const mapsRoutes = require('./routes/maps');
const bikesRoutes = require('./routes/bikes');
const statsRoutes = require('./routes/stats');
const nlpRoutes = require('./routes/nlp');
const emailService = require('./services/emailService');
const kafkaService = require('./services/kafkaService');

const app = express();
const PORT = process.env.PORT || 3000;

// Security middleware
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});
app.use(limiter);

// Body parsing middleware (must be before request logger to have access to body)
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Custom request logging middleware
app.use(requestLogger);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// API routes
app.use('/api/auth', authRoutes);
app.use('/api/itinerary', itineraryRoutes);
app.use('/api/pois', poisRoutes);
app.use('/api/valoraciones', valoracionesRoutes);
app.use('/api/maps', mapsRoutes);
app.use('/api/bikes', bikesRoutes);
app.use('/api/stats', statsRoutes);
app.use('/api/nlp', nlpRoutes);

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    path: req.originalUrl
  });
});

// Global error handler
app.use((err, req, res, next) => {
  logger.logError('Global Error Handler', err);
  res.status(500).json({
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal server error' 
      : err.message
  });
});

app.listen(PORT, async () => {
  logger.logStartup(PORT, process.env.NODE_ENV || 'development');
  
  // Verify email service
  try {
    await emailService.initialize();
    logger.logServiceInitialization('Email Service', 'success');
  } catch (error) {
    logger.logServiceInitialization('Email Service', 'warning');
  }
  
  // Connect to Kafka (already subscribes to itinerary-responses and nlp-responses)
  try {
    await kafkaService.connect();
    logger.logServiceInitialization('Kafka Service', 'success');
  } catch (error) {
    logger.logServiceInitialization('Kafka Service', 'error');
  }
});

module.exports = app;
