---
name: pollinations-image-gen
version: 1.0.0
description: >
  Generate images using Pollinations.ai free API - no API key required.
  Supports various art styles including pixel art, RPG, fantasy, and more.
  This skill provides free image generation for MCOP Quest and other projects.
tags: [image-generation, pollinations, pixel-art, rpg, free-api]
---

# Pollinations Image Generation Skill

## Overview

Generate high-quality images using Pollinations.ai's free API. No API key required, no rate limits.

**Perfect for:**
- RPG game assets (world maps, icons, characters)
- Pixel art generation
- UI mockups and wireframes
- Concept art

## Installation

The tool script is located at:
```
~/.config/claudeskills/pollinations-generate-tool.sh
```

Or use the global command:
```bash
pollinations-gen "your prompt" [width] [height] [output.png]
```

## Usage

### Basic Usage
```bash
# Default 1024x1024
~/.config/claudeskills/pollinations-generate-tool.sh "retro RPG pixel art world map"

# Custom size
~/.config/claudeskills/pollinations-generate-tool.sh "pixel art sword icon" 512 512 sword.png
```

### From Claude Code

When you need to generate an image, use the bash tool to run:

```bash
export PATH="$HOME/bin:$PATH" && pollinations-gen "retro 90s RPG pixel art world map Bangkok fantasy SNES style" 1024 1024 "mcop-world-map.png"
```

### Prompt Engineering Tips

**For Pixel Art / RPG Style:**
- Include: "pixel art", "16-bit", "SNES", "retro", "RPG", "fantasy"
- Example: "16-bit pixel art RPG world map, SNES style, fantasy landscape"

**For UI/Icons:**
- Include: "game UI", "icon", "minimalist", "clean design"
- Example: "pixel art RPG item icon, sword, minimalist"

**For Characters:**
- Include: "character sprite", "pixel art", "RPG class", "fantasy"
- Example: "pixel art warrior character sprite, RPG fantasy style"

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prompt | string | required | Image description. Be detailed and specific. |
| width | number | 1024 | Image width in pixels |
| height | number | 1024 | Image height in pixels |
| output_file | string | auto | Output filename |

## Examples

### MCOP Quest World Map
```bash
pollinations-gen \
  "retro 90s RPG pixel art world map, SNES style, fantasy landscape with castles, dungeons as cave entrances, quest markers, forests, mountains, top-down view, grid-based, vibrant colors" \
  1024 1024 \
  "mcop-world-map.png"
```

### RPG Item Icons
```bash
pollinations-gen "pixel art RPG potion icon, red health potion, 16-bit style" 128 128 potion.png
pollinations-gen "pixel art RPG sword icon, iron sword, fantasy style" 128 128 sword.png
pollinations-gen "pixel art RPG shield icon, wooden shield, retro style" 128 128 shield.png
```

### Character Sprites
```bash
pollinations-gen "pixel art RPG character sprite, mage class, purple robe, staff, 16-bit SNES style" 256 256 mage-sprite.png
```

## Output

The tool returns JSON:
```json
{
  "success": true,
  "file": "output.png",
  "type": "JPEG image data, 1024x1024",
  "size": "175K",
  "width": 1024,
  "height": 1024,
  "prompt": "your prompt"
}
```

## Notes

- **Free forever**: No API key, no credits, no limits
- **Quality varies**: May need multiple attempts for best results
- **File format**: Usually JPEG despite .png extension
- **Seed randomization**: Each request uses random seed for variety

## Troubleshooting

**Image not generated:**
- Check internet connection
- Try simpler prompt
- Check if output directory is writable

**Quality not good:**
- Add more specific keywords ("SNES", "16-bit", "pixel art")
- Try variations with different seeds
- Be more detailed in description

## Related Skills

- `ui-ux-pro-max` - For UI design patterns
- `pixel-art` - For pixel art specific techniques
- `rpg-assets` - For RPG game asset creation

## Version History

- 1.0.0 (2026-01-30): Initial release
  - Basic image generation via Pollinations.ai
  - Support for custom dimensions
  - JSON output format
