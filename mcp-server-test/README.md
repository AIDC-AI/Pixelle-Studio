# MCP Server Test - Social Media Video Generator

This is a test MCP server demonstrating a complete video generation workflow with upstream and downstream tool dependencies.

## Tools Overview

The server provides 6 tools that work together to generate social media videos:

```
User Topic → Scripts → Image Prompts → Images
                    ↓                     ↓
                  Audio               Video Clips → Final Video
```

### Tool Chain

1. **user_topic_prompts_tool** (str → List[str])
   - Input: Video topic/title
   - Output: List of script segments (逐字稿)
   - Example: "AI编程" → ["大家好，今天聊AI编程", "首先了解背景...", ...]

2. **prompt_word_generationV3** (str → str)
   - Input: Single script segment
   - Output: Image generation prompt
   - Example: "大家好..." → "A professional presenter in modern studio..."

3. **t2i_flux_krea** (str → str)
   - Input: Image generation prompt
   - Output: Generated image path
   - Example: "A professional..." → "/storage/images/flux_gen_1234.png"

4. **t2a_index** (str → str)
   - Input: Script segment
   - Output: Generated audio path (TTS)
   - Example: "大家好..." → "/storage/audio/tts_5678.mp3"

5. **picture_subtitle** (str, str → str)
   - Input: Image path, Audio path
   - Output: Video clip path
   - Example: (image, audio) → "/storage/videos/clip_9012.mp4"

6. **v_merge** (List[str] → str)
   - Input: List of video clip paths
   - Output: Final merged video path
   - Example: [clip1, clip2, clip3] → "/storage/videos/final_video_12345.mp4"

## Installation

```bash
cd mcp-server-test
pip install -e .
```

## Running the Server

### As stdio MCP Server

```bash
python server.py
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python server.py
```

## Example Workflow

```python
# Step 1: Generate scripts from topic
scripts = user_topic_prompts_tool("AI编程技巧")
# → ["大家好，今天聊AI编程", "首先了解AI编程的背景", ...]

# Step 2-5: Process each script segment
video_clips = []
for script in scripts:
    # Generate image prompt
    prompt = prompt_word_generationV3(script)
    
    # Generate image and audio in parallel
    image = t2i_flux_krea(prompt)
    audio = t2a_index(script)
    
    # Combine into video clip
    clip = picture_subtitle(image, audio)
    video_clips.append(clip)

# Step 6: Merge all clips
final_video = v_merge(video_clips)
# → "/storage/videos/final_video_12345.mp4"
```

## Integration with Main Workflow

This MCP server can be configured in the main application's MCP configuration UI:

1. Click "⚙️ Configure MCP Servers"
2. Add new server:
   - Name: "Video Generator"
   - Type: stdio
   - Command: `python`
   - Args: `/path/to/mcp-server-test/server.py`

## Notes

- All tools return mock data (simulated file paths)
- Perfect for testing workflow orchestration
- Demonstrates complex tool dependencies
- Can be extended with real implementations
