import io
import random
import threading
from typing import Dict, Optional, Tuple
import docker
import logging
from docker.models.containers import Container
from docker.errors import ImageNotFound, NotFound, APIError
import tarfile
import json
import uuid
from sqlmodel import Session, select
from app.service.db.postgres import engine

from app.config.setting import settings
from app.models.game import GameStatus, GameLog

logger = logging.getLogger(__name__)


class DockerService:
    """
    Singleton service for managing Docker containers and networks for game environments.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DockerService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        
        self.client = docker.from_env()
        self._initialized = True
        self.use_ports = set()
        self._port_lock = threading.Lock()

        # Initialize environment
        self._setup_environment()

    def format_username(self, username: str) -> str:
        """Format username by replacing spaces with 'gspaceg' for use in container names."""
        return username.replace(" ", "gspaceg")

    def _setup_environment(self) -> None:
        """Initialize Docker environment with required network and images."""
        try:
            # Create game network
            self.create_network(settings.GAME_NETWORK_NAME)

            # Pull required images
            self._pull_image(settings.GAME_ENGINE_IMAGE)
            self._pull_image(settings.RUNNER_IMAGE)
        except Exception as e:
            logger.error(f"Failed to setup Docker environment: {str(e)}")
            raise

    def get_all_containers_live_status(self) -> Dict[str, str]:
        """Get the status of all containers."""
        try:
            containers = self.client.containers.list(all=True)
            return {container.name: container.status for container in containers}
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
            return {}
        
    def generate_random_port(self) -> int:
        """Generate and reserve a random port for a game server."""
        with self._port_lock:
            while True:
                port = random.randint(settings.GAME_ENGINE_PORT_START, settings.GAME_ENGINE_PORT_END)
                if port not in self.use_ports:
                    self.use_ports.add(port)
                    return port

    def release_port(self, port: int) -> None:
        """Release a previously reserved port."""
        with self._port_lock:
            self.use_ports.discard(port)
        
    def _pull_image(self, image_name: str, force: bool = False) -> None:
        """Pull a Docker image if it doesn't exist or if forced."""
        try:
            if force:
                logger.info(f"Forcibly pulling image '{image_name}'...")
                self.client.images.pull(image_name)
                return

            self.client.images.get(image_name)
            logger.info(f"Image '{image_name}' already exists.")
        except ImageNotFound:
            logger.info(f"Image '{image_name}' not found. Pulling the image...")
            self.client.images.pull(image_name)
        except Exception as e:
            logger.error(f"Failed to pull image '{image_name}': {str(e)}")
            raise

    def _get_container(self, container_name: str) -> Optional[Container]:
        """Get a container by name with error handling."""
        try:
            return self.client.containers.get(container_name)
        except NotFound:
            logger.warning(f"Container '{container_name}' not found.")
            return None
        except Exception as e:
            logger.error(f"Error getting container '{container_name}': {str(e)}")
            return None

    def _start_container(self, image: str, ports: Dict[str, int], name: str, 
                         environment: Dict[str, str], mem_limit: str = None) -> Optional[Container]:
        """Start a new Docker container with the specified configuration."""
        try:
            kwargs = {
                "image": image,
                "detach": True,
                "name": name,
                "environment": environment,
                "ports": ports
            }
            
            if mem_limit:
                kwargs["mem_limit"] = mem_limit
            
            container = self.client.containers.run(**kwargs)
            logger.info(f"Container '{name}' started successfully.")
            return container
        except Exception as e:
            logger.error(f"Failed to start container '{name}': {str(e)}")
            return None
        
    def clean_container_internal(self, container_name: str) -> bool:
        """Run cleanup script inside a container."""
        container = self._get_container(container_name)
        if not container:
            return False
        
        try:
            container.exec_run("python cleanup.py")
            logger.info(f"Container '{container_name}' cleaned up.")
            return True
        except Exception as e:
            logger.error(f"Failed to clean container '{container_name}': {str(e)}")
            return False

    def start_game_server(self, port: int, sim: bool = False, num_bot=5) -> bool:
        """Start a game server container on the specified port."""
        container_name = self.get_game_server_container_name(port)
        try:
            container = self._start_container(
                settings.GAME_ENGINE_IMAGE,
                ports={f"{port}/tcp": port},
                name=container_name,
                environment={
                    "PORT": str(port),
                    "DOCKER_HOST": settings.DOCKER_SOCKET,
                },
            )

            if not container:
                return False
            
            self.connect_container_to_network(settings.GAME_NETWORK_NAME, container_name)

            # Ensure output directory exists and has proper permissions
            container.exec_run("mkdir -p /app/output")
            container.exec_run("chmod 755 /app/output")

            if sim:
                exec_command = f"python main.py --port={port} --sim --players={num_bot + 1} --log-file=/app/output/game.log"
            else:
                # Execute the command inside the container
                exec_command = f"python main.py --port={port} --log-file=/app/output/game.log"
            container.exec_run(exec_command, detach=True)
            logger.info(f"Game server started on port {port}.")
            return True
        except Exception as e:
            logger.error(f"Failed to start game server: {str(e)}")
            return False

    def create_idle_game_server(self, port: int) -> bool:
        """Create a game server container without starting the game server process."""
        container_name = self.get_game_server_container_name(port)
        try:
            container = self._start_container(
                settings.GAME_ENGINE_IMAGE,
                ports={f"{port}/tcp": port},
                name=container_name,
                environment={
                    "PORT": str(port),
                    "DOCKER_HOST": settings.DOCKER_SOCKET,
                },
            )

            if not container:
                return False
            
            self.connect_container_to_network(settings.GAME_NETWORK_NAME, container_name)

            # Ensure output directory exists and has proper permissions
            container.exec_run("mkdir -p /app/output")
            container.exec_run("chmod 755 /app/output")

            logger.info(f"Idle game server container created on port {port}.")
            return True
        except Exception as e:
            logger.error(f"Failed to create idle game server: {str(e)}")
            return False
        
    def stop_and_remove_container(self, container_name: str) -> bool:
        """Stop and remove a container by name."""
        container = self._get_container(container_name)
        if not container:
            return False
        
        try:
            container.stop()
            container.remove(force=True)
            logger.info(f"Container '{container_name}' stopped and removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to stop and remove container '{container_name}': {str(e)}")
            return False

    def start_client_container(self, host: str, server_port: int, id: str, sim: bool = False) -> bool:
        """Start a client container connected to a game server."""
        formatted_id = self.format_username(id)
        client_container_name = f"client_container_{server_port}_{formatted_id}"
        try:
            container = self._start_container(
                settings.RUNNER_IMAGE,
                ports={},
                name=client_container_name,
                environment={
                    "DOCKER_HOST": settings.DOCKER_SOCKET,
                },
                mem_limit="100m",
            )

            if not container:
                return False
            
            self.connect_container_to_network(settings.GAME_NETWORK_NAME, client_container_name)

            # Ensure output directory exists and has proper permissions for client
            container.exec_run("mkdir -p /app/output")
            container.exec_run("chmod 755 /app/output")

            # Execute the command inside the container
            if sim:
                exec_command = f"python main.py --host={host} --port={server_port} -s True"
            else:
                exec_command = f"python main.py --host={host} --port={server_port}"
            container.exec_run(exec_command, detach=True)

            logger.info(f"Client container {client_container_name} started.")
            return True
        except Exception as e:
            logger.error(f"Failed to start client container: {str(e)}")
            return False
        
    def get_client_score(self, container_name: str) -> int:
        """Get the score from a client container."""
        container = self._get_container(container_name)
        if not container:
            return 0
        
        try:
            _, output = container.exec_run("python check.py")
            score = int(float(output.decode().strip()))
            return score
        except Exception as e:
            logger.error(f"Failed to get score from container '{container_name}': {str(e)}")
            return 0
        
    def get_game_server_container_name(self, port: int) -> str:
        """Get the container name for a game server on the specified port."""
        return f"game_server_{port}"
        
    def check_log_file_exists(self, container_name: str, log_path: str = "/app/output/game.log") -> bool:
        """Check if a log file exists in a container."""
        container = self._get_container(container_name)
        if not container:
            return False
        
        try:
            exit_code, output = container.exec_run(f"test -f {log_path}")
            return exit_code == 0
        except Exception as e:
            logger.error(f"Failed to check log file existence: {str(e)}")
            return False
    
    def get_container_logs(self, container_name: str, tail: int = 50) -> str:
        """Get logs from a container for debugging."""
        container = self._get_container(container_name)
        if not container:
            return f"Container {container_name} not found"
        
        try:
            logs = container.logs(tail=tail).decode("utf-8")
            return logs
        except Exception as e:
            logger.error(f"Failed to get logs for container '{container_name}': {str(e)}")
            return f"Error getting logs: {str(e)}"
    
    def get_log_file_content(self, container_name: str, log_path: str = "/app/output/game.log") -> str:
        """Get the content of a log file from a container."""
        container = self._get_container(container_name)
        if not container:
            return f"Container {container_name} not found"
        
        try:
            exit_code, output = container.exec_run(f"cat {log_path}")
            if exit_code == 0:
                return output.decode("utf-8")
            else:
                return f"Failed to read log file (exit code: {exit_code})"
        except Exception as e:
            logger.error(f"Failed to get log file content: {str(e)}")
            return f"Error reading log file: {str(e)}"
    
    def find_and_read_id_log_from_client(self, container_name: str) -> str:
        """Find and read a game log file, with fallback to search if exact name fails."""
        container = self._get_container(container_name)
        if not container:
            return f"Container {container_name} not found"
        
        # First try the exact filename
        log_path = f"/app/output/gameid.log"
        try:
            exit_code, output = container.exec_run(f"cat {log_path}")
            if exit_code == 0:
                return output.decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to find and read game log: {str(e)}")
            return f"Error finding game log: {str(e)}"

    def extract_player_id_from_log(self, container_name: str) -> Optional[int]:
        """Extract numeric player ID from gameid.log file."""
        log_content = self.find_and_read_id_log_from_client(container_name)
        
        if "Container" in log_content and "not found" in log_content:
            return None
        if "Error" in log_content:
            return None
            
        try:
            # Extract numeric ID from "Player connected: XXXXX" format
            if "Player connected:" in log_content:
                # Split by "Player connected:" and get the number part
                parts = log_content.strip().split("Player connected:")
                if len(parts) > 1:
                    player_id_str = parts[1].strip()
                    return int(player_id_str)
            return None
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to extract player ID from log content '{log_content}': {str(e)}")
            return None
        
    def check_game_container_status(self, port: int, sim=False) -> GameStatus:
        """Check the status of a game container."""
        game_container_name = self.get_game_server_container_name(port)
        container = self._get_container(game_container_name)

        sim_arg = "--sim" if sim else ""

        if not container:
            return GameStatus.NON_EXISTENT
        
        try:
            _, output = container.exec_run("python check.py " + sim_arg)
            status_text = output.decode()
            
            if GameStatus.NOT_STARTED.value in status_text:
                return GameStatus.NOT_STARTED
            elif GameStatus.IN_PROGRESS.value in status_text:
                return GameStatus.IN_PROGRESS
            elif GameStatus.COMPLETED.value in status_text:
                return GameStatus.COMPLETED
            else:
                return GameStatus.NON_EXISTENT
        except Exception as e:
            logger.error(f"Failed to check game status for container '{game_container_name}': {str(e)}")
            return GameStatus.NON_EXISTENT
    
    def create_network(self, network_name: str) -> bool:
        """Create a Docker network if it doesn't exist."""
        try:
            existing_networks = self.client.networks.list(names=[network_name])
            if existing_networks:
                logger.info(f"Network '{network_name}' already exists.")
                return True

            self.client.networks.create(network_name, driver="bridge")
            logger.info(f"Network '{network_name}' created.")
            return True
        except APIError as e:
            logger.error(f"Failed to create network '{network_name}': {str(e)}")
            return False

    def connect_container_to_network(self, network_name: str, container_name: str) -> bool:
        """Connect a container to a network."""
        try:
            network = self.client.networks.get(network_name)
            container = self.client.containers.get(container_name)
            network.connect(container)
            logger.info(f"Container '{container.name}' connected to network '{network_name}'.")
            return True
        except NotFound:
            logger.error(f"Network '{network_name}' or container not found.")
            return False
        except Exception as e:
            logger.error(f"Failed to connect container to network '{network_name}': {str(e)}")
            return False

    def remove_network(self, network_name: str) -> bool:
        """Remove a Docker network."""
        try:
            network = self.client.networks.get(network_name)
            network.remove()
            logger.info(f"Network '{network_name}' removed.")
            return True
        except NotFound:
            logger.warning(f"Network '{network_name}' not found.")
            return False
        except Exception as e:
            logger.error(f"Failed to remove network '{network_name}': {str(e)}")
            return False

    def load_file_into_container(self, container_name: str, tarstream: io.BytesIO) -> bool:
        """Load files from a tar stream into a container."""
        container = self._get_container(container_name)
        if not container:
            return False
        
        try:
            container.put_archive("/app", tarstream)
            logger.info(f"Files loaded into container '{container_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to load files into container '{container_name}': {str(e)}")
            return False

    def install_python_package(self, container_name: str) -> str:
        """Install Python packages in a container using requirements.txt."""
        container = self._get_container(container_name)
        if not container:
            return "Container not found"
        
        try:
            exit_code, output = container.exec_run("pip install -r requirements.txt")
            output_text = output.decode("utf-8")
            
            if exit_code == 0:
                logger.info(f"Python packages installed in container '{container_name}'.")
                return "success"
            else:
                return f"Error: {output_text}"
        except Exception as e:
            logger.error(f"Failed to install packages in container '{container_name}': {str(e)}")
            return f"Error: {str(e)}"

    def malform_file_client_check(self, container_name: str) -> str:
        """Run validation check on player script in a container."""
        container = self._get_container(container_name)
        if not container:
            return "Container not found"
        
        try:
            # Step 1: Check Python syntax using py_compile
            exit_code, output = container.exec_run("python -m py_compile player.py")
            output_text = output.decode("utf-8")
            
            if exit_code != 0:
                return f"Python syntax error: {output_text}"
            
            # Step 2: Try to import the module to catch import errors
            exit_code, output = container.exec_run("python -c 'import player'")
            output_text = output.decode("utf-8")
            
            if exit_code != 0:
                return f"Python import error: {output_text}"
            
            # Step 3: Run the original play_script.py check for additional validation
            exit_code, output = container.exec_run("python play_script.py")
            output_text = output.decode("utf-8")
            
            if exit_code != 0:
                return f"Validation error: {output_text}"
            
            # Check for any error messages in the output
            if "error" in output_text.lower() or "exception" in output_text.lower():
                return f"Error detected: {output_text}"
            
            logger.info(f"Malform file check executed successfully in container '{container_name}'.")
            return "success"
            
        except Exception as e:
            logger.error(f"Failed to execute malform file check in container '{container_name}': {str(e)}")
            return f"Error: {str(e)}"
        
    def run_game_and_save_log(self, container_name: str, num_players: int) -> Tuple[bool, str]:
        """Runs a poker game in a specified container, retrieves the log, and saves it to the db"""
        container = self._get_container(container_name)
        if not container:
            return False, f"Container '{container_name}' not found."
        
        try:
            logger.info(f"Executing game in container {container_name} for {num_players} players...")
            game_command = f"python main.py --players {num_players} --sim"
            exit_code, output = container.exec_run(cmd=game_command)
            output_str = output.decode('utf-8')

            if exit_code != 0:
                logger.error(f"Error running game in container {container_name}: {output_str}")
                return False, f"Game execution failed: {output_str}"
            
            logger.info("Searching for game log file in container...")
            ls_command = "ls /app/output"
            exit_code, (stdout, stderr) = container.exec_run(cmd=ls_command)
            if exit_code != 0:
                return False, "Could not list files in /app/output"
            
            files = stdout.decode('utf-8').splitlines()
            log_filename = next((f for f in files if f.startswith("game_log_") and f.endswith(".json")), None)

            if not log_filename:
                logger.error("Game log file not found in container output.")
                return False, "Game log file not found in container output."
            
            log_filepath_in_container = f"/app/output/{log_filename}"
            logger.info(f"Found log file: {log_filepath_in_container}")

            bits, stat = container.get_archive(log_filepath_in_container)
            file_obj = io.BytesIO()
            for chunk in bits:
                file_obj.write(chunk)
            file_obj.seek(0)

            with tarfile.open(fileobj=file_obj) as tar:
                member = tar.getmembers()[0]
                extracted_file = tar.extractfile(member)
                if extracted_file:
                    file_content = extracted_file.read().decode('utf-8')
                    game_data = json.loads(file_content)
                else:
                    return False, "Failed to extract log file from archive."
            
            game_uuid = game_data.get("gameId")
            logger.info(f"Saving game log with UUID {game_uuid} to database...")
            with Session(engine) as session:
                existing_log = session.exec(select(GameLog).where(GameLog.game_uuid == game_uuid)).first()
                if existing_log:
                    logger.warning(f"Game log with UUID {game_uuid} already exists. Skipping.")
                    return True, f"Game log {game_uuid} already existed."
                
                new_log = GameLog(
                    id=uuid.UUID(game_uuid),
                    game_uuid=game_uuid,
                    game_data=game_data
                )

                session.add(new_log)
                session.commit()
                logger.info(f"Successfully saved game log {new_log.game_uuid} to database.")

            return True, f"Game log {new_log.game_uuid} saved."
        
        except Exception as e:
            logger.error(f"An exception occurred in run_game_and_save_log: {e}", exc_info=True)
            return False, str(e)