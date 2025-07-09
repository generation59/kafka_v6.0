#!/bin/bash

# Скрипт для создания Kafka топиков

KAFKA_CONTAINER="kafka-broker-1"
REPLICATION_FACTOR=3
PARTITIONS=6

echo "Создание Kafka топиков..."

# Функция для создания топика
create_topic() {
    local topic_name=$1
    local partitions=${2:-$PARTITIONS}
    local replication=${3:-$REPLICATION_FACTOR}
    
    echo "Создание топика: $topic_name (партиции: $partitions, репликация: $replication)"
    
    docker exec -it $KAFKA_CONTAINER kafka-topics \
        --create \
        --topic $topic_name \
        --bootstrap-server localhost:9092 \
        --partitions $partitions \
        --replication-factor $replication \
        --config min.insync.replicas=2 \
        --if-not-exists
}

# Основные топики
echo "=== Создание основных топиков ==="

# Топик для товаров от магазинов
create_topic "shop-products" 6 3

# Топик для отфильтрованных товаров
create_topic "filtered-products" 6 3

# Топик для событий фильтрации
create_topic "filtered-events" 3 3

# Топики для клиентских запросов
create_topic "client-searches" 3 3
create_topic "client-recommendations" 3 3
create_topic "recommendations-results" 3 3

# Топики для Kafka Connect
echo "=== Создание служебных топиков ==="

create_topic "docker-connect-configs" 1 3
create_topic "docker-connect-offsets" 25 3
create_topic "docker-connect-status" 5 3

# Топики для файлового вывода
create_topic "file-sink-products" 3 3
create_topic "file-sink-analytics" 3 3

echo "=== Список созданных топиков ==="
docker exec -it $KAFKA_CONTAINER kafka-topics \
    --list \
    --bootstrap-server localhost:9092

echo "=== Детали топиков ==="
docker exec -it $KAFKA_CONTAINER kafka-topics \
    --describe \
    --bootstrap-server localhost:9092

echo "Настройка топиков завершена!" 