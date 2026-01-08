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
  
  // 检查字段是否存在
  if (regex.test(content)) {
    // 存在则替换
    return content.replace(regex, `$1${newValue}`);
  } else {
    // 不存在则添加到 frontmatter 中
    // 查找 frontmatter 的结束位置（第二个 ---）
    const frontmatterEndRegex = /^---\s*\n([\s\S]*?)\n---/m;
    const match = content.match(frontmatterEndRegex);
    
    if (match) {
      // 在第二个 --- 之前添加新字段
      const frontmatterContent = match[1];
      const newFrontmatter = `${frontmatterContent}\n${fieldName}: ${newValue}`;
      return content.replace(frontmatterEndRegex, `---\n${newFrontmatter}\n---`);
    } else {
      // 如果没有 frontmatter，创建一个
      return `---\n${fieldName}: ${newValue}\n---\n\n${content}`;
    }
  }
}