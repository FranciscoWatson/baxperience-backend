const chalk = require('chalk');

/**
 * Utility Logger for BAXperience API Gateway
 * Provides colorful, detailed console logging for demonstrations
 */
class Logger {
  constructor() {
    this.colors = {
      // Request/Response
      request: chalk.cyan,
      response: chalk.greenBright,
      error: chalk.red,
      warning: chalk.yellow,
      
      // Services
      kafka: chalk.magenta,
      database: chalk.blue,
      auth: chalk.yellowBright,
      
      // Status
      success: chalk.greenBright,
      info: chalk.blueBright,
      
      // Highlights
      bold: chalk.bold,
      dim: chalk.dim,
      
      // Values
      value: chalk.white,
      label: chalk.gray,
      highlight: chalk.cyanBright
    };
  }

  _timestamp() {
    const now = new Date();
    return chalk.gray(`[${now.toLocaleTimeString('es-AR', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    })}]`);
  }

  _formatObject(obj, indent = 2) {
    if (typeof obj === 'string') return obj;
    if (obj === null || obj === undefined) return 'null';
    
    try {
      return JSON.stringify(obj, null, indent);
    } catch (e) {
      return String(obj);
    }
  }

  // ==================== REQUEST LOGGING ====================
  
  logIncomingRequest(method, path, ip, userId = null) {
    // Simplified one-liner
    const userInfo = userId ? ` | User: ${userId}` : '';
    console.log(
      this._timestamp(),
      this.colors.request.bold(`${method} ${path}`) + userInfo
    );
  }

  logRequestBody(body) {
    // Removed - we don't show request body anymore
  }

  logResponse(statusCode, duration, method = '', url = '') {
    const statusColor = statusCode >= 500 ? this.colors.error :
                        statusCode >= 400 ? this.colors.warning :
                        statusCode >= 300 ? this.colors.info :
                        this.colors.success;
    
    const endpointInfo = method && url ? ` ${method} ${url} →` : '';
    
    console.log(
      this._timestamp(),
      statusColor.bold(`${endpointInfo} Devuelto ${statusCode}`) +
      this.colors.dim(` (${duration}ms)`)
    );
  }

  // ==================== KAFKA LOGGING ====================

  logKafkaRequest(topic, eventType, requestId, userId, data = {}) {
    // Simplified one-liner for emitting message
    console.log(
      this._timestamp(),
      this.colors.kafka.bold(`→ Emitido: ${topic}`) +
      this.colors.dim(` | ${eventType} | ID: ${requestId.substring(0, 20)}...`)
    );
  }

  logKafkaResponse(topic, requestId, status, data = {}) {
    const statusColor = status === 'success' ? this.colors.success : this.colors.error;
    const statusText = status === 'success' ? 'OK' : 'ERROR';
    
    // Simplified one-liner for receiving message
    console.log(
      this._timestamp(),
      statusColor.bold(`← Recibido: ${topic} [${statusText}]`) +
      this.colors.dim(` | ID: ${requestId.substring(0, 20)}...`)
    );
  }

  logKafkaWaiting(requestId, timeout) {
    // Removed - we don't show waiting message
  }

  // ==================== DATABASE LOGGING ====================

  logDatabaseQuery(operation, table, params = {}) {
    // Removed - we don't show individual queries
  }

  logDatabaseResult(rowCount) {
    // Removed - we don't show individual query results
  }

  // ==================== AUTHENTICATION LOGGING ====================

  logAuthAttempt(email, ip) {
    // Removed - we don't show auth attempts
  }

  logAuthSuccess(userId, email) {
    // Removed - success shown in response
  }

  logAuthFailure(reason) {
    // Removed - failure shown in response
  }

  // ==================== MICROSERVICE ROUTING ====================

  logMicroserviceRoute(service, endpoint, method = 'FORWARD') {
    // Removed - routing shown via Kafka messages
  }

  // ==================== ERROR LOGGING ====================

  logError(context, error) {
    console.log(
      this._timestamp(),
      this.colors.error.bold(`ERROR: ${context} - ${error.message}`)
    );
  }

  logWarning(context, message) {
    console.log(
      this._timestamp(),
      this.colors.warning.bold(`WARNING: ${context} - ${message}`)
    );
  }

  // ==================== SUCCESS LOGGING ====================

  logSuccess(context, message, details = {}) {
    // Removed - success shown in response
  }

  // ==================== INFO LOGGING ====================

  logInfo(context, message, details = {}) {
    // Removed - we only show essential info
  }

  // ==================== ITINERARY GENERATION ====================

  logItineraryGeneration(userId, days, startDate, endDate) {
    // Removed - we only show Kafka messages
  }

  logItineraryDay(dayNumber, totalDays, date, activitiesCount) {
    // Removed - we only show Kafka messages
  }

  logItineraryComplete(totalActivities, uniquePois, uniqueEvents) {
    // Removed - we only show response
  }

  // ==================== NLP LOGGING ====================

  logNLPQuery(userId, query) {
    // Removed - we only show Kafka messages
  }

  logNLPResult(entities, poisFound) {
    // Removed - we only show response
  }

  // ==================== STARTUP LOGGING ====================

  logStartup(port, environment) {
    console.log(
      this.colors.success.bold(`\nBAXPERIENCE API GATEWAY`) +
      this.colors.value(` - Port ${port} - ${environment}\n`)
    );
  }

  logServiceInitialization(serviceName, status, details = '') {
    const statusColor = status === 'success' ? this.colors.success : 
                        status === 'warning' ? this.colors.warning : 
                        this.colors.error;
    
    const statusText = status === 'success' ? 'OK' : status === 'warning' ? 'WARN' : 'ERROR';
    
    console.log(
      this._timestamp(),
      statusColor.bold(`${serviceName}: ${statusText}`)
    );
  }

  // ==================== HELPER METHODS ====================

  _extractRelevantFields(data) {
    const relevant = {};
    const fieldsToShow = [
      'name', 'fecha_visita', 'fecha_fin', 'hora_inicio', 'duracion_horas',
      'zona_preferida', 'query', 'excluded_poi_ids', 'excluded_event_ids'
    ];

    fieldsToShow.forEach(field => {
      if (data[field] !== undefined && data[field] !== null) {
        if (Array.isArray(data[field]) && data[field].length > 0) {
          relevant[field] = `[${data[field].length} items]`;
        } else if (typeof data[field] === 'object') {
          relevant[field] = JSON.stringify(data[field]);
        } else {
          relevant[field] = data[field];
        }
      }
    });

    return relevant;
  }
}

// Singleton instance
const logger = new Logger();

module.exports = logger;
