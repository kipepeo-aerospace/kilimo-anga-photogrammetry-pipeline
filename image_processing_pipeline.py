import os
import glob
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
import math
from pyproj import Transformer

def get_exif_data(image_path):
    """Extracts EXIF data from an image, including GPS info."""
    image = Image.open(image_path)
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]
                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value
    return exif_data

def get_decimal_from_dms(dms, ref):
    """Converts GPS coordinates from DMS (degrees, minutes, seconds) to decimal."""
    # dms is a tuple of 3 rational values. Each value is a tuple of (numerator, denominator).
    # We unpack and divide to get the float value.
    
    # Degrees
    deg_num, deg_den = dms[0]
    degrees = float(deg_num) / float(deg_den)

    # Minutes
    min_num, min_den = dms[1]
    minutes = (float(min_num) / float(min_den)) / 60.0

    # Seconds
    sec_num, sec_den = dms[2]
    seconds = (float(sec_num) / float(sec_den)) / 3600.0

    decimal_degrees = degrees + minutes + seconds

    if ref in ['S', 'W']:
        decimal_degrees = -decimal_degrees

    return decimal_degrees

def get_lat_lon(exif_data):
    """Extracts latitude and longitude from EXIF data."""
    if 'GPSInfo' in exif_data:
        gps_info = exif_data['GPSInfo']
        lat_dms = gps_info.get('GPSLatitude')
        lon_dms = gps_info.get('GPSLongitude')
        lat_ref = gps_info.get('GPSLatitudeRef')
        lon_ref = gps_info.get('GPSLongitudeRef')

        if lat_dms and lon_dms and lat_ref and lon_ref:
            lat = get_decimal_from_dms(lat_dms, lat_ref)
            lon = get_decimal_from_dms(lon_dms, lon_ref)
            return lat, lon
    return None, None

def get_focal_length(exif_data):
    """Extracts focal length in mm from EXIF data."""
    focal_length_rational = exif_data.get('FocalLength')
    if focal_length_rational:
        num, den = focal_length_rational
        return float(num) / float(den)
    return None

def get_flight_altitude(exif_data):
    """Extracts flight altitude in meters from EXIF data."""
    if 'GPSInfo' in exif_data:
        gps_info = exif_data['GPSInfo']
        altitude_rational = gps_info.get('GPSAltitude')
        if altitude_rational:
            num, den = altitude_rational
            return float(num) / float(den)
    return None

def get_image_dimensions(exif_data):
    """Extracts image width and height from EXIF data."""
    width = exif_data.get('ExifImageWidth')
    height = exif_data.get('ExifImageHeight')
    return width, height

def get_sensor_width(exif_data):
    """Calculates sensor width in mm from EXIF data."""
    focal_plane_x_res_rational = exif_data.get('FocalPlaneXResolution')
    image_width = exif_data.get('ExifImageWidth')
    
    if focal_plane_x_res_rational and image_width:
        fpx_num, fpx_den = focal_plane_x_res_rational
        focal_plane_x_res = float(fpx_num) / float(fpx_den)
        
        # Sensor width (mm) = Image width (pixels) / Focal plane resolution (pixels/mm)
        sensor_width_mm = (float(image_width) / focal_plane_x_res)
        
        # Resolution unit: 2 = inches, 3 = cm. Default is inches if not specified.
        resolution_unit = exif_data.get('FocalPlaneResolutionUnit', 2)
        if resolution_unit == 2:  # Inches to mm
            sensor_width_mm *= 25.4
        elif resolution_unit == 3:  # cm to mm
            sensor_width_mm *= 10
            
        return sensor_width_mm
    return None

def calculate_gsd(focal_length, flight_altitude, sensor_width, image_width):
    """Calculates Ground Sampling Distance (GSD) in meters."""
    if focal_length and flight_altitude and sensor_width and image_width:
        # GSD = (sensor_width * flight_altitude) / (focal_length * image_width)
        gsd = (sensor_width * flight_altitude) / (focal_length * image_width)
        return gsd

def calculate_pixel_size(gsd, lat):
    """Calculates pixel size in degrees based on the image's geotransform"""
    lat_rad = math.radians(lat)
    # Approximate conversion factor from meters to degrees at the equator
    meters_per_degree = 111320 * math.cos(lat_rad)
    pixel_size = gsd / meters_per_degree  # GSD in degrees
    return pixel_size

def get_utm_epsg(lat, lon):
    zone_number = int((lon + 180) / 6) + 1 
    if lat >= 0:
        return f"EPSG:{32600 + zone_number}" # Northern hemisphere
    else:
        return f"EPSG:{32700 + zone_number}" # Southern hemisphere

