#!/bin/bash

# Демонстрационный скрипт работы аналитической платформы маркетплейса

set -e

echo "🎬 Демонстрация аналитической платформы маркетплейса"
echo "=================================================="

# Проверка запуска системы
check_system() {
    echo "🔍 Проверка готовности системы..."
    
            services=(
            "localhost:9092:Kafka"
            "localhost:8083:Kafka Connect"
            "localhost:8080:Spark"
        )
    
    for service in "${services[@]}"; do
        IFS=':' read -r host port name <<< "$service"
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "✅ $name готов"
        else
            echo "❌ $name не доступен на $host:$port"
            echo "Запустите систему командой: ./scripts/start_system.sh"
            exit 1
        fi
    done
    
    echo ""
}

# Демонстрация Shop API
demo_shop_api() {
    echo "🏪 Демонстрация Shop API (отправка товаров в Kafka)"
    echo "------------------------------------------------"
    
    echo "📦 Отправляем товары из файла в Kafka..."
    python -m src.shop_api.producer --file data/products.json --delay 0.5 &
    SHOP_PID=$!
    
    echo "⏳ Ждем 10 секунд для отправки товаров..."
    sleep 10
    
    # Останавливаем продюсер
    kill $SHOP_PID 2>/dev/null || true
    
    echo "✅ Товары отправлены в топик shop-products"
    echo ""
}

# Демонстрация фильтрации
demo_filtering() {
    echo "🔍 Демонстрация фильтрации запрещённых товаров"
    echo "----------------------------------------------"
    
    echo "🚫 Добавляем товар в чёрный список..."
    python -m src.stream_processor.banned_filter ban \
        --product-id "BANNED-TEST-001" \
        --name "Тестовый запрещённый товар" \
        --reason "Демонстрация фильтрации"
    
    echo "📋 Текущий список запрещённых товаров:"
    python -m src.stream_processor.banned_filter list
    
    echo "🔄 Запускаем фильтрацию (10 секунд)..."
    python -m src.stream_processor.banned_filter start &
    FILTER_PID=$!
    
    sleep 10
    kill $FILTER_PID 2>/dev/null || true
    
    echo "✅ Фильтрация завершена"
    echo ""
}

# Демонстрация Client API
demo_client_api() {
    echo "👥 Демонстрация Client API (поиск и рекомендации)"
    echo "------------------------------------------------"
    
    echo "🔍 Поиск товаров по запросу 'умные часы':"
    python -m src.client_api.client search "умные часы" --limit 3
    
    echo ""
    echo "🔍 Поиск товаров по запросу 'смартфон':"
    python -m src.client_api.client search "смартфон" --limit 2
    
    echo ""
    echo "💡 Запрос персонализированных рекомендаций:"
    python -m src.client_api.client recommendations \
        --category "Электроника" \
        --max-price 30000 \
        --brand "XYZ"
    
    echo ""
    echo "📊 Статус подключений Client API:"
    python -m src.client_api.client status
    
    echo ""
}

# Демонстрация аналитики
demo_analytics() {
    echo "📊 Демонстрация аналитической системы"
    echo "------------------------------------"
    
    echo "🧠 Тестирование генерации рекомендаций:"
    python -m src.analytics.spark_analytics test-recommendations \
        "demo-user-001" \
        --category "Электроника" \
        --max-price 50000
    
    echo ""
    echo "⚡ Запуск Spark аналитики (15 секунд)..."
    echo "   (В реальной системе это работает непрерывно)"
    
    timeout 15 python -m src.analytics.spark_analytics start || true
    
    echo "✅ Демонстрация аналитики завершена"
    echo ""
}

# Демонстрация мониторинга
demo_monitoring() {
    echo "📈 Демонстрация системы мониторинга"
    echo "----------------------------------"
    
    echo "🎯 Веб-интерфейсы мониторинга:"
    echo "• Grafana:      http://localhost:3000 (admin/grafana)"
    echo "• Prometheus:   http://localhost:9090"
    echo "• Spark UI:     http://localhost:8080"
    
    echo ""
    echo "📊 Проверка метрик Prometheus:"
    
    # Проверяем доступность Prometheus
    if curl -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
        echo "✅ Prometheus доступен"
        
        # Получаем список метрик
        echo "📋 Доступные метрики:"
        curl -s http://localhost:9090/api/v1/label/__name__/values | \
            jq -r '.data[]' | grep -E "(kafka|up)" | head -5 || echo "   Метрики загружаются..."
    else
        echo "⚠️  Prometheus недоступен"
    fi
    
    echo ""
    echo "🔔 Проверка Alertmanager:"
    if curl -s http://localhost:9093/-/healthy >/dev/null 2>&1; then
        echo "✅ Alertmanager доступен"
        
        # Проверяем активные алерты
        alerts=$(curl -s http://localhost:9093/api/v1/alerts | jq '.data | length' 2>/dev/null || echo "0")
        echo "📢 Активных алертов: $alerts"
    else
        echo "⚠️  Alertmanager недоступен"
    fi
    
    echo ""
}

# Проверка выходных файлов
demo_output_files() {
    echo "📁 Проверка выходных файлов"
    echo "---------------------------"
    
    echo "📄 Файлы в директории data/output/:"
    if [ -d "data/output" ]; then
        ls -la data/output/ || echo "   Пусто"
    else
        echo "   Директория не существует"
    fi
    
    echo ""
    echo "📄 Файлы Kafka Connect:"
    if [ -d "data/kafka-connect-data" ]; then
        ls -la data/kafka-connect-data/ || echo "   Пусто"
    else
        echo "   Директория не существует"
    fi
    
    echo ""
    echo "📊 Статистика Kafka топиков:"
    echo "docker exec kafka-broker-1 kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic shop-products"
    
    echo ""
}

# Главная функция демонстрации
main() {
    echo "Начинаем демонстрацию через 3 секунды..."
    sleep 3
    
    check_system
    
    echo "1️⃣  Демонстрация Shop API"
    demo_shop_api
    
    echo "2️⃣  Демонстрация фильтрации"
    demo_filtering
    
    echo "3️⃣  Демонстрация Client API"
    demo_client_api
    
    echo "4️⃣  Демонстрация аналитики"
    demo_analytics
    
    echo "5️⃣  Демонстрация мониторинга"
    demo_monitoring
    
    echo "6️⃣  Проверка файлов"
    demo_output_files
    
    echo "🎉 Демонстрация завершена!"
    echo "========================"
    echo ""
    echo "🔧 Для дальнейшего изучения:"
    echo "• Откройте Grafana: http://localhost:3000"
    echo "• Изучите Kafka топики: docker exec kafka-broker-1 kafka-topics.sh --list --bootstrap-server localhost:9092"
    echo "• Просмотрите логи: docker compose logs -f"
    echo "• Поэкспериментируйте с CLI командами из README.md"
    echo ""
    echo "📝 Для остановки системы: docker compose down"
}

# Обработка ошибок
trap 'echo "❌ Демонстрация прервана"; exit 1' ERR

# Запуск демонстрации
main 