
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



import sys
import asyncio
from app.mcp_client import call_tool, upload_result

async def main():
    # Get topic from command line arguments to allow external input
    # Default to "如何治愈原生家庭" if no argument is provided
    if len(sys.argv) > 1:
        topic = sys.argv[1]
    else:
        topic = "如何治愈原生家庭"
    
    print(f"Starting video generation workflow for topic: {topic}")

    try:
        # Step 1: Generate script segments based on the topic
        print("Generating script segments...")
        segments = await call_tool('user_topic_prompts_tool', {'topic': topic})
        
        if not segments or not isinstance(segments, list):
            print("Error: Failed to generate script segments.")
            return {"status": "error", "summary": "Failed to generate script segments"}

        print(f"Generated {len(segments)} segments.")
        
        video_clips = []
        
        # Process each segment
        for index, segment in enumerate(segments):
            print(f"Processing segment {index + 1}/{len(segments)}...")
            
            # Step 2: Generate image prompt for the segment
            image_prompt = await call_tool('prompt_word_generationV3', {'script_segment': segment})
            
            # Step 3: Generate image from the prompt
            image_path = await call_tool('t2i_flux_krea', {'image_prompt': image_prompt})
            
            # Step 4: Generate audio from the script segment
            audio_path = await call_tool('t2a_index', {'script_segment': segment})
            
            # Step 5: Combine image and audio into a video clip with subtitles
            video_path = await call_tool('picture_subtitle', {
                'image_path': image_path, 
                'audio_path': audio_path
            })
            
            video_clips.append(video_path)
        
        # Step 6: Merge all video clips into the final video
        print("Merging video clips...")
        final_video_path = await call_tool('v_merge', {'video_paths': video_clips})
        
        print(f"Workflow completed successfully. Final video: {final_video_path}")
        
        return {
            "status": "success",
            "summary": f"Video generated for topic '{topic}'",
            "video_path": final_video_path
        }

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {
            "status": "error",
            "summary": str(e)
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
