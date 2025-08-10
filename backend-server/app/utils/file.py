# ───── Helpers ────────────────────────────────────────────────────────────────
import io
import tarfile
from typing import Tuple, Union, Protocol

from app.service.docker.main import DockerService

# Protocol for file-like objects (works with both UploadFile and SimpleNamespace)
class FileProtocol(Protocol):
    file: io.IOBase

def clone_bytes(file: io.BytesIO) -> io.BytesIO:
    """Clone a BytesIO object."""
    file.seek(0)
    return io.BytesIO(file.read())


def extract_file_from_tar(tar_file: io.BytesIO) -> dict[str, bytes]:
    """
    Extract a specific file from a tar archive.
    :param tar_file: A BytesIO object containing the tar archive.
    :param file_name: The name of the file to extract.
    :return: The contents of the extracted file as bytes.
    """
    with tarfile.open(fileobj=tar_file, mode='r') as tar:
        extracted_files = {}
        for member in tar.getmembers():
            file_obj = tar.extractfile(member)
            if file_obj:
                extracted_files[member.name] = file_obj.read()
        return extracted_files

def create_tar_from_files(files: dict[str, FileProtocol]) -> io.BytesIO:
    """Package uploaded files into an in‑memory tar archive."""
    tarstream = io.BytesIO()
    with tarfile.open(fileobj=tarstream, mode="w") as tar:
        for arcname, upload_file in files.items():
            file_data = upload_file.file.read()
            tarinfo = tarfile.TarInfo(name=arcname)
            tarinfo.size = len(file_data)
            tar.addfile(tarinfo, io.BytesIO(file_data))
    tarstream.seek(0)
    return tarstream


def check_input_stat(
    docker_service: DockerService, container_name: str
) -> Tuple[bool, str | None]:
    """Run sanity checks inside the container. Return (ok, msg)."""
    out = docker_service.install_python_package(container_name)
    if "error" in out.lower():
        docker_service.stop_and_remove_container(container_name)
        return False, out

    out = docker_service.malform_file_client_check(container_name)
    if "error" in out.lower():
        docker_service.stop_and_remove_container(container_name)
        return False, out

    return True, None