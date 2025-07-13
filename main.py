import argparse
from stitching import convert_and_stitch
from indices import compute_vari
import os
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timezone

# Get the connection string securely from the environment
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if AZURE_STORAGE_CONNECTION_STRING is None:
    raise EnvironmentError("AZURE_STORAGE_CONNECTION_STRING is not set.")

# Initialize the blob service client
blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# --- Functions for Azure Blob Storage operations ---
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
        blob_client.upload_blob(data, overwrite=True)

def download_images_for_field(container_name, client_id, field_id):
    """
    Downloads all images under raw-images/<client_id>/<field_id>/ into the local input folder
    """
    image_dir = f"raw-images/{client_id}/{field_id}/"

    container_client = blob_service.get_container_client(container_name)
    blobs = container_client.list_blobs(name_starts_with=image_dir)

    for blob in blobs:
        if blob.name.endswith("/"):
            continue  # skip virtual folders

        #relative_path = os.path.relpath(blob.name, start="raw-images/")
        #local_path = os.path.join(local_dir, relative_path)
        
        local_path = blob.name
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Check if file already exists
        if os.path.exists(local_path):
            print(f"Skipping {blob.name} — already exists at {local_path}")
            continue

        # Download the blob to the local path
        print(f"Downloading {blob.name} → {local_path}")
        download_blob_to_file(container_name, blob.name, local_path)
    
    return image_dir

def main():
    parser = argparse.ArgumentParser(description="Photogrammetry pipeline for vegetation indices")
    parser.add_argument('--client_id', type=str, required=True, help='Client identifier')
    parser.add_argument('--field_id', type=str, required=True, help='Field identifier')
    parser.add_argument('--index', type=str, default='VARI', choices=['VARI'], help='Vegetation index to compute')

    args = parser.parse_args()

    # ---- Download images for the specified client and field ----
    print(f"Downloading images for client '{args.client_id}' and field '{args.field_id}'...")
    
    raw_container = "raw-images"
    input_dir = download_images_for_field(raw_container, args.client_id, args.field_id)
    
    # ---- Convert and stitch images ----
    
    print("Converting and stitching images...")

    converted_container = "converted-tiles"
    mosaic_container = "proecssed-mosaics"

    converted_dir, mosaic_path = convert_and_stitch(input_dir, converted_container, mosaic_container)

    # ---- Compute the specified vegetation index ----
    
    index_container = "index-maps"
    relative_path = os.path.relpath(converted_dir, start=converted_container)
    output_dir = os.path.join(index_container, relative_path)
    os.makedirs(output_dir, exist_ok=True)

    if args.index == 'VARI':
        print("Computing VARI...")
        compute_vari(mosaic_path, output_dir)

    print("Processing complete. Results saved to:", output_dir)

if __name__ == "__main__":
    main()
    #test_upload_and_download()
    
    
    #container_name = "raw-images"
    #client_id = "test"
    #field_id = "field-001"

    # Download images for a specific field
    #text = download_images_for_field(container_name, client_id, field_id)
    #print(text)