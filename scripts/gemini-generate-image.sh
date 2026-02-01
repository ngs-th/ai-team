#!/bin/bash

# Gemini Image Generation Script
# Usage: ./gemini-generate-image.sh "your prompt here"

# API Key should be set in environment variable
# export GEMINI_API_KEY="your-key-here"

if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ Error: GEMINI_API_KEY not set"
    echo ""
    echo "Please set your API key:"
    echo "  export GEMINI_API_KEY='your-key-here'"
    echo ""
    echo "Or add to ~/.zshrc:"
    echo "  export GEMINI_API_KEY='your-key-here'"
    exit 1
fi

PROMPT="${1:-Create a retro 90s RPG pixel art world map with fantasy landscape}"
OUTPUT_FILE="${2:-gemini-image-$(date +%Y%m%d-%H%M%S).png}"

echo "🎨 Generating image..."
echo "Prompt: $PROMPT"
echo ""

# Create temp file for response
TEMP_FILE=$(mktemp)

# Call Gemini API
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GEMINI_API_KEY" \
    -H "Content-Type: application/json" \
    -X POST \
    -d "{
        \"contents\": [{
            \"parts\": [{\"text\": \"$PROMPT\"}]
        }],
        \"generationConfig\": {
            \"responseModalities\": [\"Text\", \"Image\"]
        }
    }" > "$TEMP_FILE"

# Check if response contains image data
if grep -q "image/png" "$TEMP_FILE"; then
    # Extract base64 image data and decode
    cat "$TEMP_FILE" | jq -r '.candidates[0].content.parts[0].inlineData.data' | base64 -d > "$OUTPUT_FILE"
    echo "✅ Image saved to: $OUTPUT_FILE"
    rm "$TEMP_FILE"
else
    echo "❌ Error: No image in response"
    echo "Response:"
    cat "$TEMP_FILE" | jq .
    rm "$TEMP_FILE"
    exit 1
fi
