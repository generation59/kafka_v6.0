# Kafka v6.0 - SSL система обработки данных

**Полнофункциональная система на базе Apache Kafka с SSL шифрованием, потоковой обработкой и мониторингом.**

## 🏗️ Архитектура

```
Products → [SSL Kafka] → Banned Filter → [Filtered Products] → File Storage
           ↓                           ↓
      Client API                  Analytics
           ↓                           ↓
    Recommendations         [Monitoring: Prometheus + Grafana]
```

**Компоненты:**
- **3 Kafka брокера** с SSL (порты 9093, 9096, 9099)
- **Stream processor** - фильтрация запрещённых товаров
- **File writer** - сохранение в JSONL
- **Monitoring** - Prometheus + Grafana + Alertmanager

## 🚀 Быстрый старт

### 1. Подготовка
```bash
# Клонирование и setup
git clone <repository>
cd kafka_v6.0
python -m venv kafka_env
source kafka_env/bin/activate  # Linux/WSL
pip install -r requirements.txt

# Генерация SSL сертификатов
./scripts/generate_ssl_certs.sh
./scripts/fix_keystore_format.sh
./scripts/fix_client_certificates.sh
```

### 2. Запуск системы
```bash
# Запуск всех сервисов
docker compose -f docker-compose-secure.yml up -d

# Создание топиков
./scripts/create_topics_secure.sh

# Проверка SSL
python scripts/test_ssl_connection.py
```

### 3. Доступные интерфейсы
- **Grafana**: http://localhost:3000 (admin/grafana)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9394

## 💼 Использование

### Отправка данных
```bash
# Отправка товаров с SSL
python src/shop_api/producer.py --ssl-auto
```

### Фильтрация товаров
```bash
# Запуск фильтра (в отдельном терминале)
python src/stream_processor/banned_filter.py start \
  --brokers "localhost:9092,localhost:9095,localhost:9098"

# Управление чёрным списком
python src/stream_processor/banned_filter.py ban --product-id "12345" --reason "Тест"
python src/stream_processor/banned_filter.py list
python src/stream_processor/banned_filter.py unban --product-id "12345"
```

### Сохранение результатов
```bash
# Запись отфильтрованных данных
python src/file_writer/kafka_to_file.py write \
  --topic filtered-products --output results.jsonl --max-messages 100

# Проверка результатов
cat data/output/results.jsonl | jq '.data | {product_id, name, filter_status}'
```

## 🔧 Конфигурация

### SSL Kafka кластер
| Брокер | PLAINTEXT | SSL | JMX |
|--------|-----------|-----|-----|
| broker-1 | 9092 | 9093 | 9101 |
| broker-2 | 9095 | 9096 | 9102 |
| broker-3 | 9098 | 9099 | 9103 |

### Топики
| Топик | Партиции | Репликация |
|-------|----------|------------|
| shop-products | 3 | 3 |
| filtered-products | 3 | 3 |
| filtered-events | 3 | 3 |

## 📁 Структура проекта

```
kafka_v6.0/
├── src/                      # Исходный код
│   ├── shop_api/            # Producer
│   ├── stream_processor/    # Фильтрация
│   ├── file_writer/         # Запись в файлы
│   └── client_api/          # Consumer
├── data/                    # Данные и результаты
│   ├── products.json        # Исходные товары
│   ├── banned_products.json # Чёрный список
│   └── output/             # Выходные файлы
├── ssl/                     # SSL сертификаты
├── monitoring/              # Prometheus + Grafana
├── scripts/                 # Утилиты
└── docker-compose-secure.yml
```

## 🚨 Troubleshooting

### SSL ошибки
```bash
# Проверка и перегенерация сертификатов
python scripts/test_ssl_connection.py
./scripts/generate_ssl_certs.sh
./scripts/fix_keystore_format.sh
```

### Kafka недоступен
```bash
# Проверка статуса
docker ps
docker logs kafka-broker-1

# Перезапуск
docker compose -f docker-compose-secure.yml down
docker compose -f docker-compose-secure.yml up -d
```

### Проблемы с топиками
```bash
# Проверка топиков
docker exec kafka-broker-1 kafka-topics --bootstrap-server localhost:19092 --list

# Создание вручную
docker exec kafka-broker-1 kafka-topics --bootstrap-server localhost:19092 \
  --create --topic shop-products --partitions 3 --replication-factor 3
```

## 🎯 Полный цикл работы

```bash
# 1. Запуск системы
docker compose -f docker-compose-secure.yml up -d

# 2. Запуск фильтра (терминал 1)
python src/stream_processor/banned_filter.py start --brokers "localhost:9092,localhost:9095,localhost:9098"

# 3. Отправка данных (терминал 2)  
python src/shop_api/producer.py --ssl-auto

# 4. Запись результатов (терминал 3)
python src/file_writer/kafka_to_file.py write --topic filtered-products --output results.jsonl

# 5. Проверка в Grafana
open http://localhost:3000
```

---

**Система готова к работе!** 🚀 SSL кластер + фильтрация + мониторинг + файловое хранение.

