# SSL конфигурация для Kafka Python приложений
import os
from pathlib import Path

# Базовый путь к SSL сертификатам
SSL_BASE_PATH = Path(__file__).parent.parent / "ssl"

def get_ssl_config_simple() -> dict:
    """SSL конфигурация для kafka-python (простой SSL без SASL)"""
    return {
        'security_protocol': 'SSL',
        'ssl_check_hostname': False,
        'ssl_cafile': str(SSL_BASE_PATH / "ca-cert"),
        'ssl_certfile': str(SSL_BASE_PATH / "client-cert-signed"),
        'ssl_keyfile': str(SSL_BASE_PATH / "client-cert-file"),
        'ssl_password': 'kafka-secret'
    }

def get_ssl_config_sasl(username: str, password: str) -> dict:
    """SSL конфигурация для kafka-python с SASL (если потребуется в будущем)"""
    return {
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'SCRAM-SHA-256',
        'sasl_plain_username': username,
        'sasl_plain_password': password,
        'ssl_check_hostname': False,
        'ssl_cafile': str(SSL_BASE_PATH / "ca-cert"),
        'ssl_certfile': str(SSL_BASE_PATH / "client-cert-signed"),
        'ssl_keyfile': str(SSL_BASE_PATH / "client-cert-file"),
        'ssl_password': 'kafka-secret'
    }

# Основная SSL конфигурация (без SASL)
SSL_CONFIG = get_ssl_config_simple()

# Конфигурации для разных сервисов (если понадобится SASL в будущем)
SHOP_API_CONFIG_SASL = get_ssl_config_sasl('shop-api', 'shop-secret')
CLIENT_API_CONFIG_SASL = get_ssl_config_sasl('client-api', 'client-secret')
ANALYTICS_CONFIG_SASL = get_ssl_config_sasl('analytics', 'analytics-secret')
STREAM_PROCESSOR_CONFIG_SASL = get_ssl_config_sasl('stream-processor', 'stream-secret')
FILE_WRITER_CONFIG_SASL = get_ssl_config_sasl('file-writer', 'file-secret')

# Адреса брокеров (исправленные порты согласно docker-compose-secure.yml)
KAFKA_BROKERS_PLAINTEXT = ['localhost:9092', 'localhost:9095', 'localhost:9098']
KAFKA_BROKERS_SSL = ['localhost:9093', 'localhost:9096', 'localhost:9099']

# Основные топики
TOPICS = {
    'shop_products': 'shop-products',
    'filtered_products': 'filtered-products', 
    'client_searches': 'client-searches',
    'client_recommendations': 'client-recommendations',
    'recommendations_results': 'recommendations-results',
    'filtered_events': 'filtered-events',
    'system_metrics': 'system-metrics',
    'error_logs': 'error-logs'
} 