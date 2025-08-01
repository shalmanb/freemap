#!/usr/bin/env python3
import sqlite3
import os
import sys
import argparse
import time

def extract_tiles(db_file, output_dir, tms_scheme=False):
    """
    Extracts tiles from an MBTiles file to a directory structure.

    :param db_file: Path to the .mbtiles file.
    :param output_dir: Directory to save the tile files.
    :param tms_scheme: Boolean, if True, converts Y coordinates from TMS to XYZ.
    """
    try:
        # Establish connection to the SQLite database (.mbtiles file)
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        # Execute query to get all tile data from the 'tiles' table
        # This is the standard table name for MBTiles
        cur.execute("SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles")
        
        rows = cur.fetchall()
        count = len(rows)
        print(f"Found {count} tiles to extract.")

        # Start timer
        start_time = time.time()

        for i, row in enumerate(rows):
            zoom, x, y, tile_data = row

            # The MBTiles specification stores tiles in TMS (flipped Y) format.
            # Most web maps (like Leaflet, Google Maps) use XYZ.
            # This converts the Y coordinate from TMS to XYZ.
            if not tms_scheme:
                y = (2**zoom - 1) - y

            # Define the directory path for the tile
            tile_dir = os.path.join(output_dir, str(zoom), str(x))

            # Create the directory if it doesn't exist
            os.makedirs(tile_dir, exist_ok=True)
            
            # Define the full path for the tile file
            tile_path = os.path.join(tile_dir, f"{y}.png")

            # Write the tile data (blob) to the .png file
            with open(tile_path, 'wb') as f:
                f.write(tile_data)
            
            # Print progress
            progress = (i + 1) / count * 100
            print(f"Progress: {progress:.2f}% ({i+1}/{count})", end='\r')

        # End timer
        end_time = time.time()
        print(f"\nExtraction complete. Time taken: {end_time - start_time:.2f} seconds.")

    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        print("This might mean the .mbtiles file is corrupt or does not contain a 'tiles' table.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

def main():
    """Main function to parse arguments and run the extraction."""
    parser = argparse.ArgumentParser(description="Extracts tiles from an MBTiles file into a Z/X/Y directory structure.")
    parser.add_argument("input_file", help="Path to the input .mbtiles file.")
    parser.add_argument("-o", "--output", help="Path to the output directory. Defaults to a folder named after the input file.")
    parser.add_argument("--tms", action="store_true", help="Use TMS y-coordinate scheme instead of the default XYZ.")

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file not found at '{args.input_file}'")
        sys.exit(1)

    # Determine output directory
    output_dir = args.output
    if not output_dir:
        # If no output directory is specified, create one based on the input file's name
        base_name = os.path.basename(args.input_file)
        file_name_without_ext = os.path.splitext(base_name)[0]
        output_dir = f"{file_name_without_ext}_tiles"

    print(f"Input file: {args.input_file}")
    print(f"Output directory: {output_dir}")
    if args.tms:
        print("Using TMS coordinate scheme.")
    else:
        print("Using XYZ coordinate scheme (default for web maps).")

    extract_tiles(args.input_file, output_dir, args.tms)

if __name__ == "__main__":
    main()
