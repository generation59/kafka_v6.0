#!/bin/bash
# Скрипт для исправления прав доступа к SSL файлам в WSL

echo "🔧 Исправление прав доступа к SSL файлам для WSL..."

SSL_DIR="ssl"

if [ ! -d "$SSL_DIR" ]; then
    echo "❌ Директория ssl/ не найдена. Сначала создайте SSL сертификаты:"
    echo "   ./scripts/generate_ssl_certs.sh"
    exit 1
fi

cd "$SSL_DIR"

echo "📁 Исправляем права доступа к файлам..."

# Права для сертификатов и ключей
chmod 644 *.jks 2>/dev/null || echo "⚠️ JKS файлы не найдены"
chmod 644 *.properties 2>/dev/null || echo "⚠️ Properties файлы не найдены"
chmod 644 ca-cert 2>/dev/null || echo "⚠️ CA сертификат не найден"
chmod 600 ca-key 2>/dev/null || echo "⚠️ CA ключ не найден"
chmod 644 *-cert-* 2>/dev/null || echo "⚠️ Клиентские сертификаты не найдены"

# Права для директории
chmod 755 .

cd ..

echo "✅ Права доступа исправлены!"

echo ""
echo "📋 Текущие права доступа:"
ls -la ssl/ | head -10

echo ""
echo "🔍 Проверка SSL файлов:"
python3 scripts/test_ssl_connection.py 