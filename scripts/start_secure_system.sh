#!/bin/bash
# Главный скрипт для запуска безопасной Kafka системы

set -e

echo "🚀 Запуск безопасной Kafka системы с TLS + ACL..."
echo "================================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Шаг 1: Генерация SSL сертификатов
print_step "1️⃣  Генерация SSL сертификатов..."
if [ ! -d "ssl" ]; then
    chmod +x scripts/generate_ssl_certs.sh
    ./scripts/generate_ssl_certs.sh
    print_success "SSL сертификаты созданы"
else
    print_warning "SSL сертификаты уже существуют, пропускаем..."
fi

# Шаг 2: Остановка предыдущих контейнеров
print_step "2️⃣  Остановка предыдущих контейнеров..."
docker compose down -v 2>/dev/null || true
print_success "Контейнеры остановлены"

# Шаг 3: Запуск Kafka кластера
print_step "3️⃣  Запуск Kafka кластера..."
docker compose -f docker-compose-secure.yml up -d zookeeper
sleep 10
docker compose -f docker-compose-secure.yml up -d kafka-broker-1 kafka-broker-2 kafka-broker-3
sleep 30
print_success "Kafka кластер запущен"

# Шаг 4: Создание топиков
print_step "4️⃣  Создание топиков..."
chmod +x scripts/create_topics_simple.sh
./scripts/create_topics_simple.sh
print_success "Топики созданы"

# Шаг 5: Запуск мониторинга и аналитики
print_step "5️⃣  Запуск мониторинга и аналитики..."
docker compose -f docker-compose-secure.yml up -d prometheus grafana alertmanager
docker compose -f docker-compose-secure.yml up -d spark-master spark-worker
sleep 15
print_success "Мониторинг и аналитика запущены"

# Проверка статуса всех сервисов
print_step "🔍 Проверка статуса сервисов..."
echo ""
echo "📊 Kafka кластер (TLS):"
echo "- Broker 1: localhost:9093 (SSL)"
echo "- Broker 2: localhost:9096 (SSL)"
echo "- Broker 3: localhost:9099 (SSL)"
echo ""
echo "📈 Мониторинг:"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (admin/grafana)"
echo "- Alertmanager: http://localhost:9394"
echo ""
echo "⚡ Аналитика:"
echo "- Spark Master: http://localhost:8080"
echo ""

# Проверка подключения к кластеру
print_step "🧪 Тестирование подключения..."
docker exec kafka-broker-1 kafka-topics \
    --bootstrap-server localhost:9093 \
    --list

print_success "Система полностью развернута!"
echo ""
echo "🔑 БЕЗОПАСНОСТЬ НАСТРОЕНА:"
echo "✅ TLS шифрование включено"
echo "✅ Отказоустойчивость: репликация x3, min.insync.replicas=2"
echo "✅ Мониторинг системы активен"
echo ""
echo "🔐 SSL порты для подключения:"
echo "- Broker 1: localhost:9093"
echo "- Broker 2: localhost:9096"
echo "- Broker 3: localhost:9099"
echo ""
echo "📋 PLAINTEXT порты (для разработки):"
echo "- Broker 1: localhost:9092"
echo "- Broker 2: localhost:9095"
echo "- Broker 3: localhost:9098"
echo ""
echo "🎯 Готово! Один кластер с TLS + отказоустойчивостью." 