"""
Shop API Producer - отправляет товары из файла в Kafka
"""
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import os
import sys

from kafka import KafkaProducer
from kafka.errors import KafkaError
import click

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем корневую директорию в path для импорта конфигурации
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from config.kafka_ssl_config import SSL_CONFIG, KAFKA_BROKERS_SSL, KAFKA_BROKERS_PLAINTEXT
    SSL_AVAILABLE = True
except ImportError:
    logger.warning("SSL конфигурация недоступна, используется только PLAINTEXT")
    SSL_AVAILABLE = False


class ShopAPIProducer:
    """Класс для отправки товаров магазинов в Kafka"""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092', 
                 topic: str = 'shop-products', use_ssl: bool = False):
        """
        Инициализация продюсера
        
        Args:
            bootstrap_servers: Адреса Kafka брокеров
            topic: Топик для отправки данных
            use_ssl: Использовать SSL подключение
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.use_ssl = use_ssl
        self.producer = None
        
    def connect(self):
        """Подключение к Kafka"""
        try:
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                'key_serializer': lambda k: str(k).encode('utf-8'),
                'retries': 3,
                'acks': 'all',  # Ждем подтверждения от всех реплик
                'request_timeout_ms': 30000,
                'retry_backoff_ms': 100
            }
            
            # Добавляем SSL конфигурацию если требуется
            if self.use_ssl:
                if not SSL_AVAILABLE:
                    logger.error("SSL конфигурация недоступна")
                    return False
                producer_config.update(SSL_CONFIG)
                logger.info(f"Подключение к Kafka с SSL: {self.bootstrap_servers}")
            else:
                logger.info(f"Подключение к Kafka без SSL: {self.bootstrap_servers}")
            
            self.producer = KafkaProducer(**producer_config)
            logger.info("Подключение к Kafka успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Kafka: {e}")
            return False
    
    def load_products_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Загрузка товаров из JSON файла
        
        Args:
            file_path: Путь к файлу с товарами
            
        Returns:
            Список товаров
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                products = json.load(f)
            logger.info(f"Загружено {len(products)} товаров из {file_path}")
            return products
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_path}: {e}")
            return []
    
    def send_product(self, product: Dict[str, Any]) -> bool:
        """
        Отправка одного товара в Kafka
        
        Args:
            product: Данные товара
            
        Returns:
            True если отправка успешна, False иначе
        """
        if not self.producer:
            logger.error("Продюсер не инициализирован")
            return False
            
        try:
            # Добавляем timestamp отправки
            product_data = product.copy()
            product_data['kafka_sent_at'] = datetime.utcnow().isoformat()
            
            # Отправляем с ключом product_id для партиционирования
            future = self.producer.send(
                self.topic,
                key=product_data.get('product_id'),
                value=product_data
            )
            
            # Ждем подтверждения отправки
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Товар {product_data.get('product_id')} отправлен в топик {record_metadata.topic}, "
                f"партиция {record_metadata.partition}, offset {record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Ошибка отправки в Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке: {e}")
            return False
    
    def send_products_from_file(self, file_path: str, delay_seconds: float = 1.0) -> int:
        """
        Отправка всех товаров из файла
        
        Args:
            file_path: Путь к файлу с товарами
            delay_seconds: Задержка между отправками
            
        Returns:
            Количество успешно отправленных товаров
        """
        products = self.load_products_from_file(file_path)
        if not products:
            return 0
            
        success_count = 0
        
        for i, product in enumerate(products, 1):
            logger.info(f"Отправка товара {i}/{len(products)}: {product.get('name', 'Unknown')}")
            
            if self.send_product(product):
                success_count += 1
            
            # Задержка между отправками
            if i < len(products):
                time.sleep(delay_seconds)
        
        logger.info(f"Отправлено {success_count} из {len(products)} товаров")
        return success_count
    
    def close(self):
        """Закрытие соединения с Kafka"""
        if self.producer:
            self.producer.flush()  # Дожидаемся отправки всех сообщений
            self.producer.close()
            logger.info("Соединение с Kafka закрыто")


@click.command()
@click.option('--file', '-f', default='data/products.json', 
              help='Путь к файлу с товарами')
@click.option('--topic', '-t', default='shop-products',
              help='Kafka топик для отправки')
@click.option('--brokers', '-b', default='localhost:9092',
              help='Адреса Kafka брокеров')
@click.option('--delay', '-d', default=1.0, type=float,
              help='Задержка между отправками в секундах')
@click.option('--continuous', '-c', is_flag=True,
              help='Непрерывная отправка (циклично)')
@click.option('--ssl', is_flag=True,
              help='Использовать SSL подключение')
@click.option('--ssl-auto', is_flag=True,
              help='Автоматически использовать SSL брокеры из конфигурации')
def main(file: str, topic: str, brokers: str, delay: float, continuous: bool, 
         ssl: bool, ssl_auto: bool):
    """Shop API Producer - отправка товаров в Kafka"""
    
    # Определяем конфигурацию подключения
    use_ssl = ssl or ssl_auto
    
    if ssl_auto and SSL_AVAILABLE:
        brokers = ','.join(KAFKA_BROKERS_SSL)
        logger.info(f"Автоматический выбор SSL брокеров: {brokers}")
    elif ssl_auto and not SSL_AVAILABLE:
        logger.warning("SSL конфигурация недоступна, используем PLAINTEXT брокеры")
        if SSL_AVAILABLE:
            brokers = ','.join(KAFKA_BROKERS_PLAINTEXT)
        use_ssl = False
    
    producer = ShopAPIProducer(bootstrap_servers=brokers, topic=topic, use_ssl=use_ssl)
    
    if not producer.connect():
        logger.error("Не удалось подключиться к Kafka")
        return
    
    try:
        if continuous:
            logger.info("Запуск в режиме непрерывной отправки. Для остановки нажмите Ctrl+C")
            while True:
                sent_count = producer.send_products_from_file(file, delay)
                if sent_count == 0:
                    logger.warning("Не удалось отправить товары, повтор через 30 секунд")
                    time.sleep(30)
                else:
                    logger.info("Цикл завершен, повтор через 60 секунд")
                    time.sleep(60)
        else:
            producer.send_products_from_file(file, delay)
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        producer.close()


if __name__ == '__main__':
    main() 