def convert_jpg_to_geotiff(jpg_path, output_dir):
    """Converts a JPG to a GeoTIFF, embedding GPS data."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    exif_data = get_exif_data(jpg_path)
    lat, lon = get_lat_lon(exif_data)
    focal_length = get_focal_length(exif_data)
    flight_altitude = get_flight_altitude(exif_data)
    image_width, image_height = get_image_dimensions(exif_data)
    #sensor_width = get_sensor_width(exif_data)
    sensor_width = 13.2  # hardcoded value for the known DJI FC6310
    
    if lat is None or lon is None:
        print(f"Warning: No GPS data found for {jpg_path}. Skipping.")
        return None

    with rasterio.open(jpg_path) as src:
        # For accurate results, you would need to calculate this based on camera
        # parameters and flight altitude.

        gsd = calculate_gsd(focal_length, flight_altitude, sensor_width, image_width)

        # ---- Using Pixel size and EPSG ----        
        
        #pixel_size = calculate_pixel_size(gsd, lat)
        
        pixel_size = 0.00001  # Approximate pixel size in degrees
        half_width = (image_width * pixel_size) / 2
        half_height = (image_height * pixel_size) / 2

        top_left_lon = lon - half_width
        top_left_lat = lat + half_height
        transform = from_origin(top_left_lon, top_left_lat, pixel_size, pixel_size)

        # ---- End of Pixel size and EPSG ----

        # ----- Using UTM coordinates -----
        # Convert lat/lon to UTM coordinates for the transform
        # This assumes the image is small enough to use a single UTM zone.
        #utm = get_utm_epsg(lat, lon)
        #transformer = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
        #easting, northing = transformer.transform(lon, lat)

        #half_width = (image_width * gsd) / 2
        #half_height = (image_height * gsd) / 2

        #top_left_lon = easting - half_width
        #top_left_lat = northing + half_height

        #transform = from_origin(top_left_lon, top_left_lat, gsd, gsd)
        
        # ---- End of UTM coordinates ----
    
        # Update the profile with the new transform and metadata
        profile = src.profile
        profile.update(
            driver='GTiff',
            crs='EPSG:4326',  # WGS84
            #crs=utm,  # the utm crs is used
            transform=transform,
            compress='jpeg',
            tiled=True,
            blockysize=16 # Ensures RowsPerStrip is a multiple of 16
        )

        tiff_filename = os.path.splitext(os.path.basename(jpg_path))[0] + '.tif'
        tiff_path = os.path.join(output_dir, tiff_filename)

        with rasterio.open(tiff_path, 'w', **profile) as dst:
            dst.write(src.read())
            
        return tiff_path

def stitch_geotiffs(tiff_dir, output_path):
    """Stitches multiple GeoTIFFs into a single mosaic."""
    tiff_files = glob.glob(os.path.join(tiff_dir, '*.tif'))
    if not tiff_files:
        print("No TIFF files found to stitch.")
        return

    src_files_to_mosaic = []
    for fp in tiff_files:
        src = rasterio.open(fp)
        src_files_to_mosaic.append(src)

    mosaic, out_trans = merge(src_files_to_mosaic)

    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
    })

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    for src in src_files_to_mosaic:
        src.close()

if __name__ == '__main__':
    # --- Configuration ---
    # Directory containing your original JPG drone images
    jpg_input_directory = 'input/greenwood'
    
    # Directory to save the intermediate georeferenced TIFF files
    tiff_output_directory = 'input/greenwood_geotiffs'
    
    # Path for the final, stitched mosaic image
    final_mosaic_path = 'output/greenwood_mosaic.tif'
    
    # --- Create dummy images for testing if they don't exist ---
    if not os.path.exists(jpg_input_directory):
        print("Creating a dummy 'drone_images' directory with sample images.")
        os.makedirs(jpg_input_directory)
        # In a real scenario, you would have your own JPGs with EXIF data.
        # This part is just for making the script runnable out-of-the-box.
        try:
            # Create a simple blank image
            dummy_image = Image.new('RGB', (100, 100), color = 'red')
            dummy_image.save(os.path.join(jpg_input_directory, 'drone_image_1.jpg'))
            dummy_image.save(os.path.join(jpg_input_directory, 'drone_image_2.jpg'))
            print("NOTE: The dummy images do not have real GPS data, so the conversion will be skipped.")
            print("Please replace them with your actual drone images.")
        except Exception as e:
            print(f"Could not create dummy images. Please ensure you have images in the '{jpg_input_directory}' folder. Error: {e}")


    # --- Pipeline Execution ---
    
    # 1. Convert all JPGs in the input directory to GeoTIFFs
    print(f"Starting conversion of JPGs from '{jpg_input_directory}' to GeoTIFFs in '{tiff_output_directory}'...")
    converted_tiffs = []
    for jpg_file in glob.glob(os.path.join(jpg_input_directory, '*.JPG')):
        tiff_path = convert_jpg_to_geotiff(jpg_file, tiff_output_directory)
        if tiff_path:
            converted_tiffs.append(tiff_path)
            print(f"  Successfully converted {jpg_file} to {tiff_path}")

    # 2. Stitch the newly created GeoTIFFs into a single mosaic
    if converted_tiffs:
        print("\nStarting to stitch GeoTIFFs...")
        stitch_geotiffs(tiff_output_directory, final_mosaic_path)
        print(f"\nStitching complete. The final mosaic has been saved to '{final_mosaic_path}'")
    else:
        print("\nNo images were converted, so stitching was skipped.")
        print("This is likely because no GPS data was found in your JPGs.")

    print("\nPipeline finished.")

