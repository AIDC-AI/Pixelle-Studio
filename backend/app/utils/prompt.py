from typing import Optional, List


def get_full_message(user_message: str, file_urls: List[str], file_names: List[str]) -> str:
        # Build initial user message with file context
    full_user_message = user_message.strip()
    
    if file_names:
        full_user_message += "\n\n## User Uploaded Files:\n"
        full_user_message += "These files are in your current working directory. Access them directly by filename:\n"
        for name in file_names:
            full_user_message += f"- {name}\n"
    elif file_urls:
        full_user_message += "\n\n## User Uploaded Files:\n"
        full_user_message += "These files are in your current working directory. Access them directly by filename:\n"
        for url in file_urls:
            filename = url.split("/")[-1]
            full_user_message += f"- {filename}\n"
    return full_user_message