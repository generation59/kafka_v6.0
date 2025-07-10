#!/bin/bash
# Генерация SSL сертификатов для Kafka кластера

echo "🔐 Генерация SSL сертификатов для Kafka..."

# Создаем директорию для сертификатов
mkdir -p ssl
cd ssl

# Переменные
CLUSTER_NAME="kafka-cluster"
VALIDITY_DAYS=365
KEYSTORE_PASSWORD="kafka-secret"
TRUSTSTORE_PASSWORD="kafka-secret"
KEY_PASSWORD="kafka-secret"

# 1. Создаем Certificate Authority (CA)
echo "1️⃣  Создание Certificate Authority..."
openssl req -new -x509 -keyout ca-key -out ca-cert -days $VALIDITY_DAYS -subj "/CN=Kafka-Security-CA" -passin pass:$KEYSTORE_PASSWORD -passout pass:$KEYSTORE_PASSWORD

# 2. Создаем keystore для каждого брокера
for i in 1 2 3; do
    echo "2️⃣  Создание keystore для kafka-broker-$i..."
    
    # Создаем keystore
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias localhost -validity $VALIDITY_DAYS -genkey \
        -keyalg RSA -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD \
        -dname "CN=kafka-broker-$i,OU=Security,O=Marketplace,L=Moscow,S=Russia,C=RU" \
        -ext SAN=DNS:kafka-broker-$i,DNS:localhost,IP:127.0.0.1

    # Создаем certificate signing request
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias localhost -certreq -file cert-file-$i \
        -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD

    # Подписываем сертификат с помощью CA
    openssl x509 -req -CA ca-cert -CAkey ca-key -in cert-file-$i -out cert-signed-$i \
        -days $VALIDITY_DAYS -CAcreateserial -passin pass:$KEYSTORE_PASSWORD

    # Импортируем CA сертификат в keystore
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias CARoot -import -file ca-cert \
        -storepass $KEYSTORE_PASSWORD -noprompt

    # Импортируем подписанный сертификат в keystore
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias localhost -import -file cert-signed-$i \
        -storepass $KEYSTORE_PASSWORD -noprompt
done

# 3. Создаем общий truststore
echo "3️⃣  Создание truststore..."
keytool -keystore kafka.server.truststore.jks -alias CARoot -import -file ca-cert \
    -storepass $TRUSTSTORE_PASSWORD -noprompt

# 4. Создаем client keystore и truststore
echo "4️⃣  Создание client сертификатов..."
keytool -keystore kafka.client.keystore.jks -alias localhost -validity $VALIDITY_DAYS -genkey \
    -keyalg RSA -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD \
    -dname "CN=kafka-client,OU=Security,O=Marketplace,L=Moscow,S=Russia,C=RU"

keytool -keystore kafka.client.keystore.jks -alias localhost -certreq -file client-cert-file \
    -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD

openssl x509 -req -CA ca-cert -CAkey ca-key -in client-cert-file -out client-cert-signed \
    -days $VALIDITY_DAYS -CAcreateserial -passin pass:$KEYSTORE_PASSWORD

keytool -keystore kafka.client.keystore.jks -alias CARoot -import -file ca-cert \
    -storepass $KEYSTORE_PASSWORD -noprompt

keytool -keystore kafka.client.keystore.jks -alias localhost -import -file client-cert-signed \
    -storepass $KEYSTORE_PASSWORD -noprompt

# Копируем truststore для клиента
cp kafka.server.truststore.jks kafka.client.truststore.jks

# 5. Создаем файл паролей
echo "5️⃣  Создание файла паролей..."
cat > ssl-passwords.properties << EOF
# SSL Passwords
keystore.password=$KEYSTORE_PASSWORD
truststore.password=$TRUSTSTORE_PASSWORD
key.password=$KEY_PASSWORD
EOF

# 6. Создаем клиентские конфигурации
echo "6️⃣  Создание клиентских конфигураций..."
cat > client-ssl.properties << EOF
security.protocol=SSL
ssl.truststore.location=/opt/kafka/ssl/kafka.client.truststore.jks
ssl.truststore.password=$TRUSTSTORE_PASSWORD
ssl.keystore.location=/opt/kafka/ssl/kafka.client.keystore.jks
ssl.keystore.password=$KEYSTORE_PASSWORD
ssl.key.password=$KEY_PASSWORD
ssl.endpoint.identification.algorithm=
EOF

cd ..

echo "✅ SSL сертификаты созданы в директории ssl/"
echo "📋 Файлы:"
ls -la ssl/

echo ""
echo "🔑 Пароли:"
echo "Keystore Password: $KEYSTORE_PASSWORD"
echo "Truststore Password: $TRUSTSTORE_PASSWORD"
echo "Key Password: $KEY_PASSWORD" 