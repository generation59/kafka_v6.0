#!/bin/bash
# Исправление формата keystore для Confluent Platform

echo "🔧 Исправление формата keystore для Confluent Platform..."

cd ssl

KEYSTORE_PASSWORD="kafka-secret"
KEY_PASSWORD="kafka-secret"

# Удаляем старые keystore файлы
rm -f kafka-broker-*.server.keystore.jks kafka.client.keystore.jks

# Пересоздаем keystore для каждого брокера в JKS формате
for i in 1 2 3; do
    echo "🔧 Пересоздание keystore для kafka-broker-$i в JKS формате..."
    
    # Создаем keystore в JKS формате (добавляем -storetype JKS)
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias localhost -validity 365 -genkey \
        -keyalg RSA -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD \
        -dname "CN=kafka-broker-$i,OU=Security,O=Marketplace,L=Moscow,S=Russia,C=RU" \
        -ext SAN=DNS:kafka-broker-$i,DNS:localhost,IP:127.0.0.1 \
        -storetype JKS

    # Создаем certificate signing request
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias localhost -certreq -file cert-file-$i \
        -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD -storetype JKS

    # Подписываем сертификат с помощью CA
    openssl x509 -req -CA ca-cert -CAkey ca-key -in cert-file-$i -out cert-signed-$i \
        -days 365 -CAcreateserial -passin pass:$KEYSTORE_PASSWORD

    # Импортируем CA сертификат в keystore
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias CARoot -import -file ca-cert \
        -storepass $KEYSTORE_PASSWORD -noprompt -storetype JKS

    # Импортируем подписанный сертификат в keystore
    keytool -keystore kafka-broker-$i.server.keystore.jks -alias localhost -import -file cert-signed-$i \
        -storepass $KEYSTORE_PASSWORD -noprompt -storetype JKS
done

# Пересоздаем client keystore в JKS формате
echo "🔧 Пересоздание client keystore в JKS формате..."
keytool -keystore kafka.client.keystore.jks -alias localhost -validity 365 -genkey \
    -keyalg RSA -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD \
    -dname "CN=kafka-client,OU=Security,O=Marketplace,L=Moscow,S=Russia,C=RU" \
    -storetype JKS

keytool -keystore kafka.client.keystore.jks -alias localhost -certreq -file client-cert-file \
    -storepass $KEYSTORE_PASSWORD -keypass $KEY_PASSWORD -storetype JKS

openssl x509 -req -CA ca-cert -CAkey ca-key -in client-cert-file -out client-cert-signed \
    -days 365 -CAcreateserial -passin pass:$KEYSTORE_PASSWORD

keytool -keystore kafka.client.keystore.jks -alias CARoot -import -file ca-cert \
    -storepass $KEYSTORE_PASSWORD -noprompt -storetype JKS

keytool -keystore kafka.client.keystore.jks -alias localhost -import -file client-cert-signed \
    -storepass $KEYSTORE_PASSWORD -noprompt -storetype JKS

cd ..

echo "✅ Keystore пересозданы в JKS формате"
echo "🔍 Проверка формата:"
for i in 1 2 3; do
    echo "kafka-broker-$i keystore:"
    keytool -list -keystore ssl/kafka-broker-$i.server.keystore.jks -storepass $KEYSTORE_PASSWORD | head -3
done 