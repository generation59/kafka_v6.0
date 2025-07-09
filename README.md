# Аналитическая платформа для маркетплейса

Комплексная система для обработки данных маркетплейса в реальном времени с использованием Apache Kafka, Spark, файлового поиска и системы мониторинга.

## 📋 Описание проекта

Система состоит из следующих компонентов:

### 🏪 SHOP API
- Эмуляция магазинов, отправляющих товары в Kafka
- Чтение данных из JSON файла
- Отправка товаров в топик `shop-products`

### 👥 CLIENT API  
- Интерфейс для клиентов маркетплейса
- Поиск товаров (файловый поиск)
- Запрос персонализированных рекомендаций
- Отправка событий в Kafka для аналитики

### 🔍 Stream Processor
- Потоковая фильтрация запрещённых товаров
- Управление черным списком через CLI
- Обработка данных в реальном времени

### 📊 Analytics System
- Apache Spark для аналитической обработки
- Генерация персонализированных рекомендаций
- Статистика по товарам и категориям

### 💾 Storage
- Файловый поиск товаров
- Kafka Connect для записи в файлы
- Файловое хранилище как fallback

### 📈 Monitoring
- Prometheus для сбора метрик
- Grafana для визуализации
- Alertmanager для уведомлений

## 🏗️ Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Shop API      │    │  Client API     │    │ Stream Filter   │
│   (Producer)    │───▶│  (Consumer/     │    │ (Kafka Streams) │
│                 │    │   Producer)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Apache Kafka Cluster                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐         │
│  │ Broker 1:9092 │ │ Broker 2:9093 │ │ Broker 3:9094 │         │
│  └───────────────┘ └───────────────┘ └───────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Spark Analytics │    │  Kafka Connect  │    │ File Search     │
│ (Recommendations│    │  (File Sink)    │    │ (Search Index)  │
│  & Statistics)  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   File Storage  │
                       │ (products.json) │
                       └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Monitoring Stack                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │ Prometheus  │ │   Grafana   │ │Alertmanager │              │
│  │   :9090     │ │    :3000    │ │    :9093    │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Быстрый старт

### Системные требования

- Docker с Docker Compose (v2)
- Python 3.8+
- 8GB RAM (рекомендуется 16GB)
- 10GB свободного места на диске

### 1. Клонирование проекта

```bash
git clone <repository-url>
cd kafka_v6.0
```

### 2. Установка Python зависимостей

```bash
pip install -r requirements.txt
```

### 3. Запуск системы

#### Linux/macOS:
```bash
# Сделать скрипт исполняемым
chmod +x scripts/start_system.sh

# Запуск всей системы
./scripts/start_system.sh
```

#### Windows (PowerShell):
```powershell
# Запуск PowerShell скрипта
.\scripts\start_system.ps1
```

#### Альтернативный способ (любая ОС):
```bash
# Ручной запуск через Docker Compose
docker compose up -d
```

### 4. Проверка запуска

После запуска будут доступны следующие веб-интерфейсы:

- **Grafana**: http://localhost:3000 (admin/grafana)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093  
- **Spark Master**: http://localhost:8080
- **Kafka Connect**: http://localhost:8083

## 🛠️ Использование

### Shop API - Отправка товаров

```bash
# Отправка товаров из файла (однократно)
python -m src.shop_api.producer

# Непрерывная отправка
python -m src.shop_api.producer --continuous

# С пользовательскими параметрами
python -m src.shop_api.producer --file data/products.json --topic shop-products --delay 2.0
```

### Client API - Поиск и рекомендации

```bash
# Поиск товаров
python -m src.client_api.client search "умные часы"
python -m src.client_api.client search "смартфон" --limit 5

# Запрос рекомендаций
python -m src.client_api.client recommendations --category "Электроника" --max-price 50000

# Запрос с ожиданием результата
python -m src.client_api.client recommendations --category "Электроника" --wait

# Проверка статуса подключений
python -m src.client_api.client status
```

### Stream Processor - Управление запрещёнными товарами

```bash
# Запуск фильтрации
python -m src.stream_processor.banned_filter start

# Добавление товара в чёрный список
python -m src.stream_processor.banned_filter ban --product-id "12345" --reason "Нарушение правил"

# Добавление по SKU
python -m src.stream_processor.banned_filter ban --sku "FAKE-PRODUCT-123" --reason "Подделка"

# Просмотр списка запрещённых товаров
python -m src.stream_processor.banned_filter list

# Удаление из чёрного списка
python -m src.stream_processor.banned_filter unban --product-id "12345"
```

### Analytics - Аналитическая обработка

```bash
# Запуск аналитической системы
python -m src.analytics.spark_analytics start

# Тестирование рекомендаций
python -m src.analytics.spark_analytics test-recommendations user123 --category "Электроника" --max-price 30000
```

## 📊 Kafka Топики

