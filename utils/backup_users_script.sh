#!/bin/bash

# Set variables
REMOTE_USER="root"
REMOTE_HOST="" # remove ip for security
REMOTE_FILE="/root/Concept_booker/users.csv"  # Adjust this path if needed
LOCAL_BACKUP_DIR="/Users/melodiz/projects/Concept_booker/users_backups"
SSH_KEY="/Users/melodiz/.ssh/hse_booking_bot"

# Create backup directory if it doesn't exist
mkdir -p "$LOCAL_BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Perform the copy using the specific SSH key
scp -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_FILE" "$LOCAL_BACKUP_DIR/users_backup_$TIMESTAMP.csv"

