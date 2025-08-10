import json
import aio_pika
from app.config.setting import settings

class MQProducer:
    def __init__(self, rabbit_url=settings.RABBITMQ_URL):
        self.rabbit_url = rabbit_url
        self.connection = None
        self.channel = None

    async def connect(self):
        """Establish connection to RabbitMQ if not already connected"""
        if self.connection is None or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(self.rabbit_url)
            self.channel = await self.connection.channel()
            print(f"Connected to RabbitMQ at {self.rabbit_url}")

    async def close(self):
        """Close the connection to RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.connection = None
            self.channel = None
            print("Disconnected from RabbitMQ")

    async def send_message(self, queue_name: str, data: dict, persistent=True):
        """Send a message to the specified queue"""
        await self.connect()
        
        # Ensure the queue exists
        assert self.channel is not None  # Type assertion for linter
        await self.channel.declare_queue(queue_name, durable=True)
        
        # Create message
        message = aio_pika.Message(
            body=json.dumps(data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT
        )
        
        # Publish message
        await self.channel.default_exchange.publish(
            message,
            routing_key=queue_name
        )
        
        print(f"Message sent to queue '{queue_name}'")