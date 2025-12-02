"""
Example workflow script demonstrating the complete video generation pipeline.

This script shows how all 6 tools work together to create a social media video.
"""

import video_tools


def generate_video_workflow(topic: str) -> str:
    """
    Complete workflow from topic to final video.
    
    Args:
        topic: The video topic/title
        
    Returns:
        Path to the final generated video
    """
    print(f"\n{'='*60}")
    print(f"Starting video generation for topic: {topic}")
    print(f"{'='*60}\n")
    
    # Step 1: Generate script segments
    print("Step 1: Generating script segments...")
    scripts = video_tools.generate_script_from_topic(topic)
    print(f"  → Generated {len(scripts)} segments\n")
    
    # Step 2-5: Process each segment
    video_clips = []
    
    for i, script in enumerate(scripts, 1):
        print(f"Processing segment {i}/{len(scripts)}: {script[:30]}...")
        
        # Step 2: Generate image prompt
        print(f"  2. Generating image prompt...")
        image_prompt = video_tools.generate_image_prompt(script)
        
        # Step 3: Generate image
        print(f"  3. Generating image...")
        image_path = video_tools.generate_image(image_prompt)
        
        # Step 4: Generate audio (TTS)
        print(f"  4. Generating audio...")
        audio_path = video_tools.generate_audio(script)
        
        # Step 5: Combine image + audio into video clip
        print(f"  5. Creating video clip...")
        clip_path = video_tools.combine_image_audio(image_path, audio_path)
        video_clips.append(clip_path)
        print(f"  ✓ Clip {i} ready: {clip_path}\n")
    
    # Step 6: Merge all clips
    print(f"Step 6: Merging {len(video_clips)} clips into final video...")
    final_video = video_tools.merge_videos(video_clips)
    
    print(f"\n{'='*60}")
    print(f"✓ Video generation complete!")
    print(f"Final video: {final_video}")
    print(f"{'='*60}\n")
    
    return final_video


if __name__ == "__main__":
    # Example: Generate a video about AI programming
    final_video = generate_video_workflow("AI编程实战技巧")
    
    print("\n" + "="*60)
    print("Workflow Summary:")
    print("="*60)
    print("""
    ✓ Topic → Scripts (user_topic_prompts_tool)
    ✓ Script → Image Prompt (prompt_word_generationV3)
    ✓ Prompt → Image (t2i_flux_krea)
    ✓ Script → Audio (t2a_index)
    ✓ Image + Audio → Video Clip (picture_subtitle)
    ✓ Clips → Final Video (v_merge)
    """)
    print(f"Result: {final_video}")
    print("="*60)
