#!/bin/bash

# Navigate to firmwares directory
cd "/home/dominic/Documents/Claviers/ZMK-config/ZMK-firmwares"

echo "[1/3] Updating ZMK keymap from JSON..."
python3 update_keymap.py
if [ $? -ne 0 ]; then
    echo "Failed to update keymap."
    exit 1
fi

echo "[2/3] Committing and pushing to GitHub to trigger build..."
cd "/home/dominic/Documents/Claviers/ZMK-config"
git add boards/shields/optimized_fitness/optimized_fitness.keymap
git commit -m "Auto-update layout from Key Configurator"
git push
if [ $? -ne 0 ]; then
    echo "Warning: Git push failed or no changes to commit."
fi

echo "[3/3] Restarting Layout Vision overlay..."
pkill -f "python3 main.py"
sleep 1
cd "/home/dominic/Documents/Claviers/Layout Vision"
./start.sh &

echo "Pipeline completed successfully!"
