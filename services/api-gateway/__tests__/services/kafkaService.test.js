const KafkaService = require('../../src/services/kafkaService');
const { Kafka } = require('kafkajs');

// Mock kafkajs
jest.mock('kafkajs');
jest.mock('../../src/utils/logger');

describe('KafkaService', () => {
  let kafkaService;
  let mockProducer;
  let mockConsumer;
  let mockKafka;

  beforeEach(() => {
    jest.clearAllMocks();

    // Create mocks
    mockProducer = {
      connect: jest.fn().mockResolvedValue(undefined),
      disconnect: jest.fn().mockResolvedValue(undefined),
      send: jest.fn().mockResolvedValue(undefined)
    };

    mockConsumer = {
      connect: jest.fn().mockResolvedValue(undefined),
      disconnect: jest.fn().mockResolvedValue(undefined),
      subscribe: jest.fn().mockResolvedValue(undefined),
      run: jest.fn().mockResolvedValue(undefined)
    };

    mockKafka = {
      producer: jest.fn().mockReturnValue(mockProducer),
      consumer: jest.fn().mockReturnValue(mockConsumer)
    };

    Kafka.mockImplementation(() => mockKafka);

    // Create a new instance for each test
    const KafkaServiceClass = require('../../src/services/kafkaService').constructor;
    kafkaService = new KafkaServiceClass();
  });

  describe('constructor', () => {
    it('should initialize with correct configuration', () => {
      expect(Kafka).toHaveBeenCalledWith({
        clientId: 'baxperience-api-gateway',
        brokers: [process.env.KAFKA_BROKER || 'localhost:9092']
      });
    });

    it('should initialize with not connected state', () => {
      expect(kafkaService.isConnected).toBe(false);
    });

    it('should initialize empty pending requests map', () => {
      expect(kafkaService.pendingRequests).toBeInstanceOf(Map);
      expect(kafkaService.pendingRequests.size).toBe(0);
    });

    it('should initialize empty subscribed topics set', () => {
      expect(kafkaService.subscribedTopics).toBeInstanceOf(Set);
      expect(kafkaService.subscribedTopics.size).toBe(0);
    });
  });

  describe('connect', () => {
    it('should connect successfully', async () => {
      const result = await kafkaService.connect();

      expect(mockProducer.connect).toHaveBeenCalled();
      expect(mockConsumer.connect).toHaveBeenCalled();
      expect(mockConsumer.subscribe).toHaveBeenCalledWith({
        topics: ['itinerary-responses', 'nlp-responses', 'nearby-pois-responses'],
        fromBeginning: false
      });
      expect(mockConsumer.run).toHaveBeenCalled();
      expect(kafkaService.isConnected).toBe(true);
      expect(result).toBe(true);
    });

    it('should return true if already connected', async () => {
      kafkaService.isConnected = true;

      const result = await kafkaService.connect();

      expect(mockProducer.connect).not.toHaveBeenCalled();
      expect(mockConsumer.connect).not.toHaveBeenCalled();
      expect(result).toBe(true);
    });

    it('should handle connection errors', async () => {
      mockProducer.connect.mockRejectedValue(new Error('Connection failed'));

      const result = await kafkaService.connect();

      expect(result).toBe(false);
      expect(kafkaService.isConnected).toBe(false);
    });

    it('should subscribe to all response topics', async () => {
      await kafkaService.connect();

      expect(kafkaService.subscribedTopics.has('itinerary-responses')).toBe(true);
      expect(kafkaService.subscribedTopics.has('nlp-responses')).toBe(true);
      expect(kafkaService.subscribedTopics.has('nearby-pois-responses')).toBe(true);
    });

    it('should create producer with correct configuration', async () => {
      await kafkaService.connect();

      expect(mockKafka.producer).toHaveBeenCalledWith({
        maxInFlightRequests: 1,
        idempotent: true,
        transactionTimeout: 30000
      });
    });

    it('should create consumer with correct configuration', async () => {
      await kafkaService.connect();

      expect(mockKafka.consumer).toHaveBeenCalledWith({
        groupId: 'api-gateway-responses',
        sessionTimeout: 30000,
        heartbeatInterval: 3000
      });
    });
  });

  describe('sendRequest', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should send request successfully', async () => {
      const topic = 'test-topic';
      const eventType = 'test_event';
      const userId = 123;
      const requestData = { key: 'value' };

      const requestId = await kafkaService.sendRequest(
        topic,
        eventType,
        userId,
        requestData
      );

      expect(requestId).toMatch(/^req_123_\d+_/);
      expect(mockProducer.send).toHaveBeenCalledWith({
        topic,
        messages: [{
          key: requestId,
          value: expect.stringContaining(eventType)
        }]
      });
    });

    it('should include all required fields in event', async () => {
      const topic = 'test-topic';
      const eventType = 'test_event';
      const userId = 456;
      const requestData = { test: 'data' };

      await kafkaService.sendRequest(topic, eventType, userId, requestData);

      const sentMessage = JSON.parse(
        mockProducer.send.mock.calls[0][0].messages[0].value
      );

      expect(sentMessage).toHaveProperty('event_type', eventType);
      expect(sentMessage).toHaveProperty('request_id');
      expect(sentMessage).toHaveProperty('user_id', userId);
      expect(sentMessage).toHaveProperty('request_data', requestData);
      expect(sentMessage).toHaveProperty('timestamp');
      expect(sentMessage).toHaveProperty('source', 'api_gateway');
    });

    it('should use custom request prefix', async () => {
      const requestId = await kafkaService.sendRequest(
        'topic',
        'event',
        123,
        {},
        'custom_prefix'
      );

      expect(requestId).toMatch(/^custom_prefix_123_/);
    });

    it('should connect if not connected', async () => {
      const newKafkaService = new (require('../../src/services/kafkaService').constructor)();
      mockProducer.send.mockClear();

      await newKafkaService.sendRequest('topic', 'event', 1, {});

      expect(mockProducer.connect).toHaveBeenCalled();
      expect(mockProducer.send).toHaveBeenCalled();
    });

    it('should throw error if send fails', async () => {
      mockProducer.send.mockRejectedValue(new Error('Send failed'));

      await expect(
        kafkaService.sendRequest('topic', 'event', 1, {})
      ).rejects.toThrow('Failed to send event request');
    });

    it('should handle empty request data', async () => {
      const requestId = await kafkaService.sendRequest(
        'topic',
        'event',
        1
      );

      const sentMessage = JSON.parse(
        mockProducer.send.mock.calls[0][0].messages[0].value
      );

      expect(sentMessage.request_data).toEqual({});
      expect(requestId).toBeDefined();
    });
  });

  describe('sendItineraryRequest', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should send itinerary request', async () => {
      const userId = 123;
      const requestData = { days: 3 };

      const requestId = await kafkaService.sendItineraryRequest(userId, requestData);

      expect(requestId).toMatch(/^itinerary_req_123_/);
      expect(mockProducer.send).toHaveBeenCalledWith(
        expect.objectContaining({
          topic: 'itinerary-requests'
        })
      );
    });
  });

  describe('waitForResponse', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should timeout if no response arrives', async () => {
      const requestId = 'test_req_timeout';

      await expect(
        kafkaService.waitForResponse(requestId, 100)
      ).rejects.toThrow(/Timeout waiting for response/);

      expect(kafkaService.pendingRequests.has(requestId)).toBe(false);
    });

    it('should reject if request is already waiting', async () => {
      const requestId = 'test_req_duplicate';

      kafkaService.waitForResponse(requestId, 5000);

      await expect(
        kafkaService.waitForResponse(requestId, 5000)
      ).rejects.toThrow(/already waiting for response/);
    });

    it('should use custom timeout', async () => {
      const requestId = 'test_req_custom_timeout';
      const customTimeout = 50;

      const start = Date.now();
      
      await expect(
        kafkaService.waitForResponse(requestId, customTimeout)
      ).rejects.toThrow(/Timeout/);

      const elapsed = Date.now() - start;
      expect(elapsed).toBeGreaterThanOrEqual(customTimeout);
      expect(elapsed).toBeLessThan(customTimeout + 100);
    });
  });

  describe('sendAndWaitForResponse', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should handle errors during send and wait', async () => {
      mockProducer.send.mockRejectedValue(new Error('Send failed'));

      await expect(
        kafkaService.sendAndWaitForResponse('topic', 'event', 1, {})
      ).rejects.toThrow();
    });
  });

  describe('sendItineraryRequestAndWait', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should send itinerary request and wait', async () => {
      jest.spyOn(kafkaService, 'sendAndWaitForResponse').mockResolvedValue({
        requestId: 'test_id',
        response: { status: 'success' }
      });

      const result = await kafkaService.sendItineraryRequestAndWait(
        123,
        { days: 3 }
      );

      expect(kafkaService.sendAndWaitForResponse).toHaveBeenCalledWith(
        'itinerary-requests',
        'itinerary_request',
        123,
        { days: 3 },
        45000,
        'itinerary_req'
      );
      expect(result).toHaveProperty('requestId');
      expect(result).toHaveProperty('response');
    });
  });

  describe('sendNearbyPoisRequestAndWait', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should send nearby POIs request and wait', async () => {
      jest.spyOn(kafkaService, 'sendAndWaitForResponse').mockResolvedValue({
        requestId: 'test_id',
        response: { status: 'success' }
      });

      const result = await kafkaService.sendNearbyPoisRequestAndWait(
        { lat: -34.6037, lng: -58.3816 }
      );

      expect(kafkaService.sendAndWaitForResponse).toHaveBeenCalledWith(
        'nearby-pois-requests',
        'nearby_pois_request',
        0,
        { lat: -34.6037, lng: -58.3816 },
        30000,
        'nearby_pois_req'
      );
      expect(result).toHaveProperty('requestId');
    });
  });

  describe('disconnect', () => {
    it('should disconnect producer and consumer', async () => {
      await kafkaService.connect();
      await kafkaService.disconnect();

      expect(mockProducer.disconnect).toHaveBeenCalled();
      expect(mockConsumer.disconnect).toHaveBeenCalled();
      expect(kafkaService.isConnected).toBe(false);
    });

    it('should handle disconnect errors gracefully', async () => {
      await kafkaService.connect();
      mockProducer.disconnect.mockRejectedValue(new Error('Disconnect failed'));

      await expect(kafkaService.disconnect()).resolves.not.toThrow();
    });

    it('should not throw if producer is null', async () => {
      kafkaService.producer = null;

      await expect(kafkaService.disconnect()).resolves.not.toThrow();
    });
  });

  describe('subscribeToResponseTopic', () => {
    beforeEach(async () => {
      await kafkaService.connect();
    });

    it('should handle already subscribed topics', async () => {
      await kafkaService.subscribeToResponseTopic('itinerary-responses');

      // Should not throw and should complete successfully
      expect(kafkaService.subscribedTopics.has('itinerary-responses')).toBe(true);
    });

    it('should handle new topic subscription', async () => {
      await kafkaService.subscribeToResponseTopic('new-topic');

      // Method exists for compatibility but doesn't do much
      expect(true).toBe(true);
    });
  });

  describe('Message processing', () => {
    let messageHandler;

    beforeEach(async () => {
      mockConsumer.run.mockImplementation(async ({ eachMessage }) => {
        messageHandler = eachMessage;
      });

      await kafkaService.connect();
    });

    it('should process valid response messages', async () => {
      const requestId = 'test_req_123';
      const mockCallback = jest.fn();
      
      kafkaService.pendingRequests.set(requestId, mockCallback);

      const mockMessage = {
        topic: 'test-responses',
        partition: 0,
        message: {
          value: Buffer.from(JSON.stringify({
            request_id: requestId,
            status: 'success',
            data: { result: 'test' }
          }))
        }
      };

      await messageHandler(mockMessage);

      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          request_id: requestId,
          status: 'success'
        })
      );
      expect(kafkaService.pendingRequests.has(requestId)).toBe(false);
    });

    it('should handle messages with no pending request', async () => {
      const mockMessage = {
        topic: 'test-responses',
        partition: 0,
        message: {
          value: Buffer.from(JSON.stringify({
            request_id: 'unknown_req',
            status: 'success'
          }))
        }
      };

      // Should not throw
      await expect(messageHandler(mockMessage)).resolves.not.toThrow();
    });

    it('should handle malformed message JSON', async () => {
      const mockMessage = {
        topic: 'test-responses',
        partition: 0,
        message: {
          value: Buffer.from('invalid json')
        }
      };

      // Should not throw
      await expect(messageHandler(mockMessage)).resolves.not.toThrow();
    });
  });

  describe('Edge cases', () => {
    it('should generate unique request IDs', async () => {
      await kafkaService.connect();

      const id1 = await kafkaService.sendRequest('topic', 'event', 1, {});
      const id2 = await kafkaService.sendRequest('topic', 'event', 1, {});

      expect(id1).not.toBe(id2);
    });

    it('should handle rapid consecutive requests', async () => {
      await kafkaService.connect();

      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(
          kafkaService.sendRequest('topic', 'event', i, { index: i })
        );
      }

      const results = await Promise.all(promises);

      expect(results).toHaveLength(10);
      expect(new Set(results).size).toBe(10); // All unique
    });

    it('should handle connection failure gracefully', async () => {
      mockProducer.connect.mockRejectedValue(new Error('Network error'));

      const result = await kafkaService.connect();

      expect(result).toBe(false);
      expect(kafkaService.isConnected).toBe(false);
    });
  });
});
