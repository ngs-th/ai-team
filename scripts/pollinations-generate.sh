#!/bin/bash

# Pollinations AI Image Generation Script
# Free image generation, no API key required
# Usage: ./pollinations-generate.sh "your prompt" [output_filename]

# Encode URL function
url_encode() {
    local string="$1"
    local encoded=""
    local pos c o
    
    for (( pos=0; pos<${#string}; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9]) encoded+="$c" ;;
            *) printf -v o '%%%02x' "'$c"; encoded+="$o" ;;
        esac
    done
    echo "$encoded"
}

# Default prompt
PROMPT="${1:-Create a retro 90s RPG pixel art world map with fantasy landscape}"
OUTPUT_FILE="${2:-pollinations-image-$(date +%Y%m%d-%H%M%S).png}"

# URL encode the prompt
ENCODED_PROMPT=$(url_encode "$PROMPT")

echo "🎨 Generating image with Pollinations.ai..."
echo "Prompt: $PROMPT"
echo ""

# Call Pollinations API
if curl -s "https://image.pollinations.ai/prompt/${ENCODED_PROMPT}?width=1024&height=1024&seed=$RANDOM&nologo=true" \
    -H "User-Agent: Mozilla/5.0" \
    --output "$OUTPUT_FILE"; then
    
    # Check if file was created and has content
    if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
        # Check if it's a valid image
        file_type=$(file -b "$OUTPUT_FILE" | head -1)
        if echo "$file_type" | grep -q "image\|PNG\|JPEG\|bitmap"; then
            echo "✅ Image saved to: $OUTPUT_FILE"
            echo "📐 File type: $file_type"
            ls -lh "$OUTPUT_FILE"
        else
            echo "❌ Error: Downloaded file is not a valid image"
            echo "File type: $file_type"
            rm "$OUTPUT_FILE"
            exit 1
        fi
    else
        echo "❌ Error: Failed to download image"
        exit 1
    fi
else
    echo "❌ Error: API request failed"
    exit 1
fi