| Топик | Описание | Партиции | Репликация |
|-------|----------|----------|------------|
| `shop-products` | Товары от магазинов | 6 | 3 |
| `filtered-products` | Отфильтрованные товары | 6 | 3 |
| `filtered-events` | События фильтрации | 3 | 3 |
| `client-searches` | Поисковые запросы | 3 | 3 |
| `client-recommendations` | Запросы рекомендаций | 3 | 3 |
| `recommendations-results` | Результаты рекомендаций | 3 | 3 |

## 📈 Мониторинг и алерты

### Prometheus метрики

Система собирает метрики с:
- Kafka брокеров (JMX)
- Spark Master/Worker
- Пользовательских приложений

### Grafana дашборды

- Kafka Cluster состояние
- Producer/Consumer метрики
- Spark задания
- Системные ресурсы

### Alertmanager уведомления

Настроены алерты для:
- Падение Kafka брокеров
- Высокая задержка репликации
- Ошибки в Spark заданиях
- Высокое потребление ресурсов

## 🔧 Конфигурация

### Kafka

- **Репликация**: 3 брокера с `min.insync.replicas=2`
- **Отказоустойчивость**: Автоматическое переключение лидеров
- **Безопасность**: TLS отключен для упрощения (можно включить)



### Spark

- **Master**: 1 мастер-узел
- **Workers**: 1 воркер (можно масштабировать)
- **Streaming**: Обработка батчами каждые 10-30 секунд

## 🔍 Отладка

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис  
docker compose logs -f kafka-broker-1

# Python приложения
python -m src.shop_api.producer 2>&1 | tee logs/shop_api.log
```

### Просмотр Kafka топиков

```bash
# Список топиков
docker exec kafka-broker-1 kafka-topics.sh --bootstrap-server localhost:9092 --list

# Содержимое топика
docker exec kafka-broker-1 kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic shop-products --from-beginning

# Статистика топика
docker exec kafka-broker-1 kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic shop-products
```

### Проверка Kafka Connect

```bash
# Статус коннекторов
curl http://localhost:8083/connectors

# Детали коннектора
curl http://localhost:8083/connectors/file-sink-products/status
```

## 🐛 Решение проблем

### Kafka не запускается

1. Проверьте доступность портов: `netstat -an | grep 9092`
2. Увеличьте память для Docker
3. Очистите volumes: `docker compose down -v`



### Spark задания не запускаются

1. Проверьте Spark Master UI: http://localhost:8080
2. Убедитесь в доступности Kafka
3. Проверьте пути к JAR файлам

### Python приложения не подключаются

1. Проверьте, что Kafka запущен: `nc -z localhost 9092`
2. Убедитесь в правильности bootstrap серверов
3. Проверьте топики: `docker exec kafka-broker-1 kafka-topics.sh --list --bootstrap-server localhost:9092`

## 📝 Структура проекта

```
kafka_v6.0/
├── src/
│   ├── shop_api/           # Shop API (Producer)
│   ├── client_api/         # Client API (Consumer/Producer)
│   ├── stream_processor/   # Stream processing
│   └── analytics/          # Spark analytics
├── data/
│   ├── products.json       # Тестовые данные товаров
│   ├── banned_products.json # Чёрный список
│   └── output/            # Выходные файлы
├── monitoring/
│   ├── prometheus/        # Конфигурация Prometheus
│   ├── grafana/          # Дашборды Grafana
│   └── alertmanager/     # Конфигурация алертов
├── scripts/
│   ├── start_system.sh   # Запуск системы
│   └── setup_kafka_topics.sh # Создание топиков
├── config/
│   └── file-sink-connector.json # Kafka Connect
├── docker-compose.yml    # Docker Compose конфигурация
├── requirements.txt      # Python зависимости
└── README.md            # Документация
```

## 🔒 Безопасность

В текущей версии для упрощения:
- TLS отключен
- Аутентификация отключена
- ACL не настроены

Для продакшена рекомендуется:
- Включить TLS для Kafka
- Настроить SASL аутентификацию
- Настроить ACL для топиков
- Использовать secrets для паролей

## 🚀 Масштабирование

### Горизонтальное масштабирование

1. **Kafka**: Добавление брокеров в docker-compose.yml
2. **Spark**: Увеличение количества workers
3. **Приложения**: Запуск нескольких инстансов

### Вертикальное масштабирование

1. Увеличение памяти для JVM
2. Больше CPU cores для Spark
3. SSD диски для Kafka/Elasticsearch

## 📊 Производительность

### Рекомендуемые настройки

| Компонент | CPU | RAM | Диск |
|-----------|-----|-----|------|
| Kafka (3 брокера) | 6 cores | 12GB | 100GB SSD |
| Spark | 4 cores | 8GB | 50GB |
| Monitoring | 2 cores | 4GB | 20GB |

### Бенчмарки

- **Throughput**: ~10,000 сообщений/сек на товары
- **Latency**: <100ms для поиска
- **Storage**: ~1GB на 100,000 товаров
