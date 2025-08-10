import asyncio
import aio_pika
import json
import time

async def send_messages():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    channel = await connection.channel()
    
    # Send multiple messages
    for i in range(5):
        message_data = {"job_id": f"abc{i}", "timestamp": time.time()}
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(message_data).encode()),
            routing_key="echo_queue"
        )
        print(f"Sent message: {message_data}")
        await asyncio.sleep(1)  # Wait a bit between sends
    
    await connection.close()

if __name__ == "__main__":
    asyncio.run(send_messages())