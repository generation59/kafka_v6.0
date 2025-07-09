"""
Kafka to File Writer - сервис для записи данных из Kafka в файлы
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from kafka import KafkaConsumer
import click

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KafkaFileWriter:
    """Класс для записи данных из Kafka в файлы"""
    
    def __init__(self, kafka_brokers: str = 'localhost:9092'):
        """
        Инициализация Kafka File Writer
        
        Args:
            kafka_brokers: Адреса Kafka брокеров
        """
        self.kafka_brokers = kafka_brokers
        self.output_dir = Path('data/output')
        self.output_dir.mkdir(exist_ok=True)
    
    def write_topic_to_file(self, topic: str, output_file: str, max_messages: int = None):
        """
        Записывает сообщения из топика в файл
        
        Args:
            topic: Название Kafka топика
            output_file: Имя выходного файла
            max_messages: Максимальное количество сообщений (None = бесконечно)
        """
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.kafka_brokers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                group_id=f'file-writer-{topic}'
            )
            
            output_path = self.output_dir / output_file
            messages_written = 0
            
            logger.info(f"Начинаем запись из топика '{topic}' в файл '{output_path}'")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for message in consumer:
                    # Добавляем метаданные
                    record = {
                        'kafka_metadata': {
                            'topic': message.topic,
                            'partition': message.partition,
                            'offset': message.offset,
                            'timestamp': message.timestamp,
                            'key': message.key
                        },
                        'data': message.value,
                        'written_at': datetime.utcnow().isoformat()
                    }
                    
                    # Записываем в файл
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    f.flush()
                    
                    messages_written += 1
                    
                    if messages_written % 10 == 0:
                        logger.info(f"Записано {messages_written} сообщений в {output_file}")
                    
                    # Проверяем лимит
                    if max_messages and messages_written >= max_messages:
                        break
            
            logger.info(f"Завершена запись: {messages_written} сообщений в {output_path}")
            consumer.close()
            
        except Exception as e:
            logger.error(f"Ошибка записи данных: {e}")


@click.group()
def cli():
    """Kafka to File Writer - запись данных из Kafka в файлы"""
    pass


@cli.command()
@click.option('--topic', required=True, help='Kafka топик для чтения')
@click.option('--output', required=True, help='Имя выходного файла')
@click.option('--max-messages', type=int, help='Максимальное количество сообщений')
@click.option('--kafka', default='localhost:9092', help='Kafka брокеры')
def write(topic, output, max_messages, kafka):
    """Записать сообщения из топика в файл"""
    writer = KafkaFileWriter(kafka)
    writer.write_topic_to_file(topic, output, max_messages)


@cli.command()
@click.option('--kafka', default='localhost:9092', help='Kafka брокеры')
def write_all(kafka):
    """Записать данные из всех основных топиков"""
    writer = KafkaFileWriter(kafka)
    
    # Основные топики для записи
    topics_to_write = [
        ('shop-products', 'products.jsonl'),
        ('filtered-products', 'filtered_products.jsonl'),
        ('client-searches', 'client_searches.jsonl'),
        ('client-recommendations', 'client_recommendations.jsonl')
    ]
    
    for topic, filename in topics_to_write:
        click.echo(f"Записываем топик '{topic}' в файл '{filename}'...")
        writer.write_topic_to_file(topic, filename, max_messages=50)


if __name__ == '__main__':
    cli() 