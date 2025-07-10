#!/bin/bash
# Создание топиков в безопасном Kafka кластере

echo "📋 Создание топиков с TLS..."

KAFKA_BROKER="localhost:9094"
SSL_CONFIG="/etc/kafka/secrets/client-ssl.properties"

# Функция создания топика
create_topic() {
    local topic_name=$1
    local partitions=$2
    local replication_factor=$3
    local min_insync_replicas=$4
    
    echo "Создание топика: $topic_name (partitions=$partitions, replication=$replication_factor)"
    
    docker exec kafka-broker-1 kafka-topics \
        --bootstrap-server $KAFKA_BROKER \
        --command-config $SSL_CONFIG \
        --create \
        --topic $topic_name \
        --partitions $partitions \
        --replication-factor $replication_factor \
        --config min.insync.replicas=$min_insync_replicas \
        --config retention.ms=604800000 \
        --config compression.type=lz4
}

echo "1️⃣  Создание основных топиков..."

# Топики товаров (высокая нагрузка)
create_topic "shop-products" 6 3 2
create_topic "filtered-products" 6 3 2
create_topic "filtered-events" 3 3 2

# Топики поиска и рекомендаций
create_topic "client-searches" 3 3 2
create_topic "client-recommendations" 3 3 2
create_topic "recommendations-results" 3 3 2

# Топики для мониторинга
create_topic "system-metrics" 1 3 2
create_topic "error-logs" 1 3 2

echo "2️⃣  Проверка созданных топиков..."
docker exec kafka-broker-1 kafka-topics \
    --bootstrap-server $KAFKA_BROKER \
    --command-config $SSL_CONFIG \
    --list

echo "3️⃣  Детальная информация о топиках..."
docker exec kafka-broker-1 kafka-topics \
    --bootstrap-server $KAFKA_BROKER \
    --command-config $SSL_CONFIG \
    --describe

echo "✅ Все топики созданы с отказоустойчивостью!"
echo ""
echo "🔧 Параметры отказоустойчивости:"
echo "- Replication Factor: 3 (данные хранятся на 3 брокерах)"
echo "- Min In-Sync Replicas: 2 (минимум 2 реплики должны быть синхронизированы)"
echo "- Retention: 7 дней"
echo "- Compression: LZ4" 