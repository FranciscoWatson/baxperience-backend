const { Kafka } = require('kafkajs');
const logger = require('../utils/logger');

class KafkaService {
  constructor() {
    this.kafka = new Kafka({
      clientId: 'baxperience-api-gateway',
      brokers: [process.env.KAFKA_BROKER || 'localhost:9092']
    });
    
    this.producer = null;
    this.consumer = null;
    this.isConnected = false;
    this.pendingRequests = new Map(); // Para guardar callbacks de respuestas pendientes
    this.subscribedTopics = new Set(); // Para trackear topics suscritos
  }

  async connect() {
    try {
      if (this.isConnected) {
        return true;
      }

      // Crear productor
      this.producer = this.kafka.producer({
        maxInFlightRequests: 1,
        idempotent: true,
        transactionTimeout: 30000
      });

      // Crear consumidor para respuestas
      this.consumer = this.kafka.consumer({
        groupId: 'api-gateway-responses',
        sessionTimeout: 30000,
        heartbeatInterval: 3000
      });

      // Conectar
      await this.producer.connect();
      await this.consumer.connect();

      // Suscribirse a TODOS los topics de respuestas ANTES de consumer.run()
      await this.consumer.subscribe({
        topics: ['itinerary-responses', 'nlp-responses', 'nearby-pois-responses'],
        fromBeginning: false
      });

      // Agregar los topics a la lista de suscritos
      this.subscribedTopics.add('itinerary-responses');
      this.subscribedTopics.add('nlp-responses');
      this.subscribedTopics.add('nearby-pois-responses');

      // Configurar el handler ÚNICO para TODOS los topics
      await this.consumer.run({
        eachMessage: async ({ topic, partition, message }) => {
          try {
            const response = JSON.parse(message.value.toString());
            const requestId = response.request_id;

            logger.logKafkaResponse(topic, requestId, response.status, response.data || response.error || {});

            if (this.pendingRequests.has(requestId)) {
              const callback = this.pendingRequests.get(requestId);
              this.pendingRequests.delete(requestId);
              callback(response);
            } else {
              logger.logWarning('Kafka', `No pending request found for ID: ${requestId}`);
            }
          } catch (error) {
            logger.logError('Kafka Message Processing', error);
          }
        }
      });

      this.isConnected = true;
      return true;

    } catch (error) {
      logger.logError('Kafka Connection', error);
      this.isConnected = false;
      return false;
    }
  }

  async subscribeToResponseTopic(topic) {
    // Este método ya no es necesario porque suscribimos a todos los topics en connect()
    // Lo mantenemos por compatibilidad pero solo verifica si ya está suscrito
    if (this.subscribedTopics.has(topic)) {
      return;
    }
  }

  async sendRequest(topic, eventType, userId, requestData, requestPrefix = 'req') {
    if (!this.isConnected) {
      const connected = await this.connect();
      if (!connected) {
        throw new Error('Could not connect to Kafka');
      }
    }

    const requestId = `${requestPrefix}_${userId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const event = {
      event_type: eventType,
      request_id: requestId,
      user_id: userId,
      request_data: requestData || {},
      timestamp: new Date().toISOString(),
      source: "api_gateway"
    };

    try {
      await this.producer.send({
        topic: topic,
        messages: [{
          key: requestId,
          value: JSON.stringify(event)
        }]
      });

      logger.logKafkaRequest(topic, eventType, requestId, userId, requestData);
      return requestId;

    } catch (error) {
      logger.logError(`Kafka Send (${eventType})`, error);
      throw new Error(`Failed to send ${eventType} request`);
    }
  }

  // Se puede hacer asi tambien
  async sendItineraryRequest(userId, requestData) {
    return this.sendRequest('itinerary-requests', 'itinerary_request', userId, requestData, 'itinerary_req');
  }

  async sendItineraryRequestAndWait(userId, requestData, timeout = 45000) {
    return this.sendAndWaitForResponse('itinerary-requests', 'itinerary_request', userId, requestData, timeout, 'itinerary_req');
  }

  async sendNearbyPoisRequestAndWait(requestData, timeout = 30000) {
    // Para nearby POIs no necesitamos userId, pero usamos 0 como placeholder
    return this.sendAndWaitForResponse('nearby-pois-requests', 'nearby_pois_request', 0, requestData, timeout, 'nearby_pois_req');
  }

  waitForResponse(requestId, timeoutMs = 45000) {
    return new Promise((resolve, reject) => {
      // Verificar si ya hay una respuesta pendiente
      if (this.pendingRequests.has(requestId)) {
        reject(new Error(`Request ${requestId} is already waiting for response`));
        return;
      }

      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error(`Timeout waiting for response to request: ${requestId}`));
      }, timeoutMs);

      this.pendingRequests.set(requestId, (response) => {
        clearTimeout(timeout);
        resolve(response);
      });

      logger.logKafkaWaiting(requestId, timeoutMs);
    });
  }

  async sendAndWaitForResponse(topic, eventType, userId, requestData, responseTimeout = 45000, requestPrefix = 'req') {
    try {
      const requestId = await this.sendRequest(topic, eventType, userId, requestData, requestPrefix);
      const response = await this.waitForResponse(requestId, responseTimeout);
      return { requestId, response };
    } catch (error) {
      logger.logError(`Kafka Send & Wait (${eventType})`, error);
      throw error;
    }
  }

  async disconnect() {
    try {
      if (this.producer) {
        await this.producer.disconnect();
      }
      if (this.consumer) {
        await this.consumer.disconnect();
      }
      this.isConnected = false;
    } catch (error) {
      logger.logError('Kafka Disconnect', error);
    }
  }
}

// Singleton instance
const kafkaService = new KafkaService();

// Manejar cierre graceful
process.on('SIGINT', async () => {
  await kafkaService.disconnect();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await kafkaService.disconnect();
  process.exit(0);
});

module.exports = kafkaService;
