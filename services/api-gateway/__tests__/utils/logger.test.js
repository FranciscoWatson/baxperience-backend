const logger = require('../../src/utils/logger');

// Don't mock chalk to test actual output
describe('Logger', () => {
  let consoleLogSpy;

  beforeEach(() => {
    // Spy on console.log to capture output
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
  });

  describe('logIncomingRequest', () => {
    it('should log incoming request with method and path', () => {
      logger.logIncomingRequest('GET', '/api/users', '127.0.0.1');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('GET');
      expect(output).toContain('/api/users');
    });

    it('should include user ID if provided', () => {
      logger.logIncomingRequest('POST', '/api/data', '127.0.0.1', 123);

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('User: 123');
    });

    it('should not include user info if not provided', () => {
      logger.logIncomingRequest('GET', '/api/public', '127.0.0.1');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).not.toContain('User:');
    });

    it('should handle different HTTP methods', () => {
      const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];
      
      methods.forEach(method => {
        consoleLogSpy.mockClear();
        logger.logIncomingRequest(method, '/api/test', '127.0.0.1');
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toContain(method);
      });
    });
  });

  describe('logResponse', () => {
    it('should log successful response (200)', () => {
      logger.logResponse(200, 150, 'GET', '/api/users');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('200');
      expect(output).toContain('150ms');
    });

    it('should log error response (500)', () => {
      logger.logResponse(500, 200, 'POST', '/api/data');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('500');
    });

    it('should handle different status code ranges', () => {
      const statusCodes = [200, 201, 301, 400, 401, 404, 500, 503];
      
      statusCodes.forEach(code => {
        consoleLogSpy.mockClear();
        logger.logResponse(code, 100);
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toContain(String(code));
      });
    });

    it('should include duration in milliseconds', () => {
      logger.logResponse(200, 1234);

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('1234ms');
    });

    it('should handle optional method and url', () => {
      logger.logResponse(200, 100);

      expect(consoleLogSpy).toHaveBeenCalled();
      // Should not throw
    });
  });

  describe('logKafkaRequest', () => {
    it('should log Kafka request emission', () => {
      logger.logKafkaRequest(
        'test-topic',
        'test_event',
        'req_123_456',
        1,
        { key: 'value' }
      );

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('test-topic');
      expect(output).toContain('test_event');
    });

    it('should truncate long request IDs', () => {
      const longId = 'req_' + 'a'.repeat(100);
      
      logger.logKafkaRequest('topic', 'event', longId, 1, {});

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('...');
    });

    it('should handle different topics', () => {
      const topics = ['itinerary-requests', 'nlp-requests', 'nearby-pois-requests'];
      
      topics.forEach(topic => {
        consoleLogSpy.mockClear();
        logger.logKafkaRequest(topic, 'event', 'req_123', 1, {});
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toContain(topic);
      });
    });
  });

  describe('logKafkaResponse', () => {
    it('should log successful Kafka response', () => {
      logger.logKafkaResponse('test-responses', 'req_123', 'success', {});

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('test-responses');
      expect(output).toContain('OK');
    });

    it('should log error Kafka response', () => {
      logger.logKafkaResponse('test-responses', 'req_456', 'error', {});

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('ERROR');
    });

    it('should truncate request ID in response', () => {
      const longId = 'req_' + 'b'.repeat(100);
      
      logger.logKafkaResponse('topic-responses', longId, 'success', {});

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('...');
    });
  });

  describe('logError', () => {
    it('should log error with context', () => {
      const error = new Error('Test error message');
      
      logger.logError('TestContext', error);

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('ERROR');
      expect(output).toContain('TestContext');
      expect(output).toContain('Test error message');
    });

    it('should handle different error types', () => {
      const errors = [
        new Error('Standard error'),
        new TypeError('Type error'),
        new ReferenceError('Reference error')
      ];

      errors.forEach(error => {
        consoleLogSpy.mockClear();
        logger.logError('Context', error);
        
        expect(consoleLogSpy).toHaveBeenCalled();
      });
    });

    it('should handle errors with stack traces', () => {
      const error = new Error('Error with stack');
      error.stack = 'Stack trace here';
      
      logger.logError('Context', error);

      expect(consoleLogSpy).toHaveBeenCalled();
    });
  });

  describe('logWarning', () => {
    it('should log warning message', () => {
      logger.logWarning('TestContext', 'Warning message');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('WARNING');
      expect(output).toContain('TestContext');
      expect(output).toContain('Warning message');
    });

    it('should handle different warning contexts', () => {
      const contexts = ['Database', 'Kafka', 'Email', 'Authentication'];
      
      contexts.forEach(context => {
        consoleLogSpy.mockClear();
        logger.logWarning(context, 'Test warning');
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toContain(context);
      });
    });
  });

  describe('logStartup', () => {
    it('should log startup message with port and environment', () => {
      logger.logStartup(3000, 'development');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('BAXPERIENCE');
      expect(output).toContain('3000');
      expect(output).toContain('development');
    });

    it('should handle production environment', () => {
      logger.logStartup(8080, 'production');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('production');
    });

    it('should handle different ports', () => {
      const ports = [3000, 8080, 5000, 4000];
      
      ports.forEach(port => {
        consoleLogSpy.mockClear();
        logger.logStartup(port, 'test');
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toContain(String(port));
      });
    });
  });

  describe('logServiceInitialization', () => {
    it('should log successful service initialization', () => {
      logger.logServiceInitialization('Email Service', 'success');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('Email Service');
      expect(output).toContain('OK');
    });

    it('should log failed service initialization', () => {
      logger.logServiceInitialization('Kafka Service', 'error');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('Kafka Service');
      expect(output).toContain('ERROR');
    });

    it('should log warning service initialization', () => {
      logger.logServiceInitialization('Database Service', 'warning');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('Database Service');
      expect(output).toContain('WARN');
    });

    it('should handle different service names', () => {
      const services = ['Email', 'Kafka', 'Database', 'Cache', 'Storage'];
      
      services.forEach(service => {
        consoleLogSpy.mockClear();
        logger.logServiceInitialization(service, 'success');
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toContain(service);
      });
    });
  });

  describe('Timestamp formatting', () => {
    it('should include timestamp in all logs', () => {
      logger.logIncomingRequest('GET', '/test', '127.0.0.1');

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      // Timestamp format: [HH:MM:SS] or with AM/PM
      expect(output).toMatch(/\[\d{1,2}:\d{2}:\d{2}/);
    });

    it('should use consistent timestamp format', () => {
      const logs = [
        () => logger.logIncomingRequest('GET', '/test', '127.0.0.1'),
        () => logger.logResponse(200, 100),
        () => logger.logError('Test', new Error('test'))
      ];

      logs.forEach(logFn => {
        consoleLogSpy.mockClear();
        logFn();
        
        const output = consoleLogSpy.mock.calls[0].join(' ');
        expect(output).toMatch(/\[\d{1,2}:\d{2}:\d{2}/);
      });
    });
  });

  describe('Color formatting', () => {
    it('should have colors object defined', () => {
      expect(logger.colors).toBeDefined();
      expect(logger.colors).toHaveProperty('request');
      expect(logger.colors).toHaveProperty('response');
      expect(logger.colors).toHaveProperty('error');
      expect(logger.colors).toHaveProperty('kafka');
    });

    it('should use different colors for different log types', () => {
      // This test verifies the structure exists
      expect(logger.colors.success).toBeDefined();
      expect(logger.colors.error).toBeDefined();
      expect(logger.colors.warning).toBeDefined();
    });
  });

  describe('Helper methods', () => {
    it('should have _timestamp method', () => {
      expect(logger._timestamp).toBeDefined();
      expect(typeof logger._timestamp).toBe('function');
    });

    it('should have _formatObject method', () => {
      expect(logger._formatObject).toBeDefined();
      expect(typeof logger._formatObject).toBe('function');
    });

    it('should format objects correctly', () => {
      const obj = { key: 'value', nested: { data: 123 } };
      const formatted = logger._formatObject(obj);
      
      expect(formatted).toContain('key');
      expect(formatted).toContain('value');
    });

    it('should handle null and undefined in _formatObject', () => {
      expect(logger._formatObject(null)).toBe('null');
      expect(logger._formatObject(undefined)).toBe('null');
    });

    it('should handle strings in _formatObject', () => {
      const result = logger._formatObject('test string');
      expect(result).toBe('test string');
    });
  });

  describe('Edge cases', () => {
    it('should handle very long paths', () => {
      const longPath = '/api/' + 'a'.repeat(500);
      
      logger.logIncomingRequest('GET', longPath, '127.0.0.1');

      expect(consoleLogSpy).toHaveBeenCalled();
    });

    it('should handle special characters in paths', () => {
      const specialPath = '/api/users?name=José&city=São Paulo';
      
      logger.logIncomingRequest('GET', specialPath, '127.0.0.1');

      expect(consoleLogSpy).toHaveBeenCalled();
    });

    it('should handle zero duration', () => {
      logger.logResponse(200, 0);

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('0ms');
    });

    it('should handle very large duration', () => {
      logger.logResponse(200, 999999);

      expect(consoleLogSpy).toHaveBeenCalled();
      const output = consoleLogSpy.mock.calls[0].join(' ');
      expect(output).toContain('999999ms');
    });

    it('should handle empty strings', () => {
      logger.logIncomingRequest('', '', '');

      expect(consoleLogSpy).toHaveBeenCalled();
    });

    it('should handle undefined values gracefully', () => {
      logger.logIncomingRequest(undefined, undefined, undefined);

      expect(consoleLogSpy).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    it('should handle rapid consecutive logs', () => {
      for (let i = 0; i < 100; i++) {
        logger.logIncomingRequest('GET', '/test', '127.0.0.1');
      }

      expect(consoleLogSpy).toHaveBeenCalledTimes(100);
    });

    it('should not throw on complex objects', () => {
      const complexObject = {
        level1: {
          level2: {
            level3: {
              level4: {
                data: 'deep'
              }
            }
          }
        }
      };

      expect(() => {
        logger._formatObject(complexObject);
      }).not.toThrow();
    });

    it('should handle circular references gracefully', () => {
      const circular = { name: 'test' };
      circular.self = circular;

      // Should not throw
      const result = logger._formatObject(circular);
      expect(result).toBeDefined();
    });
  });

  describe('Logger instance', () => {
    it('should be a singleton', () => {
      const logger1 = require('../../src/utils/logger');
      const logger2 = require('../../src/utils/logger');

      expect(logger1).toBe(logger2);
    });

    it('should maintain state across requires', () => {
      const logger1 = require('../../src/utils/logger');
      logger1.testProperty = 'test';

      const logger2 = require('../../src/utils/logger');
      expect(logger2.testProperty).toBe('test');

      delete logger1.testProperty;
    });
  });
});
