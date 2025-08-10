from abc import ABC, abstractmethod
import aio_pika
import asyncio
import json

from app.config.setting import settings

class MQBaseWorker(ABC):
    def __init__(self, queue_name: str, name: str, rabbit_url: str = settings.RABBITMQ_URL):
        self.queue_name = queue_name
        self.name = name
        self.rabbit_url = rabbit_url

        self.connection = None
        self.channel = None
        self.queue = None

    async def connect(self):
        print(f"Connecting to RabbitMQ: {self.rabbit_url}")
        tried = 0
        while tried < settings.WORKER_RETRY_COUNT:
            try:
                self.connection = await aio_pika.connect_robust(self.rabbit_url)
                self.channel = await self.connection.channel()
                self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
                print(f"Successfully connected to queue: {self.queue_name}")
                tried = settings.WORKER_RETRY_COUNT  # Exit loop on success
            except Exception as e:
                print(f"Connection error: {e}")
                tried += 1
                await asyncio.sleep(settings.WORKER_RETRY_DELAY)

    async def consume(self):
        await self.connect()
        await self.queue.consume(self._on_message)
        print(f"{self.name} listening on {self.queue_name}")
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            print(f"{self.name} received cancellation signal, shutting down gracefully...")
            await self.shutdown()
            
    async def shutdown(self):
        """Gracefully shutdown the worker."""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            print(f"{self.name} shutdown complete")
        except Exception as e:
            print(f"{self.name} error during shutdown: {e}")

    async def _on_message(self, message: aio_pika.IncomingMessage):
        try:
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await self.process_message(data)
                except asyncio.CancelledError:
                    print(f"{self.name} processing was cancelled")
                    # Re-raise to properly handle cancellation
                    raise
                except Exception as e:
                    print(f"{self.name} error processing message: {e}")
        except asyncio.CancelledError:
            print(f"{self.name} message processing was cancelled")
            # Don't re-raise here to prevent the error from propagating to the event loop
        except Exception as e:
            print(f"{self.name} error in message handler: {e}")

    
    @abstractmethod
    async def process_message(self, data: dict):
        """
        Process the incoming message.
        This method should be implemented by subclasses.
        """
        pass