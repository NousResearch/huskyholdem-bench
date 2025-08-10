import asyncio
import argparse
import time
from app.service.rabbitmq.echo_worker import EchoWorker

async def main(i: int):
    worker = EchoWorker(name=f"echo_worker_{i}")
    await worker.consume()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start an echo worker.")
    parser.add_argument("number", type=int, help="The number to identify the worker.")
    args = parser.parse_args()

    # wait a bit for rabbitmq to start
    time.sleep(5)  # Simulate some delay before starting the worker
    asyncio.run(main(args.number))
