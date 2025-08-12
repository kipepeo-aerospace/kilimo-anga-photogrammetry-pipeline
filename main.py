import argparse
from stitching import convert_and_stitch, convert_tif_to_jpg
from indices import compute_vari, compute_gndvi, compute_ndvi, compute_savi, convert_index_tif_to_jpg
from azure_blob import upload_file_to_blob, download_images_for_field, upload_large_file_to_blob
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
        help='Comma separated Vegetation index to compute')
    
    args =  parser.parse_args()
    
    # Fail early if any required input is missing
    if not args.client_id or not args.field_id or not args.index:
        raise ValueError("Missing client_id, field_id, or index.")

    return args

# ============================================
# Mapping the vegetation indices to functions
# ============================================

INDEX_FUNCTIONS = {
    'VARI': compute_vari,
    'NDVI': compute_ndvi,
    'GNDVI': compute_gndvi,
    'SAVI': compute_savi
} 

# ============================================
# Main pipeline function
# ============================================

def main():

    args = runtime_args()

    # ---- Download images for the specified client and field ----
    logger.info(f"Downloading images for client '{args.client_id}' and field '{args.field_id}'...")
    
    input_dir = download_images_for_field(RAW_IMAGES_CONTAINER, args.client_id, args.field_id)
    
    # ---- Convert and stitch images ----
    
    logger.info("Converting and stitching images...")

    converted_dir, mosaic_path = convert_and_stitch(input_dir, TIF_CONTAINER, MOSAIC_CONTAINER, args)

    # ---- Upload the converted images to the converted container ----
    
    logger.info(f"Uploading converted images to '{TIF_CONTAINER}'...")
    
    for tif_file in glob.glob(os.path.join(converted_dir, '*.tif')):
        blob_name = tif_file
        # Upload the blob to the container
        logger.info(f"  Uploading {blob_name} to {converted_dir}...")
        upload_file_to_blob(TIF_CONTAINER, tif_file, blob_name)

    logger.info("Converted images uploaded successfully.")
    
    # ---- Convert TIF mosaic to JPG and upload them both to the mosaic container ----
    
    logger.info("Converting mosaic to JPG...")
    jpg_mosaic_path = convert_tif_to_jpg(mosaic_path)

    logger.info(f"Uploading final mosaics to '{MOSAIC_CONTAINER}'...")
    upload_large_file_to_blob(MOSAIC_CONTAINER, mosaic_path, mosaic_path)
    upload_large_file_to_blob(MOSAIC_CONTAINER, jpg_mosaic_path, jpg_mosaic_path)
    logger.info("Mosaics uploaded successfully.")
    
    # ---- Compute the vegetation indices ----

    relative_path = os.path.relpath(converted_dir, start=TIF_CONTAINER)
    output_dir = os.path.join(INDICES_CONTAINER, relative_path)
    os.makedirs(output_dir, exist_ok=True)

    # Loop through indices to process
    for index_name in args.index.split(','):  # if you're passing "VARI,NDVI" as a string
        index_name = index_name.strip().upper()
        if index_name in INDEX_FUNCTIONS:
            logger.info(f"Computing {index_name}...")
            INDEX_FUNCTIONS[index_name](mosaic_path, output_dir)
        else:
            logger.warning(f"Unknown index: {index_name}")
    
    logger.info("All indices computed successfully.")

    # ---- Upload them both to index container ----

    logger.info(f"Uploading index results to '{INDICES_CONTAINER}'...")
    
    for index_file in glob.glob(os.path.join(output_dir, '*.tif')):
        blob_name = index_file
        logger.info(f"Uploading {index_file} as {blob_name}")
        upload_large_file_to_blob(INDICES_CONTAINER, index_file, blob_name)

        # convert and upload JPG version of the index as well
        logger.info(f"Converting {index_file} to JPG and uploading as {blob_name}.jpg")
        jpg_index_path = convert_index_tif_to_jpg(index_file)
        upload_large_file_to_blob(INDICES_CONTAINER, jpg_index_path, jpg_index_path)

    logger.info("Index results uploaded successfully.")

    logger.info("All pipeline operations completed successfully.")

# ============================================
# Entry point for the script
# ============================================

if __name__ == "__main__":
    logger.info("Initailizing the Kilimo Anga Photogrammetry Pipeline")
    main()
    