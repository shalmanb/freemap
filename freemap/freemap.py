#!/usr/bin/env python3
import sqlite3
import os
import sys
import argparse
import time
from tqdm import tqdm

def get_tile_format(cur):
    """
    Queries the metadata table to determine the tile image format.
    Defaults to 'png' if not found.
    """
    try:
        cur.execute("SELECT value FROM metadata WHERE name = 'format'")
        result = cur.fetchone()
        if result:
            return result[0]
    except sqlite3.OperationalError:
        print("Warning: Could not read 'format' from metadata table.")
    return 'png' # Default to png if not specified

# MODIFIED: This function now uses the user-provided static HTML as a template.
def create_static_html_viewer(output_dir, tile_format):
    """
    Creates a static index.html file in the main directory.
    """
    # Get the name of the tile folder to use in the HTML path
    tile_folder_name = os.path.basename(output_dir)

    # User-provided HTML, with the tile path made dynamic
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dhamoirhat Map</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
     integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
     crossorigin=""/>
     
    <style>
        /* Basic styling for the map container */
        html, body {{
            height: 100%;
            margin: 0;
            padding: 0;
        }}
        #map {{
            width: 100%;
            height: 100%;
        }}
    </style>
</head>
<body>

<div id="map"></div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
     integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
     crossorigin=""></script>

<script>
    // Initialize the map and set its view
    const map = L.map('map').setView([25.13, 88.85], 12); // Centered view

    // Add the tile layer to the map, pointing to the local folder
    L.tileLayer('{tile_folder_name}/{{z}}/{{x}}/{{y}}.{tile_format}', {{
        maxZoom: 18,
        minZoom: 0,
        attribution: 'Map data &copy; OpenStreetMap contributors',
        tms: false // Set to false because our script output is XYZ
    }}).addTo(map);

</script>

</body>
</html>
"""
    # MODIFIED: Create index.html in the current working directory
    html_path = 'index.html'
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content.strip())
        print(f"Success: Created map viewer at '{os.path.abspath(html_path)}'")
    except Exception as e:
        print(f"Error: Could not create index.html file. Reason: {e}")

def extract_tiles(db_file, output_dir, tms_scheme=False):
    """
    Extracts tiles from an MBTiles file and creates an HTML viewer.
    """
    conn = None # Initialize conn to None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        tile_format = get_tile_format(cur)
        print(f"Detected tile format: .{tile_format}")

        cur.execute("SELECT COUNT(*) FROM tiles")
        count = cur.fetchone()[0]
        if count == 0:
            print("No tiles to extract.")
            return
        
        print(f"Found {count} tiles to extract.")
        cur.execute("SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles")
        
        start_time = time.time()
        for row in tqdm(cur, total=count, desc="Extracting Tiles"):
            zoom, x, y, tile_data = row
            
            if not tms_scheme:
                y = (2**zoom - 1) - y

            tile_dir = os.path.join(output_dir, str(zoom), str(x))
            os.makedirs(tile_dir, exist_ok=True)
            
            tile_path = os.path.join(tile_dir, f"{y}.{tile_format}")
            with open(tile_path, 'wb') as f:
                f.write(tile_data)
        
        end_time = time.time()
        print(f"\nExtraction complete. Time taken: {end_time - start_time:.2f} seconds.")

        # MODIFIED: Call the new static HTML creator
        create_static_html_viewer(output_dir, tile_format)

    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

def main():
    """Main function to parse arguments and run the extraction."""
    parser = argparse.ArgumentParser(description="Extracts tiles from an MBTiles file and creates an HTML viewer.")
    parser.add_argument("input_file", help="Path to the input .mbtiles file.")
    parser.add_argument("-o", "--output", help="Path to the output directory. Defaults to a folder named after the input file.")
    parser.add_argument("--tms", action="store_true", help="Use TMS y-coordinate scheme instead of the default XYZ.")
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"Error: Input file not found at '{args.input_file}'")
        sys.exit(1)

    output_dir = args.output
    if not output_dir:
        base_name = os.path.basename(args.input_file)
        file_name_without_ext = os.path.splitext(base_name)[0]
        output_dir = f"{file_name_without_ext}_tiles"

    print(f"Input file: {args.input_file}")
    print(f"Output directory: {output_dir}")
    if args.tms:
        print("Using TMS coordinate scheme.")
    else:
        print("Using XYZ coordinate scheme (default for web maps).")
        
    os.makedirs(output_dir, exist_ok=True)

    extract_tiles(args.input_file, output_dir, args.tms)

if __name__ == "__main__":
    main()