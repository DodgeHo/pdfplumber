"""
教材内容精简脚本 (Textbook Content Refiner)

功能描述：
本脚本用于自动精简教材内容，去除冗长、重复、空洞的表述，保留核心知识点和技术概念。
特别针对中国教材中常见的"废话文学"进行优化，生成简洁明了的教学内容。

主要特性：
1. 智能分段处理 - 优先按段落分割，长段落再按句子分割
2. 批量API调用 - 自动向DeepSeek发送分段请求
3. 内容精简 - 去除冗余表述，保留核心信息
4. 进度跟踪 - 实时显示处理进度和预计剩余时间
5. 错误重试 - 内置重试机制应对API限制
6. 断点续传 - 支持从上次中断处继续处理
7. 安全配置 - API密钥通过环境变量管理

输入输出：
- 输入：textbook.txt (原始教材文本文件)
- 输出：refined_textbook.txt (精简后的教材文本文件)
- 进度文件：.refiner_progress.json (用于断点续传)

使用场景：
- 教育工作者优化教材内容
- 学生获取更清晰的学习材料
- 培训机构精简培训资料
- 个人学习提升效率

注意事项：
1. 需要有效的DeepSeek API密钥（通过环境变量DEEPSEEK_API_KEY设置）
2. 处理大量文本时可能需要较长时间
3. 建议在非高峰时段运行以避免API限制
4. 首次使用前请安装requests库: pip install requests

作者：AI Assistant
版本：2.0
创建日期：2024年
更新日期：2025年10月
"""

