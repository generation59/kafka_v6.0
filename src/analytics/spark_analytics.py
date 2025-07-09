"""
Аналитическая система на базе Apache Spark
Обрабатывает данные из Kafka и генерирует рекомендации
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.streaming import StreamingQuery
import click

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SparkAnalytics:
    """Класс для аналитической обработки данных с помощью Spark"""
    
    def __init__(self, 
                 kafka_brokers: str = 'localhost:9092',
                 spark_master: str = 'spark://spark-master:7077'):
        """
        Инициализация Spark Analytics
        
        Args:
            kafka_brokers: Адреса Kafka брокеров
            spark_master: Адрес Spark Master
        """
        self.kafka_brokers = kafka_brokers
        self.spark_master = spark_master
        self.spark = None
        
        # Топики Kafka
        self.products_topic = 'filtered-products'
        self.searches_topic = 'client-searches'
        self.recommendations_topic = 'client-recommendations'
        self.recommendations_result_topic = 'recommendations-results'
        
    def create_spark_session(self) -> bool:
        """Создание Spark сессии"""
        try:
            self.spark = SparkSession.builder \
                .appName("MarketplaceAnalytics") \
                .master(self.spark_master) \
                .config("spark.jars.packages", 
                       "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .getOrCreate()
            
            self.spark.sparkContext.setLogLevel("WARN")
            logger.info(f"Spark сессия создана: {self.spark_master}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания Spark сессии: {e}")
            return False
    
    def read_kafka_stream(self, topic: str) -> DataFrame:
        """
        Чтение потока данных из Kafka
        
        Args:
            topic: Имя топика Kafka
            
        Returns:
            Spark DataFrame
        """
        try:
            df = self.spark \
                .readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", self.kafka_brokers) \
                .option("subscribe", topic) \
                .option("startingOffsets", "earliest") \
                .load()
            
            logger.info(f"Подключение к Kafka топику: {topic}")
            return df
            
        except Exception as e:
            logger.error(f"Ошибка чтения из Kafka: {e}")
            return None
    
    def parse_product_data(self, kafka_df: DataFrame) -> DataFrame:
        """
        Парсинг данных о товарах из Kafka
        
        Args:
            kafka_df: Исходный DataFrame из Kafka
            
        Returns:
            Обработанный DataFrame
        """
        # Схема для данных товаров
        product_schema = StructType([
            StructField("product_id", StringType(), True),
            StructField("name", StringType(), True),
            StructField("description", StringType(), True),
            StructField("category", StringType(), True),
            StructField("brand", StringType(), True),
            StructField("price", StructType([
                StructField("amount", DoubleType(), True),
                StructField("currency", StringType(), True)
            ]), True),
            StructField("tags", ArrayType(StringType()), True),
            StructField("store_id", StringType(), True),
            StructField("created_at", StringType(), True),
            StructField("filter_passed_at", DoubleType(), True)
        ])
        
        # Парсинг JSON данных
        parsed_df = kafka_df.select(
            col("key").cast("string").alias("product_key"),
            from_json(col("value").cast("string"), product_schema).alias("product"),
            col("timestamp").alias("kafka_timestamp")
        ).select(
            col("product_key"),
            col("product.*"),
            col("kafka_timestamp")
        )
        
        return parsed_df
    
    def parse_search_data(self, kafka_df: DataFrame) -> DataFrame:
        """
        Парсинг данных о поисках из Kafka
        
        Args:
            kafka_df: Исходный DataFrame из Kafka
            
        Returns:
            Обработанный DataFrame
        """
        # Схема для поисковых данных
        search_schema = StructType([
            StructField("user_id", StringType(), True),
            StructField("query", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("filters", MapType(StringType(), StringType()), True)
        ])
        
        # Парсинг JSON данных
        parsed_df = kafka_df.select(
            col("key").cast("string").alias("user_key"),
            from_json(col("value").cast("string"), search_schema).alias("search"),
            col("timestamp").alias("kafka_timestamp")
        ).select(
            col("user_key"),
            col("search.*"),
            col("kafka_timestamp")
        )
        
        return parsed_df
    
    def analyze_product_popularity(self, products_df: DataFrame, searches_df: DataFrame) -> DataFrame:
        """
        Анализ популярности товаров
        
        Args:
            products_df: DataFrame с товарами
            searches_df: DataFrame с поисками
            
        Returns:
            DataFrame с популярностью товаров
        """
        # Подсчет поисков по категориям
        category_searches = searches_df \
            .filter(col("query").isNotNull()) \
            .groupBy("query") \
            .agg(
                count("*").alias("search_count"),
                countDistinct("user_id").alias("unique_users")
            )
        
        # Агрегация товаров по категориям
        product_stats = products_df \
            .groupBy("category", "brand") \
            .agg(
                count("*").alias("product_count"),
                avg("price.amount").alias("avg_price"),
                min("price.amount").alias("min_price"),
                max("price.amount").alias("max_price")
            )
        
        return product_stats
    
    def generate_recommendations(self, user_id: str, preferences: Dict) -> List[Dict]:
        """
        Генерация рекомендаций для пользователя
        (Упрощенная логика для демонстрации)
        
        Args:
            user_id: ID пользователя
            preferences: Предпочтения пользователя
            
        Returns:
            Список рекомендованных товаров
        """
        try:
            # Читаем данные о товарах из файла для простоты
            with open('data/products.json', 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            recommendations = []
            
            # Простая логика рекомендаций на основе предпочтений
            for product in products:
                score = 0
                reasons = []
                
                # Проверяем категорию
                if 'category' in preferences:
                    if product.get('category', '').lower() == preferences['category'].lower():
                        score += 50
                        reasons.append(f"Соответствует предпочитаемой категории: {preferences['category']}")
                
                # Проверяем бренд
                if 'brand' in preferences:
                    if product.get('brand', '').lower() == preferences['brand'].lower():
                        score += 30
                        reasons.append(f"Соответствует предпочитаемому бренду: {preferences['brand']}")
                
                # Проверяем цену
                if 'max_price' in preferences:
                    product_price = product.get('price', {}).get('amount', float('inf'))
                    if product_price <= preferences['max_price']:
                        score += 20
                        reasons.append(f"Цена в пределах бюджета: {product_price}")
                
                # Добавляем случайный компонент для разнообразия
                score += hash(product.get('product_id', '')) % 20
                
                if score > 30:  # Порог для рекомендаций
                    recommendation = product.copy()
                    recommendation['recommendation_score'] = score
                    recommendation['recommendation_reason'] = '; '.join(reasons) if reasons else 'Популярный товар'
                    recommendation['recommended_at'] = datetime.utcnow().isoformat()
                    recommendation['user_id'] = user_id
                    recommendations.append(recommendation)
            
            # Сортируем по score и берем топ-5
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            return recommendations[:5]
            
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            return []
    
    def process_recommendation_requests(self, recommendations_df: DataFrame):
        """
        Обработка запросов на рекомендации
        
        Args:
            recommendations_df: DataFrame с запросами рекомендаций
        """
        def process_batch(batch_df, batch_id):
            """Обработка батча запросов"""
            try:
                logger.info(f"Обработка батча рекомендаций {batch_id}")
                
                # Конвертируем в pandas для удобства обработки
                requests = batch_df.collect()
                
                for row in requests:
                    user_id = row['user_id']
                    preferences = row['preferences'] if row['preferences'] else {}
                    
                    logger.info(f"Генерация рекомендаций для пользователя {user_id}")
                    
                    # Генерируем рекомендации
                    recommendations = self.generate_recommendations(user_id, preferences)
                    
                    if recommendations:
                        # Отправляем результат обратно в Kafka
                        result = {
                            'user_id': user_id,
                            'recommendations': recommendations,
                            'generated_at': datetime.utcnow().isoformat(),
                            'request_id': str(uuid.uuid4())
                        }
                        
                        # Создаем DataFrame для записи в Kafka
                        result_df = self.spark.createDataFrame([
                            (user_id, json.dumps(result, ensure_ascii=False))
                        ], ["key", "value"])
                        
                        # Записываем в Kafka
                        result_df.write \
                            .format("kafka") \
                            .option("kafka.bootstrap.servers", self.kafka_brokers) \
                            .option("topic", self.recommendations_result_topic) \
                            .save()
                        
                        logger.info(f"Рекомендации отправлены для пользователя {user_id}")
                    else:
                        logger.warning(f"Не удалось сгенерировать рекомендации для {user_id}")
                        
            except Exception as e:
                logger.error(f"Ошибка обработки батча {batch_id}: {e}")
        
        return recommendations_df.writeStream \
            .foreachBatch(process_batch) \
            .outputMode("append") \
            .trigger(processingTime='10 seconds') \
            .start()
    
    def create_analytics_dashboard_data(self, products_df: DataFrame):
        """
        Создание данных для дашборда аналитики
        
        Args:
            products_df: DataFrame с товарами
        """
        def process_analytics_batch(batch_df, batch_id):
            """Обработка батча для аналитики"""
            try:
                logger.info(f"Создание аналитических данных, батч {batch_id}")
                
                if batch_df.count() == 0:
                    return
                
                # Статистика по категориям
                category_stats = batch_df.groupBy("category") \
                    .agg(
                        count("*").alias("total_products"),
                        avg("price.amount").alias("avg_price"),
                        countDistinct("brand").alias("brands_count")
                    ).collect()
                
                # Статистика по брендам
                brand_stats = batch_df.groupBy("brand") \
                    .agg(
                        count("*").alias("total_products"),
                        avg("price.amount").alias("avg_price")
                    ).collect()
                
                # Выводим статистику
                logger.info("=== Статистика по категориям ===")
                for row in category_stats:
                    logger.info(f"Категория: {row['category']}, "
                              f"Товаров: {row['total_products']}, "
                              f"Средняя цена: {row['avg_price']:.2f}, "
                              f"Брендов: {row['brands_count']}")
                
                logger.info("=== Статистика по брендам ===")
                for row in brand_stats:
                    logger.info(f"Бренд: {row['brand']}, "
                              f"Товаров: {row['total_products']}, "
                              f"Средняя цена: {row['avg_price']:.2f}")
                              
            except Exception as e:
                logger.error(f"Ошибка создания аналитических данных: {e}")
        
        return products_df.writeStream \
            .foreachBatch(process_analytics_batch) \
            .outputMode("append") \
            .trigger(processingTime='30 seconds') \
            .start()
    
    def start_analytics_processing(self):
        """Запуск аналитической обработки"""
        if not self.spark:
            logger.error("Spark сессия не создана")
            return []
        
        queries = []
        
        try:
            # Обработка товаров
            products_kafka_df = self.read_kafka_stream(self.products_topic)
            if products_kafka_df:
                products_df = self.parse_product_data(products_kafka_df)
                
                # Запускаем аналитику товаров
                analytics_query = self.create_analytics_dashboard_data(products_df)
                queries.append(analytics_query)
            
            # Обработка запросов рекомендаций
            recommendations_kafka_df = self.read_kafka_stream(self.recommendations_topic)
            if recommendations_kafka_df:
                # Схема для запросов рекомендаций
                rec_schema = StructType([
                    StructField("user_id", StringType(), True),
                    StructField("preferences", MapType(StringType(), StringType()), True),
                    StructField("timestamp", StringType(), True),
                    StructField("request_id", StringType(), True)
                ])
                
                recommendations_df = recommendations_kafka_df.select(
                    col("key").cast("string").alias("user_key"),
                    from_json(col("value").cast("string"), rec_schema).alias("request")
                ).select(
                    col("user_key"),
                    col("request.*")
                )
                
                # Запускаем обработку рекомендаций
                rec_query = self.process_recommendation_requests(recommendations_df)
                queries.append(rec_query)
            
            logger.info(f"Запущено {len(queries)} аналитических задач")
            return queries
            
        except Exception as e:
            logger.error(f"Ошибка запуска аналитической обработки: {e}")
            return []
    
    def stop(self):
        """Остановка Spark сессии"""
        if self.spark:
            self.spark.stop()
            logger.info("Spark сессия остановлена")


@click.group()
def cli():
    """Система аналитики на Apache Spark"""
    pass


@cli.command()
@click.option('--kafka-brokers', default='localhost:9092', help='Kafka брокеры')
@click.option('--spark-master', default='spark://localhost:7077', help='Spark Master URL')
def start(kafka_brokers, spark_master):
    """Запуск аналитической обработки"""
    analytics = SparkAnalytics(
        kafka_brokers=kafka_brokers,
        spark_master=spark_master
    )
    
    if analytics.create_spark_session():
        logger.info("Запуск аналитической системы...")
        queries = analytics.start_analytics_processing()
        
        if queries:
            try:
                # Ждем завершения всех запросов
                for query in queries:
                    query.awaitTermination()
            except KeyboardInterrupt:
                logger.info("Получен сигнал остановки")
                for query in queries:
                    query.stop()
            finally:
                analytics.stop()
        else:
            logger.error("Не удалось запустить аналитические задачи")
            analytics.stop()
    else:
        logger.error("Не удалось создать Spark сессию")


@cli.command()
@click.argument('user_id')
@click.option('--category', help='Предпочитаемая категория')
@click.option('--brand', help='Предпочитаемый бренд')
@click.option('--max-price', type=float, help='Максимальная цена')
def test_recommendations(user_id, category, brand, max_price):
    """Тестирование генерации рекомендаций"""
    analytics = SparkAnalytics()
    
    preferences = {}
    if category:
        preferences['category'] = category
    if brand:
        preferences['brand'] = brand
    if max_price:
        preferences['max_price'] = max_price
    
    recommendations = analytics.generate_recommendations(user_id, preferences)
    
    if recommendations:
        click.echo(f"Рекомендации для пользователя {user_id}:")
        click.echo("-" * 50)
        
        for i, rec in enumerate(recommendations, 1):
            click.echo(f"{i}. {rec.get('name', 'Без названия')}")
            click.echo(f"   Цена: {rec.get('price', {}).get('amount', 'Не указана')} "
                      f"{rec.get('price', {}).get('currency', '')}")
            click.echo(f"   Оценка: {rec.get('recommendation_score', 0)}")
            click.echo(f"   Причина: {rec.get('recommendation_reason', 'Не указана')}")
            click.echo()
    else:
        click.echo("Рекомендации не найдены")


if __name__ == '__main__':
    cli() 