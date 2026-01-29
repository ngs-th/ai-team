#!/bin/bash
# Pollinations Image Generation Tool for kimi-cli skill
# Usage: generate-image "prompt" [width] [height] [output_file]

PROMPT="$1"
WIDTH="${2:-1024}"
HEIGHT="${3:-1024}"
OUTPUT_FILE="${4:-pollinations-$(date +%Y%m%d-%H%M%S).png}"

if [ -z "$PROMPT" ]; then
    echo '{"error": "No prompt provided"}'
    exit 1
fi

# URL encode
url_encode() {
    local string="$1"
    local encoded=""
    for (( pos=0; pos<${#string}; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9]) encoded+="$c" ;;
            *) printf -v o '%%%02x' "'$c"; encoded+="$o" ;;
        esac
    done
    echo "$encoded"
}

ENCODED=$(url_encode "$PROMPT")
SEED=$((RANDOM % 10000))

# Download image
if curl -s "https://image.pollinations.ai/prompt/${ENCODED}?width=${WIDTH}&height=${HEIGHT}&seed=${SEED}&nologo=true" \
    -H "User-Agent: Mozilla/5.0" \
    --output "$OUTPUT_FILE" 2>/dev/null; then
    
    if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
        FILE_TYPE=$(file -b "$OUTPUT_FILE" | head -1)
        FILE_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
        
        if echo "$FILE_TYPE" | grep -qi "image\|png\|jpeg\|bitmap"; then
            echo "{"
            echo "  \"success\": true,"
            echo "  \"file\": \"$OUTPUT_FILE\","
            echo "  \"type\": \"$FILE_TYPE\","
            echo "  \"size\": \"$FILE_SIZE\","
            echo "  \"width\": $WIDTH,"
            echo "  \"height\": $HEIGHT,"
            echo "  \"prompt\": \"$PROMPT\""
            echo "}"
        else
            rm "$OUTPUT_FILE"
            echo '{"error": "Invalid image downloaded"}'
            exit 1
        fi
    else
        echo '{"error": "Failed to download image"}'
        exit 1
    fi
else
    echo '{"error": "API request failed"}'
    exit 1
fi
