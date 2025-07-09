"""
Client API - интерфейс для клиентов маркетплейса
Поиск товаров и получение персонализированных рекомендаций
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import click
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClientAPI:
    """Класс для работы с клиентскими запросами"""
    
    def __init__(self, 
                 kafka_brokers: str = 'localhost:9092',
                 user_id: str = None):
        """
        Инициализация Client API
        
        Args:
            kafka_brokers: Адреса Kafka брокеров
            user_id: ID пользователя
        """
        self.kafka_brokers = kafka_brokers
        self.user_id = user_id or str(uuid.uuid4())
        self.producer = None
        
        # Топики Kafka
        self.search_topic = 'client-searches'
        self.recommendations_topic = 'client-recommendations'
        self.recommendations_result_topic = 'recommendations-results'
    
    def connect_kafka(self) -> bool:
        """Подключение к Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_brokers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8'),
                retries=3,
                acks='all'
            )
            logger.info(f"Подключение к Kafka успешно: {self.kafka_brokers}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Kafka: {e}")
            return False
    

    
    def send_search_event(self, query: str, filters: Dict = None) -> bool:
        """
        Отправка события поиска в Kafka для аналитики
        
        Args:
            query: Поисковый запрос
            filters: Дополнительные фильтры
            
        Returns:
            True если отправка успешна
        """
        if not self.producer:
            logger.error("Kafka продюсер не инициализирован")
            return False
        
        search_event = {
            'user_id': self.user_id,
            'query': query,
            'filters': filters or {},
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'product_search'
        }
        
        try:
            self.producer.send(
                self.search_topic,
                key=self.user_id,
                value=search_event
            )
            logger.info(f"Событие поиска отправлено в Kafka: {query}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки события поиска: {e}")
            return False
    

    
    def search_products_file(self, query: str, file_path: str = 'data/products.json') -> List[Dict]:
        """
        Простой поиск товаров в файле (fallback)
        
        Args:
            query: Поисковый запрос
            file_path: Путь к файлу с товарами
            
        Returns:
            Список найденных товаров
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            query_lower = query.lower()
            results = []
            
            for product in products:
                # Поиск по названию, описанию, тегам
                searchable_text = (
                    product.get('name', '').lower() + ' ' +
                    product.get('description', '').lower() + ' ' +
                    ' '.join(product.get('tags', [])).lower() + ' ' +
                    product.get('brand', '').lower() + ' ' +
                    product.get('category', '').lower()
                )
                
                if query_lower in searchable_text:
                    results.append(product)
            
            logger.info(f"Найдено {len(results)} товаров в файле")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска в файле: {e}")
            return []
    
    def search_products(self, query: str) -> List[Dict]:
        """
        Поиск товаров в файле
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список найденных товаров
        """
        # Отправляем событие поиска в Kafka для аналитики
        self.send_search_event(query)
        
        # Используем файловый поиск
        results = self.search_products_file(query)
        
        return results
    
    def request_recommendations(self, user_preferences: Dict = None) -> bool:
        """
        Запрос персонализированных рекомендаций
        
        Args:
            user_preferences: Предпочтения пользователя
            
        Returns:
            True если запрос отправлен успешно
        """
        if not self.producer:
            logger.error("Kafka продюсер не инициализирован")
            return False
        
        recommendation_request = {
            'user_id': self.user_id,
            'preferences': user_preferences or {},
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': str(uuid.uuid4())
        }
        
        try:
            self.producer.send(
                self.recommendations_topic,
                key=self.user_id,
                value=recommendation_request
            )
            logger.info(f"Запрос рекомендаций отправлен для пользователя {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки запроса рекомендаций: {e}")
            return False
    
    def get_recommendations(self, timeout_seconds: int = 30) -> List[Dict]:
        """
        Получение рекомендаций из Kafka топика
        
        Args:
            timeout_seconds: Таймаут ожидания в секундах
            
        Returns:
            Список рекомендованных товаров
        """
        try:
            consumer = KafkaConsumer(
                self.recommendations_result_topic,
                bootstrap_servers=self.kafka_brokers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                consumer_timeout_ms=timeout_seconds * 1000
            )
            
            logger.info(f"Ожидание рекомендаций для пользователя {self.user_id}...")
            
            for message in consumer:
                if message.key == self.user_id:
                    recommendations = message.value.get('recommendations', [])
                    logger.info(f"Получено {len(recommendations)} рекомендаций")
                    consumer.close()
                    return recommendations
            
            logger.warning("Таймаут ожидания рекомендаций")
            consumer.close()
            return []
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций: {e}")
            return []
    
    def close(self):
        """Закрытие соединений"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka соединение закрыто")


