const logger = require('../utils/logger');

module.exports = (req, res, next) => {
  // Capture start time
  const startTime = Date.now();
  
  // Get user ID if authenticated
  const userId = req.user?.userId || req.user?.id || null;
  
  // Capture method and URL for response logging
  const method = req.method;
  const url = req.originalUrl;
  
  // Flag to prevent duplicate logging
  let logged = false;
  
  // Log incoming request (one line)
  logger.logIncomingRequest(method, url, req.ip, userId);
  
  // Capture the original res.json to log responses
  const originalJson = res.json.bind(res);
  res.json = function(body) {
    // Log response only once
    if (!logged) {
      const duration = Date.now() - startTime;
      logger.logResponse(res.statusCode, duration, method, url);
      logged = true;
    }
    
    return originalJson(body);
  };
  
  // Handle cases where res.send is used instead of res.json
  const originalSend = res.send.bind(res);
  res.send = function(body) {
    // Log response only once
    if (!logged) {
      const duration = Date.now() - startTime;
      logger.logResponse(res.statusCode, duration, method, url);
      logged = true;
    }
    
    return originalSend(body);
  };
  
  next();
};
