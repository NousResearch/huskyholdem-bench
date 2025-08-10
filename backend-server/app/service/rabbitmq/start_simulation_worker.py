import asyncio
import argparse
import time
import logging
from app.service.rabbitmq.simulation_worker import SimulationWorker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def periodic_llm_batch_check(worker: SimulationWorker):
    """Periodically check for LLM_BATCH_RUN jobs and log the count."""
    while True:
        try:
            await asyncio.sleep(worker.llm_batch_check_interval)
            await worker.check_llm_batch_jobs()
        except asyncio.CancelledError:
            logger.info(f"LLM batch checking task cancelled for {worker.name}")
            break
        except Exception as e:
            logger.error(f"Error in periodic LLM batch check for {worker.name}: {e}")

async def main(i: int):
    worker = SimulationWorker(name=f"simulation_worker_{i}")
    
    # Start both the worker consumption and periodic LLM batch checking
    worker_task = asyncio.create_task(worker.consume())
    llm_batch_task = asyncio.create_task(periodic_llm_batch_check(worker))
    
    logger.info(f"Started {worker.name} with LLM batch checking every {worker.llm_batch_check_interval}s")
    
    try:
        # Wait for either task to complete (they should run indefinitely)
        await asyncio.gather(worker_task, llm_batch_task)
    except asyncio.CancelledError:
        logger.info(f"Received cancellation signal, shutting down {worker.name}...")
        worker_task.cancel()
        llm_batch_task.cancel()
        try:
            await asyncio.gather(worker_task, llm_batch_task, return_exceptions=True)
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a simulation worker.")
    parser.add_argument("number", type=int, help="The number to identify the worker.")
    args = parser.parse_args()

    # wait a bit for rabbitmq to start
    time.sleep(10)
    asyncio.run(main(args.number))