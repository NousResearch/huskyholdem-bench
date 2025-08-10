import asyncio
import base64
import datetime
import io
import json
from types import SimpleNamespace
import uuid
import logging
import traceback
import os
import aio_pika
import tarfile

from sqlmodel import Session
from app.config.setting import settings
from app.models.game import GameStatus, GameLog
from app.models.job import Job, JobStatus, JobType
from app.models.rabbit_message import SimulationMessageType
from app.models.submission import Submission
from app.models.leaderboard import LeaderBoard
from app.models.batch_llm import BatchLLMQueue
from app.service.docker.shared_manager import SharedDockerPoolManager
from app.service.rabbitmq.base_worker import MQBaseWorker
from app.service.db.supabase import SupabaseBucketService
from app.service.cache.redis import RedisService
from sqlmodel import select
from typing import Tuple
import time

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.service.db.postgres import engine
from app.utils.file import clone_bytes, create_tar_from_files, check_input_stat

# Get supabase bucket
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")
bucket_service = SupabaseBucketService(SUPABASE_BUCKET)  # Your Supabase bucket name

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimulationWorker(MQBaseWorker):
    """
    Simulation worker for handling simulation tasks with Docker container pooling.
    """

    def __init__(self, name):
        super().__init__("simulation_queue", name)
        self.docker_pool_manager = SharedDockerPoolManager()
        self.worker_id = f"sim_worker_{name}"
        self.sim_mode = True
        self.llm_batch_check_interval = 10  # Check every 10 seconds
        self.redis_service = RedisService()
        self.redis_client = self.redis_service.client
        
        # LLM batch lock configuration
        self.LLM_BATCH_LOCK_KEY = "llm_batch_queue:lock"
        self.LLM_BATCH_LOCK_TIMEOUT = 5  # seconds

    def _acquire_llm_batch_lock(self, timeout: int = None):
        """Acquire a distributed lock for LLM batch operations."""
        if timeout is None:
            timeout = self.LLM_BATCH_LOCK_TIMEOUT
            
        class LLMBatchLock:
            def __init__(self, redis_client, key, timeout, worker_id):
                self.redis_client = redis_client
                self.key = key
                self.timeout = timeout
                self.worker_id = worker_id
                self.acquired = False
                
            def __enter__(self):
                end_time = time.time() + self.timeout
                while time.time() < end_time:
                    if self.redis_client.set(self.key, self.worker_id, ex=self.timeout, nx=True):
                        self.acquired = True
                        logger.debug(f"Acquired LLM batch lock for {self.worker_id}")
                        return self
                    time.sleep(0.1)
                raise Exception(f"Failed to acquire LLM batch lock {self.key} within {self.timeout} seconds")
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.acquired:
                    try:
                        # Only delete if we still own the lock (check value matches our worker_id)
                        current_owner = self.redis_client.get(self.key)
                        if current_owner:
                            # Handle both bytes and string responses from Redis
                            if isinstance(current_owner, bytes):
                                current_owner_str = current_owner.decode()
                            else:
                                current_owner_str = current_owner
                            
                            if current_owner_str == self.worker_id:
                                self.redis_client.delete(self.key)
                                logger.debug(f"Released LLM batch lock for {self.worker_id}")
                    except Exception as e:
                        logger.error(f"Error releasing LLM batch lock {self.key}: {e}")
        
        return LLMBatchLock(self.redis_client, self.LLM_BATCH_LOCK_KEY, timeout, self.worker_id)

    async def check_llm_batch_jobs(self):
        """Process pending LLM_BATCH_RUN jobs using distributed lock."""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # Try to acquire the lock
                with self._acquire_llm_batch_lock():
                    logger.debug(f"Acquired LLM batch lock for processing jobs (attempt {attempt + 1})")
                    
                    with Session(engine) as session:
                        # Find the first pending job with LLM_BATCH_RUN tag
                        statement = select(Job).where(
                            Job.tag == JobType.LLM_BATCH_RUN,
                            Job.status == JobStatus.PENDING
                        ).limit(1)
                        pending_job = session.exec(statement).first()
                        
                        if not pending_job:
                            # Log summary of all LLM batch jobs for monitoring
                            all_jobs_statement = select(Job).where(Job.tag == JobType.LLM_BATCH_RUN)
                            all_jobs = session.exec(all_jobs_statement).all()
                            
                            if all_jobs:
                                status_counts = {}
                                for job in all_jobs:
                                    status = job.status.value if job.status else "Unknown"
                                    status_counts[status] = status_counts.get(status, 0) + 1
                                
                                status_summary = ", ".join([f"{status}: {count}" for status, count in status_counts.items()])
                                logger.info(f"LLM_BATCH_RUN jobs - Total: {len(all_jobs)}, {status_summary} - No pending jobs to process")
                            else:
                                logger.info("No LLM_BATCH_RUN jobs found")
                            return
                        
                        # Find the corresponding BatchLLMQueue record
                        batch_record = session.exec(
                            select(BatchLLMQueue).where(BatchLLMQueue.job_id == pending_job.id)
                        ).first()
                        
                        if not batch_record:
                            logger.error(f"No BatchLLMQueue record found for job {pending_job.id}")
                            # Mark job as failed
                            pending_job.status = JobStatus.FAILED
                            pending_job.error_message = "No BatchLLMQueue record found"
                            session.add(pending_job)
                            session.commit()
                            return
                        
                        # Update job status to running and release lock
                        pending_job.status = JobStatus.RUNNING
                        session.add(pending_job)
                        session.commit()
                        session.refresh(pending_job)
                        
                        job_id = pending_job.id
                        users_list = batch_record.users_to_run
                        
                        logger.info(f"Processing LLM batch job {job_id} for users {users_list}")
                    
                    # Lock is released here, now process the job
                    await self._process_llm_batch_job(job_id, users_list)
                    return
                    
            except Exception as e:
                if "Failed to acquire" in str(e):
                    logger.debug(f"Could not acquire LLM batch lock (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Error processing LLM batch jobs (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
        
        logger.warning(f"Failed to process LLM batch jobs after {max_retries} attempts - lock may be held by another worker")

    async def _process_llm_batch_job(self, job_id: str, users_list: list):
        """Process a LLM batch job by running a simulation game with multiple users."""
        try:
            logger.info(f"Starting LLM batch simulation for job {job_id}, users: {users_list}")
            
            # Check if scaling is in progress
            if self.docker_pool_manager.redis_client.exists(self.docker_pool_manager.SCALING_LOCK_KEY):
                logger.info("Scaling in progress, marking job as failed")
                await self._update_job_failed(job_id, "Scaling in progress, cannot process job")
                return
            
            # Get users' tarstreams from Redis cache
            users_file = {}  # store users -> tarstream
            try:
                for username in users_list:
                    tarstream_bytes = self.redis_service.get_tarstream(username)
                    if tarstream_bytes is None:
                        raise Exception(f"No cached tarstream found for user {username}")
                    
                    # Convert bytes to BytesIO for use in container
                    users_file[username] = io.BytesIO(tarstream_bytes)
                    logger.info(f"Successfully retrieved cached tarstream for user {username}")
                        
            except Exception as e:
                logger.error(f"Failed to get cached tarstreams: {e}")
                await self._update_job_failed(job_id, f"Failed to get cached tarstreams: {str(e)}")
                return
            
            # Acquire container from pool
            logger.info("Acquiring container from pool...")
            port = self.docker_pool_manager.acquire_container(self.worker_id)
            
            if port is None:
                logger.error("No containers available in pool")
                await self._update_job_failed(job_id, "No containers available in pool")
                return
            
            logger.info(f"Successfully acquired container on port {port}")
            
            try:
                # Get container name and start game server
                game_server_name = self.docker_pool_manager.docker_service.get_game_server_container_name(port)
                
                # Start the game on the acquired container (6 rounds simulation)
                logger.info("Starting game on acquired container...")
                exec_command = f"python main.py --port={port} --sim --players={len(users_list)} --sim-rounds=1000 --log-file=/app/output/game.log"
                container = self.docker_pool_manager.docker_service._get_container(game_server_name)
                if container:
                    result = container.exec_run(exec_command, detach=True)
                    logger.info(f"Game started on container {game_server_name} for 6 rounds with {len(users_list)} players: {result}")
                else:
                    raise Exception("Container not found after acquisition")
                
                containers = []
                container_to_user = {}
                
                # Create container for each user
                try:
                    for username in users_list:
                        formatted_username = self.docker_pool_manager.docker_service.format_username(username)
                        user_bot_container_name = f"client_container_{port}_{formatted_username}"
                        logger.info(f"Starting user container: {user_bot_container_name}")
                        
                        # Store the container name
                        containers.append(user_bot_container_name)
                        container_to_user[user_bot_container_name] = username
                        
                        user_container = self.docker_pool_manager.docker_service.client.containers.run(
                            image=settings.RUNNER_IMAGE,
                            detach=True,
                            name=user_bot_container_name,
                            mem_limit="100m",
                        )
                        
                        await asyncio.sleep(2)
                        
                        if not self._check_container_health(user_bot_container_name):
                            raise Exception("User container failed to start properly")
                        
                        # Get user's tarstream and upload files
                        tarstream_clone = clone_bytes(users_file[username])
                        user_container.put_archive("/app", tarstream_clone)
                        
                        # Connect to network
                        self.docker_pool_manager.docker_service.connect_container_to_network(
                            settings.GAME_NETWORK_NAME, user_bot_container_name
                        )
                        
                        # Install packages
                        logger.info("Installing Python packages...")
                        out = self.docker_pool_manager.docker_service.install_python_package(user_bot_container_name)
                        if "error" in out.lower():
                            raise Exception(f"Package installation failed: {out}")
                        
                        logger.info("Package installation successful")
                        
                        # Execute the player bot
                        exec_command = f"python main.py --host={game_server_name} --port={port} -s True"
                        logger.info(f"Executing user bot: {exec_command}")
                        user_container.exec_run(exec_command, detach=True)
                
                except Exception as e:
                    logger.error(f"User container setup failed: {e}")
                    await self._update_job_failed(job_id, f"User container setup failed: {str(e)}")
                    return
                
                # Monitor game progress
                start_time = datetime.datetime.now()
                end_time = start_time + datetime.timedelta(seconds=settings.GAME_RUN_TIMEOUT)
                game_completed = False
                error = False
                
                logger.info("Running LLM batch simulation...")
                check_count = 0
                
                while datetime.datetime.now() < end_time:
                    try:
                        check_count += 1
                        logger.info(f"Checking game container status (attempt {check_count})...")
                        
                        # Check if all containers are still healthy
                        if not self._check_container_health(game_server_name):
                            raise Exception("Game server container died")
                        
                        stat = self.docker_pool_manager.docker_service.check_game_container_status(port, sim=True)
                        logger.info(f"Game status: {stat}")
                        
                        if stat == GameStatus.COMPLETED:
                            logger.info(f"LLM batch job {job_id}: Game completed.")
                            
                            # Save game logs first
                            try:
                                success, message = self.save_simulation_logs_from_container(game_server_name, port, job_id, users_list)
                                if success:
                                    logger.info(f"LLM batch job {job_id} successfully saved game logs: {message}")
                                else:
                                    logger.warning(f"LLM batch job {job_id} failed to save game logs: {message}")
                            except Exception as e:
                                logger.error(f"Error saving game logs for LLM batch job {job_id}: {e}")
                            
                            # Collect scores from all player containers
                            player_scores = {}
                            docker_service = self.docker_pool_manager.docker_service
                            
                            for username in users_list:
                                formatted_username = self.docker_pool_manager.docker_service.format_username(username)
                                user_bot_container_name = f"client_container_{port}_{formatted_username}"
                                try:
                                    score = docker_service.get_client_score(user_bot_container_name)
                                    player_scores[username] = score
                                    logger.info(f"Score for {username}: {score}")
                                except Exception as e:
                                    logger.warning(f"Failed to get score for {username}: {e}")
                                    player_scores[username] = 0
                            
                            # Convert to JSON string for storage
                            result_data = json.dumps(player_scores)
                            logger.info(f"Final player scores: {player_scores}")
                            
                            await self._update_job_status(job_id, JobStatus.FINISHED, result_data=result_data)
                            
                            game_completed = True
                            break
                            
                        elif stat == GameStatus.NON_EXISTENT:
                            raise Exception("Game server status check failed")
                        
                        await asyncio.sleep(5)  # Check every 5 seconds
                        
                    except Exception as e:
                        logger.error(f"Error during LLM batch game execution: {e}")
                        await self._update_job_failed(job_id, str(e))
                        game_completed = False
                        error = True
                        break
                
                if not game_completed and not error:
                    logger.error("LLM batch game run timed out.")
                    await self._update_job_failed(job_id, "Game run timed out.")
                
                # Cleanup containers
                logger.info("Cleaning up containers...")
                self._cleanup_containers(containers)
                
            finally:
                # Always release container back to pool
                self.docker_pool_manager.release_container(port, self.worker_id)
                logger.info(f"Released container on port {port} back to pool")
            
            logger.info(f"LLM batch simulation task {job_id} completed.")
            
        except Exception as e:
            logger.error(f"Failed to process LLM batch job {job_id}: {e}")
            await self._update_job_failed(job_id, str(e))

    async def process_message(self, data: dict):
        """
        Process the incoming message.
        This method should be implemented by subclasses.
        """
        logger.info(f"Processing simulation task: {data['job_id']} from {self.name}")

        message_type = data['type']

        logger.info(f"Message type: {message_type}")

        handlers = {
            SimulationMessageType.RUN.value: self._handle_run,
            SimulationMessageType.RUN_USER.value: self._handle_run_user, # points RUN_USER enum val to _handle_run_user function
            SimulationMessageType.SCALE_DOCKER.value: self._handle_scale_docker
        }

        handler = handlers.get(message_type)

        if handler:
            await handler(data)
        else:
            logger.error(f"Unknown message type: {message_type}")

    async def _safe_exec_run(self, container, command, timeout_seconds=300):
        """Execute command in container with timeout protection."""
        try:
            logger.info(f"Executing command in container {container.name}: {command}")
            
            # Use asyncio.wait_for to add timeout
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(None, lambda: container.exec_run(command))
            
            try:
                exit_code, output = await asyncio.wait_for(future, timeout=timeout_seconds)
                output_text = output.decode("utf-8") if output else ""
                logger.info(f"Command completed with exit code {exit_code}: {output_text[:200]}...")
                return exit_code, output_text
            except asyncio.TimeoutError:
                logger.error(f"Command timed out after {timeout_seconds} seconds: {command}")
                return -1, f"Command timed out after {timeout_seconds} seconds"
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return -1, str(e)

    def _check_container_health(self, container_name: str) -> bool:
        """Check if container is running and healthy."""
        try:
            container = self.docker_pool_manager.docker_service._get_container(container_name)
            if not container:
                logger.error(f"Container {container_name} not found")
                return False
            
            container.reload()  # Refresh container state
            status = container.status
            logger.info(f"Container {container_name} status: {status}")
            
            if status != "running":
                # Get container logs for debugging
                try:
                    logs = container.logs(tail=50).decode("utf-8")
                    logger.error(f"Container {container_name} logs: {logs}")
                except Exception as e:
                    logger.error(f"Failed to get logs for {container_name}: {e}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Health check failed for {container_name}: {e}")
            return False

    async def _ensure_channel_ready(self) -> bool:
        """Ensure channel is ready for use, reconnect if necessary."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Check if channel exists and is not closed
                if self.channel and not self.channel.is_closed:
                    # Test the channel by getting the default exchange
                    try:
                        await self.channel.get_exchange("", passive=True)
                        return True
                    except Exception:
                        # Channel exists but is not functional, mark as closed
                        logger.warning("Channel exists but is not functional, will reconnect")
                
                # Channel is None, closed, or not functional - need to reconnect
                logger.info(f"Channel is not ready, attempting to reconnect (attempt {attempt + 1}/{max_retries})...")
                
                # Close existing connections cleanly
                if self.channel and not self.channel.is_closed:
                    try:
                        await self.channel.close()
                    except:
                        pass
                        
                if self.connection and not self.connection.is_closed:
                    try:
                        await self.connection.close()
                    except:
                        pass
                
                # Reset connection objects
                self.connection = None
                self.channel = None
                
                # Attempt reconnection
                await self.connect()
                
                # Verify the connection worked
                if self.channel is not None and not self.channel.is_closed:
                    try:
                        # Test the channel
                        await self.channel.get_exchange("", passive=True)
                        logger.info("Channel reconnection successful")
                        return True
                    except Exception as e:
                        logger.error(f"Channel test failed after reconnection: {e}")
                
            except asyncio.CancelledError:
                logger.warning("Channel reconnection was cancelled")
                return False
            except Exception as e:
                logger.error(f"Failed to ensure channel ready (attempt {attempt + 1}): {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        logger.error(f"Failed to establish channel after {max_retries} attempts")
        return False

    async def _safe_requeue_message(self, data: dict, context: str = "simulation") -> bool:
        """Safely requeue a message with proper error handling."""
        try:
            # Add delay to prevent immediate retry
            await asyncio.sleep(5)
            
            # Ensure we have a valid channel
            if not await self._ensure_channel_ready():
                logger.error(f"[{context.upper()}] Could not establish valid channel for requeue")
                return False
            
            # Prepare message
            message_body = json.dumps(data).encode()
            
            # Get exchange and publish
            exchange = await self.channel.get_exchange("")
            await exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=self.queue_name
            )
            
            logger.info(f"[{context.upper()}] Successfully requeued job {data['job_id']}")
            return True
            
        except asyncio.CancelledError:
            logger.warning(f"[{context.upper()}] Requeue operation was cancelled")
            return False
        except Exception as e:
            logger.error(f"[{context.upper()}] Failed to requeue message: {e}")
            return False
    
            
    async def _handle_scale_docker (self, data: dict):
        """
            Handle scale docker message type
            Determine type of scaling based on current total container and target size.
        """
        try:
            with self.docker_pool_manager._acquire_scaling_lock():
                logger.info("Scaling lock acquired")

                job_id = data['job_id']
                target_size = data['target_size']

                # Update job db to running ---------------------------------------
                try:
                    with Session(engine) as session:
                        job = session.exec(select(Job).where(Job.id == job_id)).first()
                        logger.info(f"Queried job: {job}")
                        if not job:
                            logger.error(f"Job ID {job_id} not found in the database.")
                            return
                    
                        job.status = JobStatus.RUNNING
                        session.add(job)
                        logger.info("Added job with updated status, about to commit...")

                        try: 
                            session.commit()
                            logger.info("Commit succeeded")
                            session.refresh(job)
                        except Exception as e:
                            logger.error(f"❌ Commit failed: {e}")
                            traceback.print_exc()
                except Exception as e:
                    logger.error(f"❌ Outer DB error: {e}")
                    traceback.print_exc()

                # Get Pool information and determine scaling ----------------------------
                pool_manager = self.docker_pool_manager
                status = pool_manager.get_pool_status()
                total_containers = status['total_containers']

                if (total_containers == target_size):
                    # No Scale
                    logger.info("No scaling needed, pool already at target size")
                    await self._commit_scale_finished(job_id, "Pool already at target size")
                    return
                elif (target_size > total_containers):
                    # Scale up
                    logger.info(f"Scaling UP from {total_containers} → {target_size}")
                    await self._scale_up_docker(data, total_containers)
                    return
                elif (target_size < total_containers):
                    # Scale down
                    logger.info(f"Scaling DOWN from {total_containers} → {target_size}")
                    await self._scale_down_docker(data, total_containers)
        except Exception as e:
            logger.warning(f"Skipped scaling job: {e}")
            await self._commit_scale_failed(data["job_id"], str(e))
        
    
    async def _scale_up_docker(self, data: dict, total_containers: int):
        """
            Scale up container up to target_size
        """
        job_id = data['job_id']
        target_size = data['target_size']
        logger.info(f"Starting scale-up: need {target_size - total_containers} new containers") 

        try:
            # Adding container up to target_size
            for _ in range(target_size - total_containers):
                if not self.docker_pool_manager._add_container_to_pool():
                    raise Exception("add_container_to_pool failed")
            
            logger.info("Scale-up finished, committing success")
            await self._commit_scale_finished(job_id, "Scale up completed successfully.")
            return

        except Exception as e:
            logger.error(f"Scale-up error: {e}")
        
        curr_status = self.docker_pool_manager.get_pool_status()
        curr_total_container = curr_status['total_containers']
        if (curr_total_container < target_size):
            await self._requeue_scale_job(data)
            return

    async def _scale_down_docker(self, data: dict, total_containers: int):
        """
            Scale down container up to target_size
        """
        job_id = data['job_id']
        target_size = data['target_size']

        # Get num of containers to be removed
        to_remove_count = total_containers - target_size
        logger.info(f"Need to remove {to_remove_count} containers")

        # Remove idle containers first
        try: 
            idle_containers = self.docker_pool_manager._get_pool_containers()
            for container in idle_containers:
                if to_remove_count == 0:
                    await self._commit_scale_finished(job_id, "Scale down completed successfully.")
                    return
                
                logger.info(f"Removing idle {container.container_name}")
                self.docker_pool_manager._remove_container_from_pool(container)
                to_remove_count -= 1
        except Exception as e:
            logger.error(f"Error removing idle containers: {e}") 
        
        # Remove active containers if needed
        try:
            if (to_remove_count == 0):
                await self._commit_scale_finished(job_id, "Scale down completed successfully.")
                return
            elif (to_remove_count > 0):
                active_containers = self.docker_pool_manager._get_active_containers()
                for container in active_containers:
                    if to_remove_count == 0:
                        await self._commit_scale_finished(job_id, "Scale down completed successfully.")
                        return
                    
                    game_status = self.docker_pool_manager.docker_service.check_game_container_status(container.port, sim=self.sim_mode)
                    if game_status == GameStatus.IN_PROGRESS:
                        logger.info(f"Container {container.container_name} is running a game, skip")
                        continue
                    else:
                        logger.info(f"Removing active {container.container_name}") 
                        self.docker_pool_manager._remove_container_from_pool(container)
                        to_remove_count -= 1

        except Exception as e:
            logger.error(f"Error removing active containers: {e}")
        
        if (to_remove_count == 0):
            await self._commit_scale_finished(job_id, "Scale down completed successfully.")
            return
        elif (to_remove_count > 0):
            await self._requeue_scale_job(data)
            return

    async def _requeue_scale_job(self, data: dict) -> None:
        job_id = data['job_id']
        job_retries = data['job_retries']
        target_size = data['target_size']

        if job_retries >= settings.SCALE_DOCKER_MAX_RETRIES:
            # case where scaling down is not done yet 
            # if already 3 retries, set job to failed
            curr_status = self.docker_pool_manager.get_pool_status()
            curr_total_container = curr_status['total_containers']
            failed_message = f"""
                            Scaling failed after {settings.SCALE_DOCKER_MAX_RETRIES} retries.
                            Target size: {target_size}, Current size: {curr_total_container}.
                            """
            await self._commit_scale_failed(job_id, failed_message)
        else:
            # send back to the queue for retries
            data["job_retries"] += 1
            
            success = await self._safe_requeue_message(data, context="scale")
            
            if success:
                logger.info(
                    f"[SCALE] Re-queued job {data['job_id']} "
                    f"(retry {data['job_retries']})"
                )
            else:
                logger.error(f"[SCALE] Failed to re-queue job {job_id}")
                self._commit_scale_failed(
                    job_id,
                    "Scale operation failed and could not be re-queued"
                )

    async def _commit_scale_finished(self, job_id: int, message: str): 
        """
            Set job DB to finished
        """
        try:
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                job.status = JobStatus.FINISHED
                job.result_data = message
                session.add(job)
                session.commit()
                session.refresh(job)
        except Exception as e:
            logger.error(f"❌ Outer DB error: {e}")
            traceback.print_exc()
    
    async def _commit_scale_failed(self, job_id: int, message: str): 
        """
            Set job DB to failed
        """
        try:
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                job.status = JobStatus.FAILED
                job.result_data = message
                job.error_message = message
                session.add(job)
                session.commit()
                session.refresh(job)
        except Exception as e:
            logger.error(f"❌ Outer DB error: {e}")
            traceback.print_exc()
    
    
    async def _handle_run_user(self, data: dict):
        """
            Handle run_user message type.
            Start simulation run on the listed users
        """

        print(f"Running simulation for job ID: {data['job_id']}")
        logger.info(f"Received data from queue: {data}")
        
        # Block message during scaling
        if self.docker_pool_manager.redis_client.exists(self.docker_pool_manager.SCALING_LOCK_KEY):
            logger.info("Scaling in progress, requeueing simulation")
            await self._requeue_message(data)
            return
        
        job_id = data['job_id']
        users_list = data['users_list']
        num_rounds = data.get('num_rounds', 6)
        blind = data.get('blind', None)
        blind_multiplier = data.get('blind_multiplier', None)
        blind_increase_interval = data.get('blind_increase_interval', None)
        logger.info(f"Extracted parameters: blind={blind}, blind_multiplier={blind_multiplier}, blind_increase_interval={blind_increase_interval}")
        logger.info(f"Worker {self.name} processing job {job_id} to run {num_rounds} rounds between users: {users_list}")

        # Update the job db status to running --------------------------
        try:
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                logger.info(f"Queried job: {job}")
                if not job:
                    logger.error(f"Job ID {job_id} not found in the database.")
                    return

                job.status = JobStatus.RUNNING
                session.add(job)
                logger.info("Added job with updated status, about to commit...")

                try:
                    session.commit()
                    logger.info("Commit succeeded")
                    session.refresh(job)
                except Exception as e:
                    logger.error(f"❌ Commit failed: {e}")
                    traceback.print_exc()
        except Exception as e:
            logger.error(f"❌ Outer DB error: {e}")
            traceback.print_exc()


        # Download final submission files from list of users -----------------------------------
        users_file = {} # store users -> tarstream
        try:
            with Session(engine) as session:
                for username in users_list:
                    #  Get file path
                    python_file_path = session.exec(select(Submission.player_file).
                        where(Submission.username == username, Submission.final == True)).first()
                    packages_file_path = session.exec(select(Submission.package_file).
                        where(Submission.username == username, Submission.final == True)).first()
                    
                    # file path check
                    if not python_file_path or not packages_file_path:
                        raise Exception(f"Missing file path(s) for user {username}")
                            
                    # Download file bytes from supabase
                    try:
                        python_file_bytes = bucket_service.download_file(python_file_path)
                        packages_file_bytes = bucket_service.download_file(packages_file_path)
                    except Exception as e:
                        raise Exception(f"Download failed for user {username}: {e}") from e

                    # convert bytes into files
                    with open("player.py", "wb") as f:
                        f.write(python_file_bytes)

                    with open("requirements.txt", "wb") as f:
                        f.write(packages_file_bytes)
                    
                    with open("player.py", "rb") as player_file, open("requirements.txt", "rb") as packages_file:
                        tarstream = create_tar_from_files({
                            "player.py": SimpleNamespace(file=player_file),
                            "requirements.txt": SimpleNamespace(file=packages_file)
                        })

                    # store user -> tarstream in the dict
                    users_file[username] = tarstream 
        except Exception as e:
            logger.error(f"Downloading file failed for user {username}: {e}")
            with Session(engine) as session:
                job.status = JobStatus.FAILED
                job.error_message = f"Downloading file failed for user {username}: {str(e)}"
                session.add(job)
                session.commit()
                session.refresh(job)
            return
            
        
        # Start game server ------------------------------------------------------------
        logger.info("Starting game server...")
        port = self.docker_pool_manager.acquire_container(self.worker_id)
        
        if port is None:
            logger.error("No containers available in pool, requeuing message...")
            await self._requeue_message(data)
            return

        logger.info(f"Successfully acquired container on port {port}")

        # Get container name
        game_server_name = self.docker_pool_manager.docker_service.get_game_server_container_name(port)

        # Start the game on the acquired container
        logger.info("Starting game on acquired container...")
        try:
            logger.info(f"Blind parameters: blind={blind}, blind_multiplier={blind_multiplier}, blind_increase_interval={blind_increase_interval}")
            exec_command = f"python main.py --port={port} --sim --players={len(users_list)} --sim-rounds={num_rounds} --log-file=/app/output/game.log"
            if blind is not None:
                exec_command += f" --blind={blind}"
                logger.info(f"Added blind parameter: {blind}")
            if blind_multiplier is not None:
                exec_command += f" --blind-multiplier={blind_multiplier}"
                logger.info(f"Added blind_multiplier parameter: {blind_multiplier}")
            if blind_increase_interval is not None:
                exec_command += f" --blind-increase-interval={blind_increase_interval}"
                logger.info(f"Added blind_increase_interval parameter: {blind_increase_interval}")
            
            container = self.docker_pool_manager.docker_service._get_container(game_server_name)
            if container:
                logger.info(f"Final command to execute: {exec_command}")
                result = container.exec_run(exec_command, detach=True)
                logger.info(f"Exec_run result: {result}")
                logger.info(f"Game started on container {game_server_name} for {num_rounds} rounds with command: {exec_command}")
            else:
                raise Exception("Container not found after acquisition")
        except Exception as e:
            logger.error(f"Failed to start game on container: {e}")
            self.docker_pool_manager.release_container(port, self.worker_id)
            await self._update_job_failed(job_id, str(e))
            return

        containers = []
        container_to_user = {} 
        tasks = {} # store user -> task
        # Create container for each user -------------------------------------------------------------
        try:
            # Setup the container and run the file
            for username in users_list:
                formatted_username = self.docker_pool_manager.docker_service.format_username(username)
                user_bot_container_name = f"client_container_{port}_{formatted_username}"
                logger.info(f"Starting user container: {user_bot_container_name}")
                # Store the container name
                containers.append(user_bot_container_name)
                container_to_user[user_bot_container_name] = username

                user_container = self.docker_pool_manager.docker_service.client.containers.run(
                    image=settings.RUNNER_IMAGE,
                    detach=True,
                    name=user_bot_container_name,
                    mem_limit="100m",
                )
                
                await asyncio.sleep(2)
                
                if not self._check_container_health(user_bot_container_name):
                    raise Exception("User container failed to start properly")

                # Get users file
                tarstream_clone = clone_bytes(users_file[username])
                user_container.put_archive("/app", tarstream_clone)

                self.docker_pool_manager.docker_service.connect_container_to_network(
                    settings.GAME_NETWORK_NAME, user_bot_container_name
                )

                # Install packages with timeout protection
                logger.info("Installing Python packages...")
                out = self.docker_pool_manager.docker_service.install_python_package(user_bot_container_name)
                if "error" in out.lower():
                    raise Exception(f"Package installation failed: {out}")
                    
                logger.info("Package installation successful")

                # Execute the player bot
                exec_command = f"python main.py --host={game_server_name} --port={port} -s True"
                logger.info(f"Executing user bot: {exec_command}")
                
                # Use timeout protection for user bot execution
                # temp_task = asyncio.create_task(self._safe_exec_run(user_container, exec_command, timeout_seconds = settings.SAFE_EXEC_TIMEOUT))
                # tasks[username] = temp_task
                user_container.exec_run(exec_command, detach=True)
            
            # # Track user bot status
            # for username, task in tasks.items():
            #     try:
            #         exit_code, output = await task
            #         if exit_code != 0:
            #             logger.error(f"User bot execution failed for {username}: {output}")
            #         else:
            #             logger.info(f"User bot executed successfully for {username}")
            #     except Exception as e:
            #         logger.error(f"Error awaiting user bot execution for {username}: {e}")

        except Exception as e:
            logger.error(f"User container setup failed: {e}")
            with Session(engine) as session:
                job.status = JobStatus.FAILED
                job.error_message = f"User container setup failed: {str(e)}"
                session.add(job)
                session.commit()
                session.refresh(job)
            return

        # Monitor game progress -------------------------------------------------------------
        users_result = {} # store user -> score

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=settings.GAME_RUN_TIMEOUT)
        game_completed = False
        error = False

        logger.info("Running simulation...")
        check_count = 0
        
        while datetime.datetime.now() < end_time:
            try:
                check_count += 1
                logger.info(f"Checking game container status (attempt {check_count})...")
                
                # Check if all containers are still healthy
                if not self._check_container_health(game_server_name):
                    raise Exception("Game server container died")
                    
                stat = self.docker_pool_manager.docker_service.check_game_container_status(port, sim=True)
                logger.info(f"Game status: {stat}")
                
                if stat == GameStatus.COMPLETED:
                    # Get result of all the users
                    logger.info(f"Job {job_id}: Game completed. Retrieving log file from {game_server_name}...")

                    success, message = self.save_simulation_logs_from_container(game_server_name, port, job_id, users_list)

                    if success:
                        logger.info(f"Job {job_id} successfully saved game logs: {message}")
                        
                        # Collect scores from all player containers
                        player_scores = {}
                        docker_service = self.docker_pool_manager.docker_service
                        
                        for username in users_list:
                            formatted_username = self.docker_pool_manager.docker_service.format_username(username)
                            user_bot_container_name = f"client_container_{port}_{formatted_username}"
                            try:
                                score = docker_service.get_client_score(user_bot_container_name)
                                player_scores[username] = score
                                logger.info(f"Score for {username}: {score}")
                            except Exception as e:
                                logger.warning(f"Failed to get score for {username}: {e}")
                                player_scores[username] = 0
                        
                        # Convert to JSON string for storage
                        result_data = json.dumps(player_scores)
                        logger.info(f"Final player scores: {player_scores}")
                        
                        await self._update_job_status(job_id, JobStatus.FINISHED, result_data=result_data)
                    else:
                        await self._update_job_failed(job_id, f"Failed to save game log: {message}")
                    
                    game_completed = True
                    break
                elif stat == GameStatus.NON_EXISTENT:
                    raise Exception("Game server status check failed")
                
                await asyncio.sleep(5)  # Check every 5 seconds instead of 1
                
            except Exception as e:
                logger.error(f"Error during game execution: {e}")
                await self._update_job_failed(job_id, str(e))
                game_completed = False
                error = True
                break

        if not game_completed and not error:
            logger.error("Game run timed out.")
            await self._update_job_failed(job_id, "Game run timed out.")
        
        # Teardown -----------------------------------------------------        
        logger.info("Cleaning up containers...")
        self._cleanup_containers(containers)

        # Release container back to pool
        self.docker_pool_manager.release_container(port, self.worker_id)
        logger.info(f"Released container on port {port} back to pool")
        
        logger.info(f"Simulation task {data['job_id']} completed.")

    def save_simulation_logs_from_container(self, container_name: str, port: int, job_id: str, users_list: list) -> Tuple[bool, str]:
        """
        Retrieves an aggregated simulation log file from a container and saves each game log into the db.
        """
        docker_service = self.docker_pool_manager.docker_service
        
        # Create username to player ID mapping using actual connection logs
        username_to_player_id = {}
        for username in users_list:
            formatted_username = self.docker_pool_manager.docker_service.format_username(username)
            user_bot_container_name = f"client_container_{port}_{formatted_username}"
            player_id = docker_service.extract_player_id_from_log(user_bot_container_name)
            if player_id is not None:
                username_to_player_id[username] = player_id
                logger.info(f"Player ID: {username} -> {player_id}")
            else:
                logger.warning(f"Failed to extract player ID for {username}")
        
        try:
            container = docker_service._get_container(container_name)
            if not container:
                return False, f"Container '{container_name}' not found."
            
            ls_command = "ls /app/output"
            exit_code, output = container.exec_run(cmd=ls_command)
            if exit_code != 0:
                return False, f"Could not list files in /app/output: {output.decode()}"
            
            files = output.decode().splitlines()
            game_log_files = [f for f in files if f.startswith("game_log_") and f.endswith(".json")]
            
            if not game_log_files:
                return False, "No game log files found in container output."
            
            # Read all game log files and create a mapping
            games_map = {}
            
            for log_filename in game_log_files:
                try:
                    # Extract game number from filename (e.g., game_log_1_uuid.json -> 1)
                    game_num = int(log_filename.split("_")[2])
                    
                    log_filepath = f"/app/output/{log_filename}"
                    bits, stat = container.get_archive(log_filepath)

                    file_obj = io.BytesIO()
                    for chunk in bits:
                        file_obj.write(chunk)
                    file_obj.seek(0)

                    with tarfile.open(fileobj=file_obj) as tar:
                        member = tar.getmembers()[0]
                        extracted_file = tar.extractfile(member)
                        if not extracted_file:
                            logger.warning(f"Failed to extract {log_filename}")
                            continue
                        
                        game_data = json.loads(extracted_file.read().decode('utf-8'))
                        games_map[game_num] = game_data
                        
                except (ValueError, IndexError, KeyError) as e:
                    logger.warning(f"Failed to process {log_filename}: {e}")
                    continue
            
            if not games_map:
                return False, "No valid game data found in log files."
            
            logger.info(f"Successfully read {len(games_map)} games: {sorted(games_map.keys())}")
            
            # Convert the games_map to a list for processing (maintain existing logic)
            list_of_games = [games_map[i] for i in sorted(games_map.keys())]
            
            saved_uuids = []
            with Session(engine) as session:
                for i, game_data in enumerate(list_of_games, 1):
                    game_uuid_str = str(i)
                    
                    # Use the direct username to player ID mapping from connection logs
                    # Create reverse mapping (player_id -> username) for the game data
                    player_id_to_username = {str(player_id): username for username, player_id in username_to_player_id.items()}
                    
                    game_data["usernameMapping"] = username_to_player_id
                    game_data["playerIdToUsername"] = player_id_to_username
                    game_uuid_obj = uuid.uuid4()

                    if session.get(GameLog, game_uuid_obj):
                        logger.warning(f"Game log {game_uuid_obj} already exists. Skipping.")
                        continue
            
                    new_log = GameLog(id=game_uuid_obj, game_uuid=game_uuid_str, game_data=game_data, job_id=job_id)
                    session.add(new_log)
                    saved_uuids.append(str(game_uuid_obj))

                session.commit()
            
            return True, f"Successfully saved {len(saved_uuids)} game logs."
        
        except Exception as e:
            logger.error(f"Exception in save_simulation_logs_from_container: {e}")
            return False, str(e)
        
    async def _update_job_status(self, job_id: str, status: JobStatus, result_data: str = None):
        """
        Helper for updating job status.
        """
        try:
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if job:
                    job.status = status
                    if result_data:
                        job.result_data = result_data
                    session.add(job)
                    session.commit()
        except Exception as e:
            logger.error(f"Failed to update job status for {job_id}: {e}")

    async def _handle_run(self, data: dict):
        """
        Handle the run message type with Docker container pooling.
        """
        logger.info(f"Running simulation for job ID: {data['job_id']}")
        # Block message during scaling
        if self.docker_pool_manager.redis_client.exists(self.docker_pool_manager.SCALING_LOCK_KEY):
            logger.info("Scaling in progress, requeueing simulation")
            await self._requeue_message(data)
            return

        # Extract and decode tarstream
        tar_encoded = data["tarstream"]
        tar_bytes = base64.b64decode(tar_encoded)
        tarstream = io.BytesIO(tar_bytes)
        tarstream_verify = clone_bytes(tarstream)
        tarstream_clone = clone_bytes(tarstream)

        logger.info("Decoded tarstream successfully.")

        job_id = data["job_id"]
        username = data["username"]

        # Update job status to running
        try:
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                logger.info(f"Queried job: {job}")
                if not job:
                    logger.error(f"Job ID {job_id} not found in the database.")
                    return

                job.status = JobStatus.RUNNING
                session.add(job)
                logger.info("Added job with updated status, about to commit...")

                try:
                    session.commit()
                    logger.info("Commit succeeded")
                    session.refresh(job)
                except Exception as e:
                    logger.error(f"❌ Commit failed: {e}")
                    traceback.print_exc()
        except Exception as e:
            logger.error(f"❌ Outer DB error: {e}")
            traceback.print_exc()

        # Verify content first with a test container - FAST FAIL before any resource allocation
        logger.info("Creating test container for file verification...")
        formatted_username = self.docker_pool_manager.docker_service.format_username(username)
        run_uuid_obj = uuid.uuid4()
        test_container_name = f"verify_test_{job_id}_{formatted_username}_{run_uuid_obj}_{str(run_uuid_obj)[:8]}"
        try:
            test_container = self.docker_pool_manager.docker_service.client.containers.run(
                image=settings.RUNNER_IMAGE,
                detach=True,
                name=test_container_name,
                mem_limit="100m",
            )
            
            # Upload files to test container
            test_container.put_archive("/app", tarstream_verify)
            
            # Verify content
            logger.info("Verifying uploaded files...")
            ok, err = check_input_stat(self.docker_pool_manager.docker_service, test_container_name)
            
            # Clean up test container immediately
            self.docker_pool_manager.docker_service.stop_and_remove_container(test_container_name)
            
            if not ok:
                logger.error(f"File verification failed: {err}")
                await self._update_job_failed(job_id, f"File verification failed: {err}")
                return
            
            logger.info("File verification passed, proceeding with simulation...")
            
        except Exception as e:
            # Ensure test container is cleaned up even on error
            try:
                self.docker_pool_manager.docker_service.stop_and_remove_container(test_container_name)
            except:
                pass
            logger.error(f"Verification setup failed: {e}")
            await self._update_job_failed(job_id, f"Verification setup failed: {str(e)}")
            return

        # Try to acquire a container from the pool
        logger.info("Attempting to acquire container from pool...")
        port = self.docker_pool_manager.acquire_container(self.worker_id)
        
        if port is None:
            logger.error("No containers available in pool, requeuing message...")
            await self._requeue_message(data)
            return

        logger.info(f"Successfully acquired container on port {port}")

        # Get container name
        game_server_name = self.docker_pool_manager.docker_service.get_game_server_container_name(port)

        # Start the game on the acquired container
        logger.info("Starting game on acquired container...")
        try:
            exec_command = f"python main.py --port={port} --sim --players={settings.BOT_NUMBER_PER_GAME_SIMULATION + 1}"
            container = self.docker_pool_manager.docker_service._get_container(game_server_name)
            if container:
                container.exec_run(exec_command, detach=True)
                logger.info(f"Game started on container {game_server_name}")
            else:
                raise Exception("Container not found after acquisition")
        except Exception as e:
            logger.error(f"Failed to start game on container: {e}")
            self.docker_pool_manager.release_container(port, self.worker_id)
            await self._update_job_failed(job_id, str(e))
            return

        # Start bot containers
        containers = []
        try:
            formatted_username = self.docker_pool_manager.docker_service.format_username(username)
            for i in range(settings.BOT_NUMBER_PER_GAME_SIMULATION):
                bot_container_name = f"client_container_{port}_{formatted_username}_bot{i}"
                containers.append(bot_container_name)
                self.docker_pool_manager.docker_service.start_client_container(
                    game_server_name, port, f"{username}_bot{i}", sim=True
                )
        except Exception as e:
            logger.error(f"Failed to start bot containers: {e}")
            self._cleanup_containers(containers + [game_server_name])
            self.docker_pool_manager.release_container(port, self.worker_id)
            await self._update_job_failed(job_id, str(e))
            return

        # Start user container
        user_bot_container_name = f"client_container_{port}_{formatted_username}"
        try:
            user_container = self.docker_pool_manager.docker_service.client.containers.run(
                image=settings.RUNNER_IMAGE,
                detach=True,
                name=user_bot_container_name,
                mem_limit="100m",
            )

            user_container.put_archive("/app", tarstream_clone)

            self.docker_pool_manager.docker_service.connect_container_to_network(
                settings.GAME_NETWORK_NAME, user_bot_container_name
            )

            # Install packages
            out = self.docker_pool_manager.docker_service.install_python_package(user_bot_container_name)
            if "error" in out.lower():
                raise Exception(f"Package installation failed: {out}")

            # Execute the player bot
            exec_command = f"python main.py --host={game_server_name} --port={port} -s True"
            user_container.exec_run(exec_command, detach=True)

        except Exception as e:
            logger.error(f"Failed to start user container: {e}")
            containers.append(user_bot_container_name)
            self._cleanup_containers(containers + [game_server_name])
            self.docker_pool_manager.release_container(port, self.worker_id)
            await self._update_job_failed(job_id, str(e))
            return

        # Monitor game execution
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=settings.GAME_RUN_TIMEOUT)

        game_completed = False
        error = False

        logger.info("Running simulation...")
        while datetime.datetime.now() < end_time:
            try:
                logger.info("Checking game container status...")
                stat = self.docker_pool_manager.docker_service.check_game_container_status(port, sim=True)
                if stat == GameStatus.COMPLETED:
                    score = self.docker_pool_manager.docker_service.get_client_score(user_bot_container_name)
                    await self._update_job_completed(job_id, score)
                    game_completed = True
                    break
                elif stat == GameStatus.NON_EXISTENT:
                    raise Exception("Game server status check failed")
                await asyncio.sleep(5) 
            except Exception as e:
                logger.error(f"Error during game execution: {e}")
                await self._update_job_failed(job_id, str(e))
                error = True
                break

        if not game_completed and not error:
            logger.error("Game run timed out.")
            await self._update_job_failed(job_id, "Game run timed out.")

        # Cleanup
        containers.append(user_bot_container_name)
        self._cleanup_containers(containers)
        
        # Release container back to pool
        self.docker_pool_manager.release_container(port, self.worker_id)
        logger.info(f"Released container on port {port} back to pool")
        
        logger.info(f"Simulation task {data['job_id']} completed.")

    async def _requeue_message(self, data: dict):
        """Requeue the message when no containers are available."""
        success = await self._safe_requeue_message(data, context="simulation")
        
        if success:
            logger.info(f"Message for job {data['job_id']} requeued due to no available containers")
        else:
            logger.error(f"Failed to requeue message for job {data['job_id']}")
            # If requeuing fails, mark job as failed
            await self._update_job_failed(data['job_id'], "Failed to acquire container and requeue failed")

    async def _update_job_completed(self, job_id: str, result_data):
        """Update job status to completed and add leaderboard entry for async_run jobs."""
        try:
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                if job:
                    job.status = JobStatus.FINISHED
                    job.result_data = json.dumps({job.username: result_data}) if isinstance(result_data, (int, float)) else result_data
                    session.add(job)
                    session.commit()
                    session.refresh(job)
                    
                    # Create leaderboard entry for successful async_run simulation
                    # Extract score from result_data JSON format: {username: score}
                    try:
                        if isinstance(result_data, (int, float)):
                            score = result_data
                        else:
                            # Parse the JSON result_data which is in format {username: score}
                            result_dict = json.loads(job.result_data) if isinstance(job.result_data, str) else job.result_data
                            score = result_dict.get(job.username, 0) if isinstance(result_dict, dict) else 0
                    except (json.JSONDecodeError, AttributeError, TypeError):
                        score = 0
                        logger.warning(f"Could not parse score from result_data for job {job_id}, using default score 0")
                    
                    leaderboard_entry = LeaderBoard(
                        username=job.username,
                        score=score,
                        tag="dev_2025"
                    )
                    session.add(leaderboard_entry)
                    session.commit()
                    session.refresh(leaderboard_entry)
                    
                    logger.info(f"Job completed successfully. Added leaderboard entry for {job.username} with score {score} and tag 'dev_2025'")
        except Exception as e:
            logger.error(f"Failed to update job status to completed: {e}")

    async def _update_job_failed(self, job_id: str, error_message: str):
        """Update job status to failed."""
        try:
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = error_message
                    session.add(job)
                    session.commit()
                    session.refresh(job)
                    logger.error(f"Job failed: {error_message}")
        except Exception as e:
            logger.error(f"Failed to update job status to failed: {e}")

    def _cleanup_containers(self, container_names: list):
        """Clean up containers using ThreadPoolExecutor."""
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.docker_pool_manager.docker_service.stop_and_remove_container, name) 
                      for name in container_names]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error tearing down container: {e}")



        