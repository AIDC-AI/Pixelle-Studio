"""
Core functions for video generation (without MCP decorators).
Can be used directly or wrapped by MCP tools.
"""

from typing import List
import random


def generate_script_from_topic(topic: str) -> List[str]:
    """
    Generate script segments (逐字稿) from a user topic.
    
    Args:
        topic: The video topic/title provided by the user
        
    Returns:
        List of script segments, each representing a scene
    """
    scripts = [
        f"大家好，今天我们来聊聊{topic}。",
        f"首先，让我们了解一下{topic}的背景和重要性。",
        f"接下来，我将分享几个关于{topic}的实用技巧。",
        f"这些方法已经帮助很多人成功应用{topic}。",
        f"最后，记得点赞关注，我们下期再见！"
    ]
    
    num_segments = random.randint(3, 4)
    selected_scripts = scripts[:num_segments]
    
    print(f"[generate_script] Generated {len(selected_scripts)} segments")
    return selected_scripts


def generate_image_prompt(script_segment: str) -> str:
    """
    Generate image generation prompt from a script segment.
    """
    prompts_templates = [
        "A professional presenter speaking in a modern studio with soft lighting",
        "Close-up of hands demonstrating a technique, shallow depth of field",
        "Animated infographic showing statistics and data, clean design",
        "Wide shot of a beautiful workspace with natural light, minimalist style",
        "Text overlay on gradient background, modern typography"
    ]
    
    prompt = random.choice(prompts_templates)
    print(f"[image_prompt] {prompt[:50]}...")
    return prompt


def generate_image(image_prompt: str) -> str:
    """
    Generate image from text prompt.
    """
    image_id = random.randint(1000, 9999)
    image_path = f"/storage/images/flux_gen_{image_id}.png"
    print(f"[generate_image] {image_path}")
    return image_path


def generate_audio(script_segment: str) -> str:
    """
    Convert script text to audio (TTS).
    """
    audio_id = random.randint(1000, 9999)
    audio_path = f"/storage/audio/tts_{audio_id}.mp3"
    duration = len(script_segment) * 0.15
    print(f"[generate_audio] {audio_path} ({duration:.1f}s)")
    return audio_path


def combine_image_audio(image_path: str, audio_path: str) -> str:
    """
    Combine image and audio to create a video clip.
    """
    video_id = random.randint(1000, 9999)
    video_path = f"/storage/videos/clip_{video_id}.mp4"
    print(f"[combine] Created {video_path}")
    return video_path


def merge_videos(video_paths: List[str]) -> str:
    """
    Merge multiple video clips into a single final video.
    """
    final_id = random.randint(10000, 99999)
    final_video_path = f"/storage/videos/final_video_{final_id}.mp4"
    print(f"[merge] Merged {len(video_paths)} clips → {final_video_path}")
    return final_video_path
