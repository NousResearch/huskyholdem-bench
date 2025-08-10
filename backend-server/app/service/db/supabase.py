import os
from typing import Union
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class SupabaseClientSingleton:
    _client: Client = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment.")
            cls._client = create_client(url, key)
        return cls._client


class SupabaseBucketService:
    """
    A service class for interacting with a Supabase storage bucket. This class provides methods
    to upload files to a specified bucket, either from a file path or directly from bytes.
    """
    def __init__(self, bucket_name: str):
        print("Initializing SupabaseBucketService with bucket:", bucket_name)
        self.bucket_name = bucket_name
        self.bucket = SupabaseClientSingleton.get_client().storage.from_(bucket_name)

    def delete_file(self, file_path: str) -> None:
        """
        Delete a file from the bucket.
        
        Args:
            file_path: Path to the file within the bucket
        """
        try:
            self.bucket.remove([file_path])
        except Exception as e:
            raise RuntimeError(f"Failed to delete file: {str(e)}")

    def download_file(self, file_path: str) -> bytes:
        """
        Download a file from the bucket as bytes.
        
        Args:
            file_path: Path to the file within the bucket
            
        Returns:
            The file contents as bytes
        """
        try:
            file_data = self.bucket.download(file_path)
            return file_data
        except Exception as e:
            raise RuntimeError(f"Failed to download file: {str(e)}")


    def upload_file_from_path(self, file_path: Union[str, Path], dest_name: str) -> dict:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with file_path.open("rb") as f:
            return self._upload(dest_name, f.read())


    def upload_file_from_bytes(self, data: bytes, dest_name: str, content_type: str = "application/octet-stream") -> dict:
        return self._upload(dest_name, data, content_type)


    def _upload(self, dest_name: str, data: bytes, content_type: str = "application/octet-stream") -> dict:
        response = self.bucket.upload(dest_name, data, {"content-type": content_type})
        return response