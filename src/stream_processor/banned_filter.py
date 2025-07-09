"""
Потоковая обработка для фильтрации запрещённых товаров
Использует Kafka Streams для обработки данных в реальном времени
"""
import json
import logging
import threading
import time
from typing import Dict, List, Set, Any
from pathlib import Path

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import click

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BannedProductFilter:
    """Класс для фильтрации запрещённых товаров"""
    
    def __init__(self, 
                 kafka_brokers: str = 'localhost:9092',
                 input_topic: str = 'shop-products',
                 output_topic: str = 'filtered-products',
                 banned_products_file: str = 'data/banned_products.json'):
        """
        Инициализация фильтра
        
        Args:
            kafka_brokers: Адреса Kafka брокеров
            input_topic: Входной топик с товарами от магазинов
            output_topic: Выходной топик с отфильтрованными товарами
            banned_products_file: Файл со списком запрещённых товаров
        """
        self.kafka_brokers = kafka_brokers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.banned_products_file = banned_products_file
        
        self.consumer = None
        self.producer = None
        self.banned_products: Set[str] = set()
        self.banned_skus: Set[str] = set()
        
        # Статистика
        self.processed_count = 0
        self.filtered_count = 0
        self.passed_count = 0
        
        # Флаг для остановки обработки
        self.running = False
        
        # Загружаем запрещённые товары
        self.load_banned_products()
    
    def load_banned_products(self):
        """Загрузка списка запрещённых товаров из файла"""
        try:
            banned_path = Path(self.banned_products_file)
            if not banned_path.exists():
                logger.warning(f"Файл запрещённых товаров не найден: {self.banned_products_file}")
                return
                
            with open(banned_path, 'r', encoding='utf-8') as f:
                banned_list = json.load(f)
            
            self.banned_products.clear()
            self.banned_skus.clear()
            
            for item in banned_list:
                if 'product_id' in item:
                    self.banned_products.add(item['product_id'])
                if 'sku' in item:
                    self.banned_skus.add(item['sku'])
            
            logger.info(f"Загружено {len(self.banned_products)} запрещённых product_id "
                       f"и {len(self.banned_skus)} запрещённых SKU")
                       
        except Exception as e:
            logger.error(f"Ошибка загрузки запрещённых товаров: {e}")
    
    def is_product_banned(self, product: Dict[str, Any]) -> bool:
        """
        Проверка, является ли товар запрещённым
        
        Args:
            product: Данные товара
            
        Returns:
            True если товар запрещён
        """
        product_id = product.get('product_id')
        sku = product.get('sku')
        
        # Проверяем product_id
        if product_id and product_id in self.banned_products:
            return True
            
        # Проверяем SKU
        if sku and sku in self.banned_skus:
            return True
            
        return False
    
    def connect(self) -> bool:
        """Подключение к Kafka"""
        try:
            # Создаём консьюмер
            self.consumer = KafkaConsumer(
                self.input_topic,
                bootstrap_servers=self.kafka_brokers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                group_id='banned-product-filter',
                enable_auto_commit=True
            )
            
            # Создаём продюсер
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_brokers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8'),
                retries=3,
                acks='all'
            )
            
            logger.info(f"Подключение к Kafka успешно: {self.kafka_brokers}")
            logger.info(f"Входной топик: {self.input_topic}")
            logger.info(f"Выходной топик: {self.output_topic}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Kafka: {e}")
            return False
    
    def process_message(self, message) -> bool:
        """
        Обработка одного сообщения
        
        Args:
            message: Сообщение из Kafka
            
        Returns:
            True если сообщение было обработано успешно
        """
        try:
            product = message.value
            product_id = product.get('product_id', 'Unknown')
            product_name = product.get('name', 'Unknown')
            
            self.processed_count += 1
            
            # Проверяем, запрещён ли товар
            if self.is_product_banned(product):
                self.filtered_count += 1
                logger.info(f"Товар отфильтрован (запрещён): {product_id} - {product_name}")
                
                # Отправляем событие о фильтрации в отдельный топик для аналитики
                filter_event = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'sku': product.get('sku'),
                    'store_id': product.get('store_id'),
                    'filtered_at': time.time(),
                    'reason': 'banned_product'
                }
                
                self.producer.send(
                    'filtered-events',
                    key=product_id,
                    value=filter_event
                )
                
                return True
            
            # Товар разрешён, пропускаем его дальше
            self.passed_count += 1
            
            # Добавляем метку о прохождении фильтрации
            filtered_product = product.copy()
            filtered_product['filter_passed_at'] = time.time()
            filtered_product['filter_status'] = 'approved'
            
            # Отправляем в выходной топик
            self.producer.send(
                self.output_topic,
                key=message.key,
                value=filtered_product
            )
            
            logger.debug(f"Товар пропущен: {product_id} - {product_name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            return False
    
    def start_processing(self):
        """Запуск обработки сообщений"""
        if not self.consumer or not self.producer:
            logger.error("Kafka соединения не установлены")
            return
        
        self.running = True
        logger.info("Запуск потоковой обработки...")
        
        try:
            while self.running:
                # Получаем сообщения с таймаутом
                message_pack = self.consumer.poll(timeout_ms=1000)
                
                if not message_pack:
                    continue
                
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        if not self.running:
                            break
                        
                        self.process_message(message)
                
                # Периодически выводим статистику
                if self.processed_count % 100 == 0 and self.processed_count > 0:
                    self.print_statistics()
        
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Ошибка в процессе обработки: {e}")
        finally:
            self.stop_processing()
    
    def stop_processing(self):
        """Остановка обработки"""
        self.running = False
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        if self.consumer:
            self.consumer.close()
        
        self.print_statistics()
        logger.info("Обработка остановлена")
    
    def print_statistics(self):
        """Вывод статистики обработки"""
        logger.info(f"Статистика: обработано={self.processed_count}, "
                   f"отфильтровано={self.filtered_count}, "
                   f"пропущено={self.passed_count}")
    
    def reload_banned_products(self):
        """Перезагрузка списка запрещённых товаров"""
        logger.info("Перезагрузка списка запрещённых товаров...")
        old_count = len(self.banned_products) + len(self.banned_skus)
        self.load_banned_products()
        new_count = len(self.banned_products) + len(self.banned_skus)
        logger.info(f"Список обновлён: было {old_count}, стало {new_count} записей")


class BannedProductManager:
    """Менеджер для управления списком запрещённых товаров"""
    
    def __init__(self, banned_products_file: str = 'data/banned_products.json'):
        self.banned_products_file = banned_products_file
    
    def load_banned_list(self) -> List[Dict]:
        """Загрузка текущего списка запрещённых товаров"""
        try:
            banned_path = Path(self.banned_products_file)
            if not banned_path.exists():
                return []
                
            with open(banned_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки списка: {e}")
            return []
    
    def save_banned_list(self, banned_list: List[Dict]):
        """Сохранение списка запрещённых товаров"""
        try:
            banned_path = Path(self.banned_products_file)
            banned_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(banned_path, 'w', encoding='utf-8') as f:
                json.dump(banned_list, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Список запрещённых товаров сохранён: {len(banned_list)} записей")
        except Exception as e:
            logger.error(f"Ошибка сохранения списка: {e}")
    
    def add_banned_product(self, product_id: str = None, sku: str = None, 
                          name: str = None, reason: str = None):
        """Добавление товара в список запрещённых"""
        if not product_id and not sku:
            raise ValueError("Необходимо указать product_id или sku")
        
        banned_list = self.load_banned_list()
        
        new_item = {}
        if product_id:
            new_item['product_id'] = product_id
        if sku:
            new_item['sku'] = sku
        if name:
            new_item['name'] = name
        if reason:
            new_item['reason'] = reason
        
        new_item['added_at'] = time.time()
        
        banned_list.append(new_item)
        self.save_banned_list(banned_list)
        
        logger.info(f"Товар добавлен в запрещённые: {new_item}")
    
    def remove_banned_product(self, product_id: str = None, sku: str = None):
        """Удаление товара из списка запрещённых"""
        banned_list = self.load_banned_list()
        original_count = len(banned_list)
        
        banned_list = [
            item for item in banned_list
            if not (
                (product_id and item.get('product_id') == product_id) or
                (sku and item.get('sku') == sku)
            )
        ]
        
        removed_count = original_count - len(banned_list)
        
        if removed_count > 0:
            self.save_banned_list(banned_list)
            logger.info(f"Удалено {removed_count} записей из запрещённых")
        else:
            logger.info("Записи для удаления не найдены")
    
    def list_banned_products(self):
        """Вывод списка запрещённых товаров"""
        banned_list = self.load_banned_list()
        
        if not banned_list:
            print("Список запрещённых товаров пуст")
            return
        
        print(f"Запрещённые товары ({len(banned_list)} записей):")
        print("-" * 60)
        
        for i, item in enumerate(banned_list, 1):
            print(f"{i}. Product ID: {item.get('product_id', 'N/A')}")
            if 'sku' in item:
                print(f"   SKU: {item['sku']}")
            if 'name' in item:
                print(f"   Название: {item['name']}")
            if 'reason' in item:
                print(f"   Причина: {item['reason']}")
            print()


@click.group()
def cli():
    """Система фильтрации запрещённых товаров"""
    pass


@cli.command()
@click.option('--brokers', default='localhost:9092', help='Kafka брокеры')
@click.option('--input-topic', default='shop-products', help='Входной топик')
@click.option('--output-topic', default='filtered-products', help='Выходной топик')
@click.option('--banned-file', default='data/banned_products.json', 
              help='Файл со списком запрещённых товаров')
def start(brokers, input_topic, output_topic, banned_file):
    """Запуск фильтрации запрещённых товаров"""
    filter_processor = BannedProductFilter(
        kafka_brokers=brokers,
        input_topic=input_topic,
        output_topic=output_topic,
        banned_products_file=banned_file
    )
    
    if filter_processor.connect():
        filter_processor.start_processing()
    else:
        logger.error("Не удалось подключиться к Kafka")


@cli.command()
@click.option('--product-id', help='ID товара')
@click.option('--sku', help='SKU товара')
@click.option('--name', help='Название товара')
@click.option('--reason', help='Причина запрета')
@click.option('--banned-file', default='data/banned_products.json')
def ban(product_id, sku, name, reason, banned_file):
    """Добавление товара в список запрещённых"""
    manager = BannedProductManager(banned_file)
    try:
        manager.add_banned_product(product_id, sku, name, reason)
        click.echo("Товар добавлен в список запрещённых")
    except Exception as e:
        click.echo(f"Ошибка: {e}")


@cli.command()
@click.option('--product-id', help='ID товара')
@click.option('--sku', help='SKU товара')
@click.option('--banned-file', default='data/banned_products.json')
def unban(product_id, sku, banned_file):
    """Удаление товара из списка запрещённых"""
    manager = BannedProductManager(banned_file)
    manager.remove_banned_product(product_id, sku)
    click.echo("Товар удалён из списка запрещённых")


@cli.command()
@click.option('--banned-file', default='data/banned_products.json')
def list(banned_file):
    """Просмотр списка запрещённых товаров"""
    manager = BannedProductManager(banned_file)
    manager.list_banned_products()


if __name__ == '__main__':
    cli() 