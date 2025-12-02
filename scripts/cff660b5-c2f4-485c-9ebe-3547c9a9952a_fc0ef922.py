
import sys
import asyncio
import json
import os
from app.mcp_client import call_tool, upload_result

# Server Configuration
from app.mcp_client import register_tool_server

register_tool_server('user_topic_prompts_tool', 'http://127.0.0.1:8002/sse', 'sse')
register_tool_server('prompt_word_generationV3', 'http://127.0.0.1:8002/sse', 'sse')
register_tool_server('t2i_flux_krea', 'http://127.0.0.1:8002/sse', 'sse')
register_tool_server('t2a_index', 'http://127.0.0.1:8002/sse', 'sse')
register_tool_server('picture_subtitle', 'http://127.0.0.1:8002/sse', 'sse')
register_tool_server('v_merge', 'http://127.0.0.1:8002/sse', 'sse')



from app.mcp_client import call_tool, upload_result
import asyncio

async def main():
    topic = "如何治愈原生家庭"
    print(f"Starting video generation workflow for topic: {topic}")

    # Step 1: Generate script segments based on the topic
    print("Step 1: Generating script segments...")
    script_segments = await call_tool('user_topic_prompts_tool', {'topic': topic})
    
    if not script_segments or not isinstance(script_segments, list):
        return {
            "status": "error", 
            "summary": "Failed to generate valid script segments."
        }
    
    print(f"Generated {len(script_segments)} segments.")
    
    video_clips = []

    # Step 2: Process each segment to create video clips
    for index, segment in enumerate(script_segments):
        print(f"Processing segment {index + 1}/{len(script_segments)}...")
        
        # 2a: Generate image prompt from script
        image_prompt = await call_tool('prompt_word_generationV3', {'script_segment': segment})
        
        # 2b: Generate image from prompt
        image_path = await call_tool('t2i_flux_krea', {'image_prompt': image_prompt})
        
        # 2c: Generate audio from script
        audio_path = await call_tool('t2a_index', {'script_segment': segment})
        
        # 2d: Combine image and audio into a subtitled video clip
        clip_path = await call_tool('picture_subtitle', {
            'image_path': image_path,
            'audio_path': audio_path
        })
        
        video_clips.append(clip_path)
        print(f"Clip {index + 1} created: {clip_path}")

    # Step 3: Merge all clips into the final video
    if video_clips:
        print("Step 3: Merging video clips...")
        final_video_path = await call_tool('v_merge', {'video_paths': video_clips})
        
        print(f"Final video generated: {final_video_path}")
        
        return {
            "status": "success",
            "summary": f"Video generated successfully: {final_video_path}",
            "files": [final_video_path]
        }
    else:
        return {
            "status": "error",
            "summary": "No video clips were generated."
        }

if __name__ == "__main__":
    try:
        # Run the async main function
        result = asyncio.run(main())
        # Print the result as the last line of stdout
        print(json.dumps(result))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(json.dumps({"status": "error", "error": str(e)}))
