#!/usr/bin/env python3
"""
Скрипт для диагностики SSL подключения к Kafka в WSL
"""
import os
import sys
import ssl
import socket
import logging
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.append(str(Path(__file__).parent.parent))

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_ssl_files():
    """Проверка доступности SSL файлов"""
    ssl_dir = Path(__file__).parent.parent / "ssl"
    logger.info(f"Проверка SSL директории: {ssl_dir}")
    
    required_files = [
        "ca-cert",
        "client-cert-signed", 
        "client-cert-file",
        "kafka.client.keystore.jks",
        "kafka.client.truststore.jks"
    ]
    
    issues = []
    
    if not ssl_dir.exists():
        issues.append(f"SSL директория не существует: {ssl_dir}")
        return issues
    
    for file_name in required_files:
        file_path = ssl_dir / file_name
        if not file_path.exists():
            issues.append(f"Файл не найден: {file_path}")
        else:
            # Проверяем права доступа
            try:
                with open(file_path, 'rb') as f:
                    f.read(1)
                logger.info(f"✅ Файл доступен: {file_path}")
            except PermissionError:
                issues.append(f"Нет прав доступа к файлу: {file_path}")
            except Exception as e:
                issues.append(f"Ошибка чтения файла {file_path}: {e}")
    
    return issues

def test_tcp_connection(host: str, port: int):
    """Тест TCP подключения"""
    logger.info(f"Тестирование TCP подключения к {host}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"✅ TCP подключение к {host}:{port} успешно")
            return True
        else:
            logger.error(f"❌ TCP подключение к {host}:{port} не удалось")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка TCP подключения к {host}:{port}: {e}")
        return False

def test_ssl_connection(host: str, port: int):
    """Тест SSL рукопожатия"""
    logger.info(f"Тестирование SSL подключения к {host}:{port}")
    try:
        # Создаем SSL контекст
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Подключаемся
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                logger.info(f"✅ SSL подключение к {host}:{port} успешно")
                logger.info(f"SSL версия: {ssock.version()}")
                logger.info(f"Cipher: {ssock.cipher()}")
                return True
    except Exception as e:
        logger.error(f"❌ SSL подключение к {host}:{port} не удалось: {e}")
        return False

def test_kafka_ssl():
    """Тест подключения к Kafka с SSL"""
    try:
        from config.kafka_ssl_config import SSL_CONFIG, KAFKA_BROKERS_SSL
        
        logger.info("Тестирование Kafka SSL подключения...")
        
        # Берем первый брокер
        broker = KAFKA_BROKERS_SSL[0]
        host, port = broker.split(':')
        port = int(port)
        
        logger.info(f"Тестируем брокер: {broker}")
        logger.info(f"SSL конфигурация: {SSL_CONFIG}")
        
        # Тест TCP подключения
        if not test_tcp_connection(host, port):
            return False
        
        # Тест SSL рукопожатия
        if not test_ssl_connection(host, port):
            return False
        
        # Тест Kafka producer
        logger.info("Тестирование Kafka Producer...")
        producer_config = {
            'bootstrap_servers': [broker],
            'value_serializer': lambda v: str(v).encode('utf-8'),
            'request_timeout_ms': 10000,
            'retries': 1
        }
        producer_config.update(SSL_CONFIG)
        
        producer = KafkaProducer(**producer_config)
        
        # Получаем метаданные (это проверит подключение)
        metadata = producer.partitions_for("test-topic")
        logger.info(f"✅ Kafka SSL подключение успешно! Метаданные получены: {metadata}")
        
        producer.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Kafka SSL подключение не удалось: {e}")
        return False

def main():
    """Основная функция диагностики"""
    logger.info("🔍 Начинаем диагностику SSL подключения к Kafka в WSL")
    logger.info("=" * 60)
    
    # 1. Проверяем SSL файлы
    logger.info("1️⃣ Проверка SSL файлов...")
    ssl_issues = check_ssl_files()
    if ssl_issues:
        logger.error("❌ Проблемы с SSL файлами:")
        for issue in ssl_issues:
            logger.error(f"  - {issue}")
        return
    else:
        logger.info("✅ Все SSL файлы найдены и доступны")
    
    # 2. Проверяем сервисы Docker
    logger.info("\n2️⃣ Проверка Docker сервисов...")
    import subprocess
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=kafka'], 
                              capture_output=True, text=True)
        if 'kafka-broker' in result.stdout:
            logger.info("✅ Kafka контейнеры запущены")
            logger.info(result.stdout)
        else:
            logger.error("❌ Kafka контейнеры не найдены")
            logger.info("Попробуйте запустить: docker compose -f docker-compose-secure.yml up -d")
            return
    except Exception as e:
        logger.error(f"❌ Ошибка проверки Docker: {e}")
    
    # 3. Тестируем Kafka SSL
    logger.info("\n3️⃣ Тест Kafka SSL подключения...")
    if test_kafka_ssl():
        logger.info("🎉 SSL подключение к Kafka работает!")
    else:
        logger.error("😞 SSL подключение к Kafka не работает")
        
        # Дополнительные советы для WSL
        logger.info("\n💡 Советы для решения проблем в WSL:")
        logger.info("1. Убедитесь, что Docker Desktop запущен")
        logger.info("2. Проверьте права доступа к SSL файлам:")
        logger.info("   chmod 644 ssl/*.jks ssl/*.properties ssl/ca-cert ssl/*-cert-*")
        logger.info("3. Перезапустите Kafka с SSL:")
        logger.info("   docker compose -f docker-compose-secure.yml down")
        logger.info("   docker compose -f docker-compose-secure.yml up -d")
        logger.info("4. Проверьте логи контейнеров:")
        logger.info("   docker logs kafka-broker-1")

if __name__ == '__main__':
    main() 