@click.group()
@click.option('--user-id', default=None, help='ID пользователя')
@click.option('--kafka', default='localhost:9092', help='Kafka брокеры')
@click.pass_context
def cli(ctx, user_id, kafka):
    """Client API - интерфейс для клиентов маркетплейса"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = ClientAPI(
        kafka_brokers=kafka,
        user_id=user_id
    )
    
    # Подключения
    ctx.obj['client'].connect_kafka()


@cli.command()
@click.argument('query')
@click.option('--limit', default=10, help='Максимальное количество результатов')
@click.pass_context
def search(ctx, query, limit):
    """Поиск товаров по запросу"""
    client = ctx.obj['client']
    
    click.echo(f"Поиск товаров: '{query}'")
    click.echo("-" * 40)
    
    results = client.search_products(query)
    
    if not results:
        click.echo("Товары не найдены")
        return
    
    for i, product in enumerate(results[:limit], 1):
        click.echo(f"{i}. {product.get('name', 'Без названия')}")
        click.echo(f"   Цена: {product.get('price', {}).get('amount', 'Не указана')} "
                  f"{product.get('price', {}).get('currency', '')}")
        click.echo(f"   Бренд: {product.get('brand', 'Не указан')}")
        click.echo(f"   Категория: {product.get('category', 'Не указана')}")
        
        if '_score' in product:
            click.echo(f"   Релевантность: {product['_score']:.2f}")
            
        click.echo()


@cli.command()
@click.option('--category', help='Предпочитаемая категория')
@click.option('--brand', help='Предпочитаемый бренд')
@click.option('--max-price', type=float, help='Максимальная цена')
@click.option('--wait', is_flag=True, help='Дождаться результата')
@click.pass_context
def recommendations(ctx, category, brand, max_price, wait):
    """Получение персонализированных рекомендаций"""
    client = ctx.obj['client']
    
    preferences = {}
    if category:
        preferences['category'] = category
    if brand:
        preferences['brand'] = brand
    if max_price:
        preferences['max_price'] = max_price
    
    click.echo(f"Запрос рекомендаций для пользователя {client.user_id}")
    if preferences:
        click.echo(f"Предпочтения: {preferences}")
    
    if client.request_recommendations(preferences):
        click.echo("Запрос рекомендаций отправлен в систему аналитики")
        
        if wait:
            click.echo("Ожидание рекомендаций...")
            recommendations = client.get_recommendations()
            
            if recommendations:
                click.echo(f"\nПолучено {len(recommendations)} рекомендаций:")
                click.echo("-" * 40)
                
                for i, product in enumerate(recommendations, 1):
                    click.echo(f"{i}. {product.get('name', 'Без названия')}")
                    click.echo(f"   Цена: {product.get('price', {}).get('amount', 'Не указана')} "
                              f"{product.get('price', {}).get('currency', '')}")
                    click.echo(f"   Причина рекомендации: {product.get('recommendation_reason', 'Не указана')}")
                    click.echo()
            else:
                click.echo("Рекомендации не получены в отведенное время")
    else:
        click.echo("Ошибка отправки запроса рекомендаций")


@cli.command()
@click.pass_context
def status(ctx):
    """Проверка статуса подключений"""
    client = ctx.obj['client']
    
    click.echo(f"Пользователь: {client.user_id}")
    click.echo(f"Kafka: {'✓' if client.producer else '✗'} {client.kafka_brokers}")
    click.echo("Поиск: файловый")


if __name__ == '__main__':
    cli() 