#!/bin/bash
# Исправление клиентских сертификатов для правильной работы с kafka-python

echo "🔧 Исправление клиентских сертификатов..."

cd ssl

KEYSTORE_PASSWORD="kafka-secret"

# Экспортируем клиентский сертификат и ключ в правильном PEM формате из JKS keystore
echo "🔧 Экспорт клиентского сертификата из JKS keystore..."

# Экспортируем сертификат
keytool -export -alias localhost -keystore kafka.client.keystore.jks \
    -storepass $KEYSTORE_PASSWORD -file client-cert.der

# Конвертируем в PEM
openssl x509 -inform DER -in client-cert.der -out client-cert-signed -outform PEM

# Экспортируем приватный ключ из keystore (через PKCS12)
echo "🔧 Экспорт приватного ключа..."

# Конвертируем JKS в PKCS12
keytool -importkeystore -srckeystore kafka.client.keystore.jks -destkeystore client-temp.p12 \
    -srcstoretype JKS -deststoretype PKCS12 \
    -srcstorepass $KEYSTORE_PASSWORD -deststorepass $KEYSTORE_PASSWORD \
    -srcalias localhost -destalias localhost \
    -srckeypass $KEYSTORE_PASSWORD -destkeypass $KEYSTORE_PASSWORD -noprompt

# Экспортируем приватный ключ в PEM
openssl pkcs12 -in client-temp.p12 -nocerts -out client-cert-file \
    -passin pass:$KEYSTORE_PASSWORD -passout pass:$KEYSTORE_PASSWORD

# Удаляем временные файлы
rm -f client-cert.der client-temp.p12

echo "✅ Клиентские сертификаты пересозданы в PEM формате"
echo "🔍 Проверка сертификатов:"
echo "CA сертификат:"
openssl x509 -in ca-cert -text -noout | head -3
echo ""
echo "Клиентский сертификат:"
openssl x509 -in client-cert-signed -text -noout | head -3
echo ""
echo "Приватный ключ:"
openssl rsa -in client-cert-file -text -noout -passin pass:$KEYSTORE_PASSWORD | head -3

cd .. 