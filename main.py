import argparse
from stitching import convert_and_stitch
from indices import compute_vari
from azure_blob import upload_file_to_blob, download_images_for_field
import os
import glob
from dotenv import load_dotenv
import logging

# ============================================
# Logging configuration
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),                      # Console
        #logging.FileHandler("logs/photogrammetry-pipeline.log", mode='a') # Log file
    ]
)

logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ============================================
# Load environment variables from .env file 
# ============================================

load_dotenv()  # Load environment variables from .env file

# Define container names from environment variables
RAW_IMAGES_CONTAINER = os.environ.get("RAW_IMAGES_CONTAINER")
TIF_CONTAINER = os.environ.get("TIFF_CONTAINER")
MOSAIC_CONTAINER = os.environ.get("MOSAIC_CONTAINER")
INDICES_CONTAINER = os.environ.get("INDICES_CONTAINER")

# ============================================
# Argument parsing for the pipeline
# ============================================

def runtime_args():
    parser = argparse.ArgumentParser(description="Kilimo Anga Photogrammetry Pipeline")
    parser.add_argument(
        '--client_id', 
        type=str, 
        default=os.getenv("CLIENT_ID"),
        required=False, 
        help='Client identifier')
    parser.add_argument(
        '--field_id', 
        type=str, 
        default=os.getenv("FIELD_ID"),
        required=False, 
        help='Field identifier')
    parser.add_argument(
        '--index', 
        type=str, 
        default=os.getenv("VEGETATION_INDEX"),
        choices=['VARI'], 
        help='Vegetation index to compute')
    
    args =  parser.parse_args()
    
    # Fail early if any required input is missing
    if not args.client_id or not args.field_id or not args.index:
        raise ValueError("Missing client_id, field_id, or index.")

    return args

# ============================================
# Main pipeline function
# ============================================

def main():

    args = runtime_args()

    # ---- Download images for the specified client and field ----
    logger.info(f"\nDownloading images for client '{args.client_id}' and field '{args.field_id}'...")
    
    input_dir = download_images_for_field(RAW_IMAGES_CONTAINER, args.client_id, args.field_id)
    
    # ---- Convert and stitch images ----
    
    logger.info("\nConverting and stitching images...")

    converted_dir, mosaic_path = convert_and_stitch(input_dir, TIF_CONTAINER, MOSAIC_CONTAINER)

    # ---- Upload the converted images to the converted container ----
    
    logger.info(f"\nUploading converted images to '{TIF_CONTAINER}'...")
    
    for tif_file in glob.glob(os.path.join(converted_dir, '*.tif')):
        blob_name = tif_file
        # Upload the blob to the container
        logger.info(f"  Uploading {blob_name} to {converted_dir}...")
        upload_file_to_blob(TIF_CONTAINER, tif_file, blob_name)

    logger.info("\nConverted images uploaded successfully.")
    
    # ---- Upload the final mosaic to the mosaic container ----
    
    logger.info(f"  Uploading final mosaic to '{MOSAIC_CONTAINER}'...")
    upload_file_to_blob(MOSAIC_CONTAINER, mosaic_path, mosaic_path)
    logger.info("\nMosaic uploaded successfully.")
    
    # ---- Compute the specified vegetation index ----

    relative_path = os.path.relpath(converted_dir, start=TIF_CONTAINER)
    output_dir = os.path.join(INDICES_CONTAINER, relative_path)
    os.makedirs(output_dir, exist_ok=True)

    if args.index == 'VARI':
        logger.info("\nComputing VARI...")
        compute_vari(mosaic_path, output_dir)

    logger.info("\nProcessing complete. Results saved to:", output_dir)

    # ---- Upload the index results ----
    
    logger.info(f"\nUploading index results to '{INDICES_CONTAINER}'...")
    
    for index_file in glob.glob(os.path.join(output_dir, '*.tif')):
        blob_name = index_file
        logger(f"  Uploading {index_file} as {blob_name}")
        upload_file_to_blob(INDICES_CONTAINER, index_file, blob_name)

    logger.info("\nIndex results uploaded successfully.")

    logger.info("\nAll pipeline operations completed successfully.")

# ============================================
# Entry point for the script
# ============================================

if __name__ == "__main__":
    logger.info("Initailizing the Kilimo Anga Photogrammetry Pipeline")
    main()
    