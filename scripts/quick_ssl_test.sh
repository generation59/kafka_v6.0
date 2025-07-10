#!/bin/bash
# Быстрый тест SSL подключения к Kafka в WSL

echo "🚀 Быстрая диагностика и исправление SSL для Kafka в WSL"
echo "==========================================================="

# Проверяем, есть ли SSL сертификаты
if [ ! -d "ssl" ]; then
    echo "📁 SSL сертификаты не найдены, создаем..."
    ./scripts/generate_ssl_certs.sh
else
    echo "📁 SSL сертификаты найдены"
fi

# Исправляем права доступа
echo ""
echo "🔧 Исправляем права доступа..."
./scripts/fix_ssl_permissions.sh

# Проверяем, запущен ли Kafka
echo ""
echo "🔍 Проверяем статус Kafka..."
if docker ps | grep -q kafka-broker; then
    echo "✅ Kafka контейнеры запущены"
else
    echo "🚀 Запускаем Kafka с SSL..."
    docker compose -f docker-compose-secure.yml down -v 2>/dev/null || true
    docker compose -f docker-compose-secure.yml up -d
    echo "⏳ Ждем запуска Kafka (30 секунд)..."
    sleep 30
fi

# Тестируем SSL подключение
echo ""
echo "🧪 Тестируем SSL подключение..."
python3 scripts/test_ssl_connection.py

echo ""
echo "📋 Статус контейнеров:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "💡 Для тестирования SSL продюсера выполните:"
echo "   python -m src.shop_api.producer --ssl-auto"
echo ""
echo "💡 Для проверки логов Kafka:"
echo "   docker logs kafka-broker-1" 