import os
from azure.storage.blob import BlobServiceClient
from azure.core.pipeline.transport import RequestsTransport
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

# ============================================
# Logging configuration
# ============================================

logger = logging.getLogger(__name__)
# ============================================
# Load environment variables from .env file 
# ============================================

load_dotenv()  # Load environment variables from .env file

# Get the connection string securely from the environment
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if AZURE_STORAGE_CONNECTION_STRING is None:
    raise EnvironmentError("AZURE_STORAGE_CONNECTION_STRING is not set.")


# Create a custom transport with extended timeouts
transport = RequestsTransport(connection_timeout=60, read_timeout=600)

# Initialize the blob service client
blob_service = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING,
    transport=transport)

# ============================================
# Azure Blob Storage utility functions 
# ============================================

def test_upload_and_download():
    import tempfile

    # Create dummy data
    client_id = "test-client"
    field_id = "test-field"
    blob_name = generate_blob_name(client_id, field_id, "test.txt")

    # Create a temp file to simulate pipeline output
    with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
        tmp_file.write("Hello from Kilimo Anga pipeline 👋")
        tmp_file_path = tmp_file.name

    # Upload dummy file
    upload_file_to_blob("processed-mosaics", tmp_file_path, blob_name)

    # Download to verify
    download_blob_to_file("processed-mosaics", blob_name, "downloaded_test.txt")

    print(f"✅ Test blob uploaded as: {blob_name}")
    print("📥 Check if 'downloaded_test.txt' has correct contents.")

def generate_blob_name(client_id, field_id, suffix):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    return f"{client_id}/{field_id}/{timestamp}-{suffix}"

def download_blob_to_file(container_name, blob_name, download_path):
    """
    Downloads a blob from the given container and saves it locally
    """
    container_client = blob_service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    with open(download_path, "wb") as file:
        download_stream = blob_client.download_blob()
        file.write(download_stream.readall())

def upload_file_to_blob(container_name, local_path, blob_name):
    """
    Uploads a local file to the specified blob container.
    """
    container_client = blob_service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    with open(local_path, "rb") as data:
        blob_client.upload_blob(
            data, 
            overwrite=True,  
            max_concurrency=1,  
            timeout=1200)  # Increased timeout for large files

def upload_large_file_to_blob(container_name, local_path, blob_name):
    """
    Uploads a local file to the specified blob container using block blob upload.
    Handles both small and large files reliably, especially in Docker environments.
    """
    # Adjust this if needed
    block_size = 4 * 1024 * 1024  # 4MB

    blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
    file_size = os.path.getsize(local_path)

    # For small files, use simple upload
    if file_size <= block_size:
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        return

    # For larger files, use block upload
    block_ids = []
    with open(local_path, "rb") as file:
        i = 0
        while True:
            data = file.read(block_size)
            if not data:
                break
            block_id = f"{i:06}".encode("utf-8")
            blob_client.stage_block(block_id=block_id, data=data)
            block_ids.append(block_id)
            i += 1

    blob_client.commit_block_list(block_ids)

def download_images_for_field(container_name, client_id, field_id):
    """
    Downloads all images under raw-images/<client_id>/<field_id>/ into the local input folder
    """
    image_dir = f"{container_name}/{client_id}/{field_id}/"

    container_client = blob_service.get_container_client(container_name)
    blobs = container_client.list_blobs(name_starts_with=image_dir)

    for blob in blobs:
        if blob.name.endswith("/"):
            continue  # skip virtual folders
        
        local_path = blob.name
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Check if file already exists
        if os.path.exists(local_path):
            logger.info(f"  Skipping {blob.name} — already exists at {local_path}")
            continue

        # Download the blob to the local path
        logger.info(f"  Downloading {blob.name} → {local_path}")
        download_blob_to_file(container_name, blob.name, local_path)
    
    return image_dir

