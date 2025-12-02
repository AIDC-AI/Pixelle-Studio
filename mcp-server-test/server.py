"""
MCP Server for Social Media Video Generation

This server provides tools for generating social media videos from user topics.
It demonstrates a complete workflow with upstream and downstream dependencies.

Workflow:
1. user_topic_prompts_tool: Generate script from topic
2. prompt_word_generationV3: Generate image prompts from script
3. t2i_flux_krea: Generate images from prompts
4. t2a_index: Generate audio from script
5. picture_subtitle: Combine image + audio into video clip
6. v_merge: Merge video clips into final video
"""

from fastmcp import FastMCP
from typing import List
import video_tools

# Initialize MCP server
mcp = FastMCP("Social Media Video Generator")


@mcp.tool()
def user_topic_prompts_tool(topic: str) -> List[str]:
    """
    Generate script segments (逐字稿) from a user topic.
    
    Args:
        topic: The video topic/title provided by the user
        
    Returns:
        List of script segments, each representing a scene
    """
    return video_tools.generate_script_from_topic(topic)


@mcp.tool()
def prompt_word_generationV3(script_segment: str) -> str:
    """
    Generate image generation prompt from a script segment.
    
    Args:
        script_segment: A single segment of the video script
        
    Returns:
        Image generation prompt in English
    """
    return video_tools.generate_image_prompt(script_segment)


@mcp.tool()
def t2i_flux_krea(image_prompt: str) -> str:
    """
    Generate image from text prompt using Flux model.
    
    Args:
        image_prompt: The text prompt for image generation
        
    Returns:
        Path to the generated image file
    """
    return video_tools.generate_image(image_prompt)


@mcp.tool()
def t2a_index(script_segment: str) -> str:
    """
    Convert script text to audio (Text-to-Audio).
    
    Args:
        script_segment: The script text to convert to speech
        
    Returns:
        Path to the generated audio file
    """
    return video_tools.generate_audio(script_segment)


@mcp.tool()
def picture_subtitle(image_path: str, audio_path: str) -> str:
    """
    Combine image and audio to create a video clip with subtitles.
    
    Args:
        image_path: Path to the image file
        audio_path: Path to the audio file
        
    Returns:
        Path to the generated video clip
    """
    return video_tools.combine_image_audio(image_path, audio_path)


@mcp.tool()
def v_merge(video_paths: List[str]) -> str:
    """
    Merge multiple video clips into a single final video.
    
    Args:
        video_paths: List of video clip paths to merge
        
    Returns:
        Path to the final merged video
    """
    return video_tools.merge_videos(video_paths)


# Example usage / test
if __name__ == "__main__":
    print("=" * 60)
    print("Social Media Video Generation MCP Server")
    print("=" * 60)
    print("\nAvailable Tools:")
    print("1. user_topic_prompts_tool - Generate script from topic")
    print("2. prompt_word_generationV3 - Generate image prompts")
    print("3. t2i_flux_krea - Text to image generation")
    print("4. t2a_index - Text to audio (TTS)")
    print("5. picture_subtitle - Combine image + audio")
    print("6. v_merge - Merge video clips")
    print("\n" + "=" * 60)
    
    # Run the server
    mcp.run()