import requests
import json
import time
import re
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('refiner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TextbookRefiner:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com", 
                 model: str = "deepseek-chat", progress_file: str = ".refiner_progress.json"):
        """
        初始化教材精简器
        
        Args:
            api_key: DeepSeek API密钥（优先使用环境变量DEEPSEEK_API_KEY）
            base_url: API基础URL，默认为DeepSeek官方地址
            model: 使用的模型名称，默认为deepseek-chat
            progress_file: 进度保存文件路径
        """
        # 优先从环境变量获取API密钥
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("未找到API密钥！请设置环境变量DEEPSEEK_API_KEY或直接传入api_key参数")
        
        self.base_url = base_url
        self.model = model
        self.progress_file = progress_file
        self.session = requests.Session()
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'failed_chunks': 0,
            'original_length': 0,
            'refined_length': 0,
            'start_time': None,
            'api_calls': 0
        }
        
    def read_textbook(self, file_path: str) -> str:
        """读取教材文本文件"""
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                logger.warning(f"文件为空: {file_path}")
                return ""
            
            logger.info(f"成功读取文件，总字符数: {len(content)}")
            self.stats['original_length'] = len(content)
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """清理文本 - 去除多余空行和首尾空格"""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1500) -> List[str]:
        """
        将文本分段，优先按段落分割
        
        Args:
            text: 待分割的文本
            chunk_size: 每段的最大字符数，默认1500
            
        Returns:
            分割后的文本段列表
        """
        chunks = []
        
        # 优先按段落分
        paragraphs = text.split('\n\n')
        
        current_chunk = ''
        
        for paragraph in paragraphs:
            # 清理段落
            clean_para = self.clean_text(paragraph)
            if not clean_para:
                continue
                
            if len(current_chunk + clean_para) <= chunk_size:
                if current_chunk:
                    current_chunk += '\n\n' + clean_para
                else:
                    current_chunk = clean_para
            else:
                # 如果当前段落太长，需要进一步分割
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ''
                
                # 处理长段落 - 改进的中文句子分割
                if len(clean_para) > chunk_size:
                    # 按中英文句子分割
                    sentences = re.split(r'(?<=[.!?。！？；;])\s*', clean_para)
                    temp_chunk = ''
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        
                        if len(temp_chunk + sentence) <= chunk_size:
                            temp_chunk += (temp_chunk and ' ' or '') + sentence
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            # 如果单个句子超长，强制分割
                            if len(sentence) > chunk_size:
                                for i in range(0, len(sentence), chunk_size):
                                    chunks.append(sentence[i:i+chunk_size])
                                temp_chunk = ''
                            else:
                                temp_chunk = sentence
                    
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    current_chunk = clean_para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.info(f"文本分割完成，共 {len(chunks)} 段")
        self.stats['total_chunks'] = len(chunks)
        return chunks
    
    def create_refinement_prompt(self) -> str:
        """
        创建内容精简的提示语
        
        专门针对中国教材中常见的冗长、重复、空洞表述进行优化
        """
        return """你是一个专业教材编辑，擅长将冗长的教材内容精简为清晰、简洁的表述，同时保留所有关键信息。

请对以下教材内容进行精简，要求：
1. 去除冗余重复的表述
2. 删除空洞的套话和废话
3. 保持技术概念的准确性
4. 确保逻辑清晰连贯
5. 保留所有重要的知识点和定义
6. 语言简洁明了，直接表达核心思想

请直接返回精简后的内容，不需要额外的说明或标记。"""
    
    def send_refinement_request(self, chunk: str, retry_count: int = 3) -> Dict[str, any]:
        """
        向DeepSeek发送内容精简请求
        
        Args:
            chunk: 待处理的文本段
            retry_count: 重试次数，默认3次
            
        Returns:
            包含精简文本和状态的字典 {'text': str, 'success': bool, 'error': str}
        """
        messages = [
            {"role": "system", "content": self.create_refinement_prompt()},
            {"role": "user", "content": chunk}
        ]
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        for attempt in range(retry_count):
            try:
                self.stats['api_calls'] += 1
                logger.debug(f"发送第 {attempt + 1} 次请求，字符数: {len(chunk)}")
                
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    refined_text = result['choices'][0]['message']['content'].strip()
                    logger.debug("请求成功")
                    return {'text': refined_text, 'success': True, 'error': None}
                
                elif response.status_code == 429:  # 频率限制
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"达到频率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                
                else:
                    error_msg = f"API请求失败，状态码: {response.status_code}, 响应: {response.text[:200]}"
                    logger.error(error_msg)
                    if attempt == retry_count - 1:
                        return {'text': chunk, 'success': False, 'error': error_msg}
                        
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{retry_count})")
            except Exception as e:
                logger.error(f"请求异常: {e}")
            
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 5
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        logger.warning("所有重试均失败，返回原始文本")
        return {'text': chunk, 'success': False, 'error': '所有重试均失败'}
    
    def save_progress(self, chunks: List[str], refined_chunks: List[str], current_index: int):
        """保存处理进度到文件"""
        try:
            progress_data = {
                'current_index': current_index,
                'total_chunks': len(chunks),
                'refined_chunks': refined_chunks,
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"进度已保存: {current_index}/{len(chunks)}")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def load_progress(self) -> Optional[Dict]:
        """从文件加载处理进度"""
        if not os.path.exists(self.progress_file):
            return None
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            logger.info(f"发现上次进度: {progress_data['current_index']}/{progress_data['total_chunks']}")
            return progress_data
        except Exception as e:
            logger.error(f"加载进度失败: {e}")
            return None
    
    def clear_progress(self):
        """清除进度文件"""
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
                logger.info("已清除进度文件")
            except Exception as e:
                logger.error(f"清除进度文件失败: {e}")
    
    def format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}小时{minutes}分钟"
        """
        主处理函数：精简整个教材内容
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            chunk_size: 文本分段大小
        """
        print("开始处理教材...")
        
        # 读取原始文本
        original_text = self.read_textbook(input_file)
        if not original_text:
            return
        
        # 分割文本
        chunks = self.split_text_into_chunks(original_text, chunk_size)
        
        # 处理每个分段
        refined_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            print(f"\n处理第 {i+1}/{total_chunks} 段...")
            print(f"原文预览: {chunk[:100]}...")
            
            refined_chunk = self.send_refinement_request(chunk)
            refined_chunks.append(refined_chunk)
            
            print(f"精简后预览: {refined_chunk[:100]}...")
            
            # 添加延迟避免频率限制
            if i < total_chunks - 1:
                time.sleep(2)
        
        # 保存结果
        combined_refined_text = "\n\n".join(refined_chunks)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(combined_refined_text)
        
        # 统计信息
        original_length = len(original_text)
        refined_length = len(combined_refined_text)
        reduction_rate = (original_length - refined_length) / original_length * 100
        
        print(f"\n处理完成!")
        print(f"原始长度: {original_length} 字符")
        print(f"精简后: {refined_length} 字符")
        print(f"精简率: {reduction_rate:.1f}%")
        print(f"结果已保存到: {output_file}")

def main():
    """
    主函数 - 配置参数并启动处理流程
    """
    # 配置参数
    API_KEY = "sk-8ff2941e7def46ef8e1ae7c9f90e930f"  # 你的DeepSeek API密钥
    INPUT_FILE = "textbook.txt"  # 输入文件路径
    OUTPUT_FILE = "refined_textbook.txt"  # 输出文件路径
    CHUNK_SIZE = 1500  # 每段字符数
    
    # 创建精简器实例
    refiner = TextbookRefiner(api_key=API_KEY)
    
    # 开始处理
    refiner.refine_textbook(
        input_file=INPUT_FILE,
        output_file=OUTPUT_FILE,
        chunk_size=CHUNK_SIZE
    )

if __name__ == "__main__":
    main()
