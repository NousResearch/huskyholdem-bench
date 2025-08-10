import logging
import time
from app.service.rabbitmq.base_worker import MQBaseWorker

def setup_worker_logger(worker_name: str):
    logger = logging.getLogger(worker_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if re-imported
    if not logger.handlers:
        handler = logging.FileHandler("echo_worker.log")
        formatter = logging.Formatter('[%(asctime)s] [%(name)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

class EchoWorker(MQBaseWorker):
    def __init__(self, name: str):
        """
        Initialize the EchoWorker with the given queue name, worker name, and RabbitMQ URL.
        """
        super().__init__("echo_queue", name)
        self.logger = setup_worker_logger(name)

    async def process_message(self, data: dict):
        """
        Process the incoming message.
        This method should be implemented by subclasses.
        """
        # Here we just echo the message back to the sender
        time.sleep(10)  # Simulate some processing time
        print(f"Echo message: {data} from {self.name}")
        self.logger.info(f"Processed job_id={data}")
