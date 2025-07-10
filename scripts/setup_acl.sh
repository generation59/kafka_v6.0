#!/bin/bash
# Настройка ACL правил для Kafka кластера

echo "🔐 Настройка ACL правил для Kafka..."

# Переменные
KAFKA_BROKER="localhost:9093"
SSL_CONFIG="ssl/client-ssl.properties"

# Функция для создания ACL
create_acl() {
    local user=$1
    local topic=$2
    local operation=$3
    local resource_type=${4:-"topic"}
    
    echo "Создание ACL: User:$user -> $operation на $resource_type:$topic"
    
    docker exec kafka-broker-1 kafka-acls \
        --bootstrap-server $KAFKA_BROKER \
        --command-config /etc/kafka/secrets/client-ssl.properties \
        --add \
        --allow-principal User:$user \
        --operation $operation \
        --$resource_type $topic
}

# Функция для создания группового ACL
create_group_acl() {
    local user=$1
    local group=$2
    local operation=$3
    
    echo "Создание Group ACL: User:$user -> $operation на группу:$group"
    
    docker exec kafka-broker-1 kafka-acls \
        --bootstrap-server $KAFKA_BROKER \
        --command-config /etc/kafka/secrets/client-ssl.properties \
        --add \
        --allow-principal User:$user \
        --operation $operation \
        --group $group
}

echo "1️⃣  Настройка прав для admin пользователя..."
# Admin имеет полные права
create_acl "admin" "*" "All" "topic"
create_acl "admin" "*" "All" "cluster"
create_group_acl "admin" "*" "All"

echo "2️⃣  Настройка прав для shop-api..."
# Shop API - может писать в топики товаров
create_acl "shop-api" "shop-products" "Write"
create_acl "shop-api" "shop-products" "Describe"
create_acl "shop-api" "shop-products" "Create"

echo "3️⃣  Настройка прав для client-api..."
# Client API - может писать в поисковые топики и читать рекомендации
create_acl "client-api" "client-searches" "Write"
create_acl "client-api" "client-searches" "Describe"
create_acl "client-api" "client-recommendations" "Write"
create_acl "client-api" "client-recommendations" "Describe"
create_acl "client-api" "recommendations-results" "Read"
create_acl "client-api" "recommendations-results" "Describe"
create_group_acl "client-api" "client-*" "Read"

echo "4️⃣  Настройка прав для analytics..."
# Analytics - может читать все топики и писать результаты
create_acl "analytics" "shop-products" "Read"
create_acl "analytics" "filtered-products" "Read"
create_acl "analytics" "client-searches" "Read"
create_acl "analytics" "client-recommendations" "Read"
create_acl "analytics" "recommendations-results" "Write"
create_acl "analytics" "recommendations-results" "Describe"
create_acl "analytics" "*" "Describe"
create_group_acl "analytics" "analytics-*" "All"

echo "5️⃣  Настройка прав для stream processing..."
# Stream processor - читает и фильтрует товары
create_acl "stream-processor" "shop-products" "Read"
create_acl "stream-processor" "filtered-products" "Write"
create_acl "stream-processor" "filtered-events" "Write"
create_acl "stream-processor" "*" "Describe"
create_group_acl "stream-processor" "stream-*" "All"

echo "6️⃣  Настройка прав для file-writer..."
# File writer - читает данные для записи в файлы
create_acl "file-writer" "*" "Read"
create_acl "file-writer" "*" "Describe"
create_group_acl "file-writer" "file-writer-*" "Read"

echo "7️⃣  Настройка служебных топиков..."
# Служебные топики для всех пользователей
for user in "shop-api" "client-api" "analytics" "stream-processor" "file-writer"; do
    create_acl "$user" "__consumer_offsets" "Read"
    create_acl "$user" "__consumer_offsets" "Describe"
    create_acl "$user" "__transaction_state" "Read"
    create_acl "$user" "__transaction_state" "Describe"
done

echo "8️⃣  Проверка созданных ACL..."
docker exec kafka-broker-1 kafka-acls \
    --bootstrap-server $KAFKA_BROKER \
    --command-config /etc/kafka/secrets/client-ssl.properties \
    --list

echo "✅ ACL правила настроены!"
echo ""
echo "🔑 Пользователи и пароли:"
echo "admin: admin-secret"
echo "shop-api: shop-secret"
echo "client-api: client-secret"
echo "analytics: analytics-secret" 