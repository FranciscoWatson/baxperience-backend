#!/bin/bash

echo "🚀 Inicializando topics de Kafka..."

# Esperar a que Kafka esté listo
echo "⏳ Esperando a que Kafka esté listo..."
sleep 30

# Crear topics
echo "📋 Creando topics..."

# Topic para eventos del scraper
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic scraper-events \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

# Topic para actualizaciones de ML
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic ml-updates \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

echo "✅ Topics creados exitosamente!"
echo "📊 Topics disponibles:"
kafka-topics --list --bootstrap-server localhost:9092
