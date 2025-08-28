const { Kafka } = require('kafkajs');

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

      // Suscribirse al topic de respuestas de itinerarios por defecto
      await this.subscribeToResponseTopic('itinerary-responses');

      this.isConnected = true;
      console.log('✅ Kafka service connected successfully');
      return true;

    } catch (error) {
      console.error('❌ Error connecting to Kafka:', error);
      this.isConnected = false;
      return false;
    }
  }

  async subscribeToResponseTopic(topic) {
    try {
      if (this.subscribedTopics.has(topic)) {
        console.log(`Already subscribed to topic: ${topic}`);
        return;
      }

      await this.consumer.subscribe({
        topic: topic,
        fromBeginning: false
      });

      this.subscribedTopics.add(topic);

      // Si es la primera suscripción, configurar el handler
      if (this.subscribedTopics.size === 1) {
        await this.consumer.run({
          eachMessage: async ({ topic, partition, message }) => {
            try {
              const response = JSON.parse(message.value.toString());
              const requestId = response.request_id;

              console.log(`📥 Response received from topic ${topic} for request: ${requestId}`);

              if (this.pendingRequests.has(requestId)) {
                const callback = this.pendingRequests.get(requestId);
                this.pendingRequests.delete(requestId);
                callback(response);
              } else {
                console.log(`No pending request found for ID: ${requestId}`);
              }
            } catch (error) {
              console.error('Error processing Kafka response:', error);
            }
          }
        });
      }

      console.log(`✅ Subscribed to response topic: ${topic}`);

    } catch (error) {
      console.error(`❌ Error subscribing to topic ${topic}:`, error);
      throw error;
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

      console.log(`📤 ${eventType} request sent - Request ID: ${requestId}, User: ${userId}, Topic: ${topic}`);
      return requestId;

    } catch (error) {
      console.error(`❌ Error sending ${eventType} request:`, error);
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

      console.log(`⏳ Waiting for response to request: ${requestId} (timeout: ${timeoutMs}ms)`);
    });
  }

  async sendAndWaitForResponse(topic, eventType, userId, requestData, responseTimeout = 45000, requestPrefix = 'req') {
    try {
      const requestId = await this.sendRequest(topic, eventType, userId, requestData, requestPrefix);
      const response = await this.waitForResponse(requestId, responseTimeout);
      return { requestId, response };
    } catch (error) {
      console.error(`❌ Error in sendAndWaitForResponse for ${eventType}:`, error);
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
      console.log('👋 Kafka service disconnected');
    } catch (error) {
      console.error('❌ Error disconnecting from Kafka:', error);
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
