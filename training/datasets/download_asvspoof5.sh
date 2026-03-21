#!/bin/bash
# Download ASVspoof 5 dataset for deepfake detection training.
# Run on Colab or a machine with sufficient storage (~50GB).

set -e

DATA_DIR="$(dirname "$0")/data/asvspoof5"
mkdir -p "$DATA_DIR"

echo "=== MoneySpeaks: ASVspoof 5 Dataset Download ==="
echo "Target directory: $DATA_DIR"
echo ""

# ASVspoof 5 is distributed via CodaLab / Zenodo
# Registration required at: https://www.asvspoof.org/
# After registration, set ASVSPOOF_TOKEN in your environment

if [ -z "$ASVSPOOF_TOKEN" ]; then
    echo "WARNING: ASVSPOOF_TOKEN not set."
    echo "To download ASVspoof 5:"
    echo "  1. Register at https://www.asvspoof.org/"
    echo "  2. Accept data usage agreement"
    echo "  3. Set ASVSPOOF_TOKEN=<your_token>"
    echo ""
    echo "For now, creating placeholder structure for training script compatibility."
    echo ""

    # Create placeholder structure
    mkdir -p "$DATA_DIR/train/bonafide"
    mkdir -p "$DATA_DIR/train/spoof"
    mkdir -p "$DATA_DIR/eval/bonafide"
    mkdir -p "$DATA_DIR/eval/spoof"

    echo "Placeholder created. Training script will use mock data."
    exit 0
fi

echo "Downloading ASVspoof 5 training set..."
# wget or curl commands would go here with the actual download URLs
# These are placeholders — actual URLs require authentication

echo ""
echo "=== Additional datasets ==="

# MLAAD (Multilingual Audio Anti-spoofing Dataset)
echo "For MLAAD, see: https://github.com/MLAAD/MLAAD"
echo "Download manually and place in $DATA_DIR/../mlaad/"

# CodecFake subset A2
echo "For CodecFake, see: https://github.com/codecfake/codecfake"
echo "Download subset A2 and place in $DATA_DIR/../codecfake/"

# LibriSpeech genuine speech (for paired real samples)
echo ""
echo "Downloading LibriSpeech test-clean (genuine speech)..."
LIBRI_DIR="$DATA_DIR/../librispeech"
mkdir -p "$LIBRI_DIR"

if command -v wget &> /dev/null; then
    wget -c "https://www.openslr.org/resources/12/test-clean.tar.gz" -P "$LIBRI_DIR"
    tar -xzf "$LIBRI_DIR/test-clean.tar.gz" -C "$LIBRI_DIR"
elif command -v curl &> /dev/null; then
    curl -L -C - "https://www.openslr.org/resources/12/test-clean.tar.gz" -o "$LIBRI_DIR/test-clean.tar.gz"
    tar -xzf "$LIBRI_DIR/test-clean.tar.gz" -C "$LIBRI_DIR"
fi

echo ""
echo "=== Dataset download complete ==="
echo "Structure:"
echo "  $DATA_DIR/train/bonafide/  — real speech"
echo "  $DATA_DIR/train/spoof/     — synthetic speech"
echo "  $DATA_DIR/eval/bonafide/   — held-out real"
echo "  $DATA_DIR/eval/spoof/      — held-out synthetic"
