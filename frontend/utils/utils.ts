// Copyright (C) 2026 AIDC-AI
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { UNKNOW } from "@/types/public"

export const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

export const capitalize = (str: string | UNKNOW) => {
  if (!str || str === '') return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

export const updateOrAddYamlField = (content: string, fieldName: string, newValue: string) => {
  const regex = new RegExp(`(${fieldName}:\\s*)([^\\n]+)`, 'm');
  
  // Check if the field exists
  if (regex.test(content)) {
    // Field exists, replace it
    return content.replace(regex, `$1${newValue}`);
  } else {
    // Field doesn't exist, add to frontmatter
    // Find the end position of frontmatter (second ---)
    const frontmatterEndRegex = /^---\s*\n([\s\S]*?)\n---/m;
    const match = content.match(frontmatterEndRegex);
    
    if (match) {
      // Add new field before the second ---
      const frontmatterContent = match[1];
      const newFrontmatter = `${frontmatterContent}\n${fieldName}: ${newValue}`;
      return content.replace(frontmatterEndRegex, `---\n${newFrontmatter}\n---`);
    } else {
      // If no frontmatter exists, create one
      return `---\n${fieldName}: ${newValue}\n---\n\n${content}`;
    }
  }
}

// Check if the file can be previewed
export const canPreviewFile = (filename: string): boolean => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    return ['html', 'htm', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'txt', 'md', 'xlsx', 'xls', 'csv', 'pptx', 'docx'].includes(ext);
};