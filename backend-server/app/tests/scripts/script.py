from app.service.docker.main import DockerService

docker_service = DockerService()

container = docker_service.client.containers.get("magical_meninsky")

out = container.exec_run("pip install -r requirements.txt")

print(out.output.decode("utf-8"))
print(out.exit_code)