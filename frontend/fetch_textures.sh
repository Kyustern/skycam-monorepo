#!/bin/bash

# Script to fetch textures from Google Drive and replace the public folder

set -e

# Google Drive folder ID
FOLDER_ID="13mYryNJleOW7CN0h-2rXiLhuRIScmWYV"

# Target directory
TARGET_DIR="/home/leon/DEV/DOCKER/TURRET/frontend/public"

# Temporary directory
TEMP_DIR="/tmp/textures_download_$$"

# Cleanup function
cleanup() {
    echo "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# Register cleanup on exit
trap cleanup EXIT

echo "Creating temporary directory: $TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Change to temp directory
cd "$TEMP_DIR"

echo "Downloading files from Google Drive folder: $FOLDER_ID"

# Download favicon.svg (ID: 1eTts7OAav7s_rPjS3IF9Us1YnfB1GFGt)
echo "Downloading favicon.svg..."
gdown 1eTts7OAav7s_rPjS3IF9Us1YnfB1GFGt -O favicon.svg

# Download icons.svg (ID: 1VMfsgVm7e33LQboto_4PCmqXSXGuUePR)
echo "Downloading icons.svg..."
gdown 1VMfsgVm7e33LQboto_4PCmqXSXGuUePR -O icons.svg

# Download assets folder (ID: 1SkTWWsmvUY_CPCIEjape7KcnApYIGXnn)
echo "Downloading assets folder..."
gdown --folder 1SkTWWsmvUY_CPCIEjape7KcnApYIGXnn -O assets

echo "All files downloaded successfully!"

# Verify downloaded files
echo "Verifying downloaded files..."
ls -la favicon.svg
ls -la icons.svg
ls -la assets/

# Create the new public folder structure
echo "Creating new public folder..."
NEW_PUBLIC="$TEMP_DIR/public"
mkdir -p "$NEW_PUBLIC"

# Copy files to new public folder
cp favicon.svg "$NEW_PUBLIC/"
cp icons.svg "$NEW_PUBLIC/"
cp -r assets "$NEW_PUBLIC/"

# Verify new public folder structure
echo "New public folder structure:"
find "$NEW_PUBLIC" -type f | sort

# Backup existing public folder
echo "Backing up existing public folder..."
BACKUP_DIR="${TARGET_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
cp -r "$TARGET_DIR" "$BACKUP_DIR"
echo "Backup created at: $BACKUP_DIR"

# Replace the old public folder with the new one
echo "Replacing public folder..."
rm -rf "$TARGET_DIR"
mv "$NEW_PUBLIC" "$TARGET_DIR"

echo "Done! Public folder has been replaced with the new textures."

# Show the new structure
echo "New public folder contents:"
find "$TARGET_DIR" -type f | sort
