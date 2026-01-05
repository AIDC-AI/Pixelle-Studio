---
name: social-media-video
description: Generate social media videos from topics using an automated multi-step workflow. Use this skill when users request video creation, video generation, or content production for social media platforms. Triggers include requests like "create a video about X", "make a social media video", "generate video content", or any task involving automated video production from text topics.
---

# Social Media Video Generator

This skill provides a complete workflow for generating social media videos from topics using MCP tools. The process transforms a text topic into a finished video through script generation, image creation, audio synthesis, and video composition.

## Workflow Overview

The video generation process follows these steps:

1. **Script Generation** - Convert topic to script segments
2. **Prompt Generation** - Create image prompts from script
3. **Asset Generation** - Generate images and audio in parallel
4. **Clip Creation** - Combine assets into video clips
5. **Final Merge** - Merge all clips into final video

## Tool Reference

### user_topic_prompts_tool
Generate script segments from a user topic.
- **Input**: `topic` (string) - The video topic/title
- **Output**: List of script segments (逐字稿), each representing a scene
- **Purpose**: Creates the narrative foundation for the video

### prompt_word_generationV3
Generate image generation prompt from a script segment.
- **Input**: `script_segment` (string) - A single segment of the video script
- **Output**: Image generation prompt in English
- **Purpose**: Translates script narrative into visual concepts

### t2i_flux_krea
Generate image from text prompt using Flux model.
- **Input**: `image_prompt` (string) - The text prompt for image generation
- **Output**: Path to the generated image file
- **Purpose**: Creates visual content for each scene

### t2a_index
Convert script text to audio (Text-to-Audio).
- **Input**: `script_segment` (string) - The script text to convert to speech
- **Output**: Path to the generated audio file
- **Purpose**: Creates voiceover narration

### picture_subtitle
Combine image and audio to create a video clip with subtitles.
- **Input**: 
  - `image_path` (string) - Path to the image file
  - `audio_path` (string) - Path to the audio file
- **Output**: Path to the generated video clip
- **Purpose**: Synthesizes visual and audio into timed video segments

### v_merge
Merge multiple video clips into a single final video.
- **Input**: `video_paths` (list of strings) - List of video clip paths to merge
- **Output**: Path to the final merged video
- **Purpose**: Combines all scenes into cohesive final product

## Implementation Pattern

### Basic Workflow

```python
# Step 1: Generate scripts from topic
scripts = call_tool('user_topic_prompts_tool', {'topic': 'Your Topic Here'})

# Step 2-5: Process each script segment
video_clips = []
for script in scripts:
    # Generate image prompt
    prompt = call_tool('prompt_word_generationV3', {'script_segment': script})
    
    # Generate image and audio (can be parallelized)
    image = call_tool('t2i_flux_krea', {'image_prompt': prompt})
    audio = call_tool('t2a_index', {'script_segment': script})
    
    # Combine into video clip
    clip = call_tool('picture_subtitle', {
        'image_path': image,
        'audio_path': audio
    })
    video_clips.append(clip)

# Step 6: Merge all clips
final_video = call_tool('v_merge', {'video_paths': video_clips})
```

### Optimization Strategies

**Parallel Processing**: Steps 3 and 4 (image and audio generation) can run concurrently for each script segment to reduce total processing time.

**Batching**: When processing multiple script segments, consider batching operations to improve efficiency.

**Error Handling**: Each tool call should include error handling to catch and report failures at any stage of the pipeline.

## Usage Examples

### Example 1: Educational Content
```
User: "Create a video about AI programming tips"
Topic: "AI编程技巧"
```

### Example 2: Marketing Content
```
User: "Make a promotional video for our new product"
Topic: "New Product Launch - Feature Highlights"
```

### Example 3: Tutorial Content
```
User: "Generate a how-to video about cooking pasta"
Topic: "Perfect Pasta Cooking Guide"
```

## Best Practices

1. **Topic Clarity**: Ensure the input topic is specific and clear for better script generation
2. **Script Review**: Check generated scripts before proceeding if quality is critical
3. **Resource Management**: Track generated file paths for cleanup or reuse
4. **Progress Tracking**: Implement progress indicators for long video generation tasks
5. **Quality Control**: Consider implementing validation checks between pipeline stages

## Troubleshooting

**Script Generation Issues**: If scripts are too short or unclear, refine the topic description with more context.

**Image Quality**: If generated images don't match the script, review the image prompts and adjust the script segments for clearer visual descriptions.

**Audio Synchronization**: Ensure audio files match the duration expectations for their corresponding images.

**Merge Failures**: Verify all video clips are successfully generated before attempting the merge operation.

## Notes

- The workflow is designed as a pipeline where each step depends on the previous one
- Processing time scales linearly with the number of script segments
- Generated assets (images, audio, video clips) should be managed appropriately for storage
- The final video format and quality depend on the underlying tool implementations