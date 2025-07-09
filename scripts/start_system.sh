#!/bin/bash

# Скрипт для запуска аналитической платформы маркетплейса

set -e

echo "🚀 Запуск аналитической платформы маркетплейса"
echo "=============================================="

# Функция для проверки доступности сервиса
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Ожидание запуска $service_name на порту $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo "✅ $service_name доступен!"
            return 0
        fi
        
        echo "   Попытка $attempt/$max_attempts..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name не удалось запустить в отведенное время"
    return 1
}

# Функция для проверки Docker образов
check_docker_images() {
    echo "🔍 Проверка Docker образов..."
    
    required_images=(
        "confluentinc/cp-zookeeper:7.4.3"
        "confluentinc/cp-kafka:7.4.3"
        "confluentinc/cp-kafka-connect:7.4.3"
        "prom/prometheus:v2.48.0"
        "grafana/grafana:10.2.0"
        "prom/alertmanager:v0.26.0"
        # "docker.elastic.co/elasticsearch/elasticsearch:8.11.1"  # Отключено из-за блокировки CloudFront
        "bitnami/spark:3.5.0"
    )
    
    for image in "${required_images[@]}"; do
        if ! docker image inspect "$image" >/dev/null 2>&1; then
            echo "⬇️  Загрузка образа $image..."
            docker pull "$image"
        fi
    done
    
    echo "✅ Все Docker образы готовы"
}

# 1. Проверка зависимостей
echo "1️⃣  Проверка зависимостей..."

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker не установлен"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "❌ Docker Compose не установлен"
    exit 1
fi

if ! command -v nc >/dev/null 2>&1; then
    echo "⚠️  netcat не установлен, проверка портов будет пропущена"
fi

check_docker_images

# 2. Остановка существующих контейнеров
echo "2️⃣  Остановка существующих контейнеров..."
docker compose down -v 2>/dev/null || true

# 3. Создание необходимых директорий
echo "3️⃣  Создание директорий..."
mkdir -p data/kafka-connect-data
mkdir -p data/output
chmod 777 data/kafka-connect-data
chmod 777 data/output

# 4. Запуск инфраструктуры
echo "4️⃣  Запуск инфраструктуры..."
docker compose up -d

# 5. Ожидание запуска сервисов
echo "5️⃣  Ожидание запуска сервисов..."

wait_for_service "Zookeeper" 2181
wait_for_service "Kafka Broker 1" 9092
wait_for_service "Kafka Broker 2" 9093
wait_for_service "Kafka Broker 3" 9094
wait_for_service "Kafka Connect" 8083
wait_for_service "Prometheus" 9090
wait_for_service "Grafana" 3000
wait_for_service "Alertmanager" 9394
# wait_for_service "Elasticsearch" 9200  # Отключено
wait_for_service "Spark Master" 8080

# 6. Настройка Kafka топиков
echo "6️⃣  Настройка Kafka топиков..."
chmod +x scripts/setup_kafka_topics.sh
./scripts/setup_kafka_topics.sh

# 7. Настройка Kafka Connect
echo "7️⃣  Настройка Kafka Connect..."
sleep 10  # Дополнительное время для полного запуска Kafka Connect

echo "Создание File Sink коннектора..."
curl -X POST http://localhost:8083/connectors \
    -H "Content-Type: application/json" \
    -d @config/file-sink-connector.json || echo "⚠️  Не удалось создать коннектор (возможно, уже существует)"

# 8. Проверка статуса
echo "8️⃣  Проверка статуса системы..."

echo ""
echo "📊 Статус сервисов:"
echo "==================="

# Kafka
if nc -z localhost 9092 2>/dev/null; then
    echo "✅ Kafka Cluster: работает"
    docker exec kafka-broker-1 kafka-topics.sh --bootstrap-server localhost:9092 --list | head -5
else
    echo "❌ Kafka Cluster: недоступен"
fi

# Kafka Connect
if curl -s http://localhost:8083/connectors >/dev/null 2>&1; then
    echo "✅ Kafka Connect: работает"
    echo "   Коннекторы: $(curl -s http://localhost:8083/connectors | jq -r '. | length') активных"
else
    echo "❌ Kafka Connect: недоступен"
fi

# Prometheus
if curl -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
    echo "✅ Prometheus: работает"
else
    echo "❌ Prometheus: недоступен"
fi

# Grafana
if curl -s http://localhost:3000/api/health >/dev/null 2>&1; then
    echo "✅ Grafana: работает (admin/grafana)"
else
    echo "❌ Grafana: недоступен"
fi

# Файловый поиск
echo "✅ Поиск товаров: файловый (Elasticsearch отключен)"

# Spark
if curl -s http://localhost:8080 >/dev/null 2>&1; then
    echo "✅ Spark Master: работает"
else
    echo "❌ Spark Master: недоступен"
fi

echo ""
echo "🎯 Веб-интерфейсы:"
echo "=================="
echo "• Grafana:        http://localhost:3000 (admin/grafana)"
echo "• Prometheus:     http://localhost:9090"
echo "• Alertmanager:   http://localhost:9394"
echo "• Spark Master:   http://localhost:8080"
echo "• Kafka Connect:  http://localhost:8083"

echo ""
echo "🔧 Команды для работы с системой:"
echo "================================="
echo "• Запуск Shop API:        python -m src.shop_api.producer"
echo "• Запуск Client API:      python -m src.client_api.client search 'умные часы'"
echo "• Запуск Stream Filter:   python -m src.stream_processor.banned_filter start"
echo "• Запуск Analytics:       python -m src.analytics.spark_analytics start"
echo "• Управление банами:      python -m src.stream_processor.banned_filter ban --product-id 'ID'"

echo ""
echo "✅ Система запущена и готова к работе!"
echo ""
echo "📝 Для остановки системы выполните: docker compose down" 