"""
教材内容智能二次精简脚本 (Smart Textbook Refiner) v3.0

功能描述：
本脚本对已精简过的教材进行二次智能优化。与v2版本不同，本脚本让AI先判断内容是否需要精简，
只对真正冗长、重复的内容进行优化，保留已经简洁明了的段落。

核心特性：
1. 智能评估 - AI先判断每段是否需要精简（评分1-10）
2. 条件处理 - 只处理评分≥6的段落（确实需要精简的内容）
3. 保留原文 - 评分<6的段落直接保留，节省API调用
4. 思考过程 - 记录AI的判断理由，便于理解决策
5. 双阶段处理 - 第一阶段评估，第二阶段精简
6. 详细统计 - 记录保留、精简、跳过的段落数量

使用场景：
- 对已精简的教材进行二次优化
- 避免过度精简导致信息丢失
- 让AI自主判断哪些内容真正需要优化

输入输出：
- 输入：refined_textbook.txt (一次精简后的文本)
- 输出：refined_textbook_v2.txt (二次精简后的文本)
- 评估日志：refiner_v3_evaluation.log (AI的判断过程)
- 进度文件：.refiner_v3_progress.json (断点续传)

作者：AI Assistant
版本：3.0
创建日期：2025年10月
"""

import requests
import json
import time
import re
import os
import logging
import argparse
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('refiner_v3.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 单独的评估日志
eval_logger = logging.getLogger('evaluation')
eval_handler = logging.FileHandler('refiner_v3_evaluation.log', encoding='utf-8')
eval_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
eval_logger.addHandler(eval_handler)
eval_logger.setLevel(logging.INFO)


class SmartTextbookRefiner:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com", 
                 model: str = "deepseek-chat", progress_file: str = ".refiner_v3_progress.json"):
        """
        初始化智能教材精简器
        
        Args:
            api_key: DeepSeek API密钥（优先使用环境变量DEEPSEEK_API_KEY）
            base_url: API基础URL
            model: 使用的模型名称
            progress_file: 进度保存文件路径
        """
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("未找到API密钥！请设置环境变量DEEPSEEK_API_KEY或直接传入api_key参数")
        
        self.base_url = base_url
        self.model = model
        self.progress_file = progress_file
        self.session = requests.Session()
        self.stats = {
            'total_chunks': 0,
            'evaluated_chunks': 0,
            'kept_original': 0,  # 保留原文的段落
            'refined_chunks': 0,  # 精简的段落
            'failed_chunks': 0,
            'original_length': 0,
            'final_length': 0,
            'start_time': None,
            'api_calls': 0,
            'score_distribution': {}  # 评分分布统计
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
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 2000) -> List[str]:
        """
        将文本分段，优先按段落分割
        
        Args:
            text: 待分割的文本
            chunk_size: 每段的最大字符数，默认2000（比v2大一些）
            
        Returns:
            分割后的文本段列表
        """
        chunks = []
        paragraphs = text.split('\n\n')
        
        current_chunk = ''
        
        for paragraph in paragraphs:
            clean_para = paragraph.strip()
            if not clean_para:
                continue
                
            if len(current_chunk + clean_para) <= chunk_size:
                if current_chunk:
                    current_chunk += '\n\n' + clean_para
                else:
                    current_chunk = clean_para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ''
                
                if len(clean_para) > chunk_size:
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
    
    def create_evaluation_prompt(self) -> str:
        """
        创建内容评估的提示语 - 让AI判断是否需要精简
        """
        return """你是一个专业的教材编辑专家。请评估以下教材内容是否需要进一步精简。

评估标准：
1. 内容是否冗长、重复？
2. 是否包含空洞的套话？
3. 表述是否可以更简洁？
4. 逻辑是否清晰直接？
5. 是否有不必要的修饰词？

请按以下JSON格式返回评估结果：
{
  "score": 评分(1-10),
  "reason": "判断理由",
  "needs_refinement": true/false
}

评分说明：
1-3分：内容简洁明了，无需精简
4-5分：基本清晰，略有改进空间但不必要
6-7分：有一定冗余，建议精简
8-9分：明显冗长，需要精简
10分：严重冗余，必须大幅精简

needs_refinement 判断：
- score >= 6: true (需要精简)
- score < 6: false (保留原文)

请仅返回JSON格式，不要添加任何其他文字。"""
    
    def create_refinement_prompt(self) -> str:
        """
        创建内容精简的提示语（与v2相同）
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
    
    def send_api_request(self, system_prompt: str, user_content: str, 
                        retry_count: int = 3) -> Dict[str, any]:
        """
        向DeepSeek发送API请求（通用方法）
        
        Args:
            system_prompt: 系统提示语
            user_content: 用户内容
            retry_count: 重试次数
            
        Returns:
            包含响应文本和状态的字典
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
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
                logger.debug(f"发送第 {attempt + 1} 次请求")
                
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result['choices'][0]['message']['content'].strip()
                    logger.debug("请求成功")
                    return {'text': response_text, 'success': True, 'error': None}
                
                elif response.status_code == 429:
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"达到频率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                
                else:
                    error_msg = f"API请求失败，状态码: {response.status_code}"
                    logger.error(error_msg)
                    if attempt == retry_count - 1:
                        return {'text': '', 'success': False, 'error': error_msg}
                        
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{retry_count})")
            except Exception as e:
                logger.error(f"请求异常: {e}")
            
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 5
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        return {'text': '', 'success': False, 'error': '所有重试均失败'}
    
    def evaluate_chunk(self, chunk: str) -> Tuple[int, str, bool]:
        """
        评估文本段是否需要精简
        
        Args:
            chunk: 待评估的文本段
            
        Returns:
            (评分, 理由, 是否需要精简)
        """
        result = self.send_api_request(self.create_evaluation_prompt(), chunk)
        
        if not result['success']:
            logger.warning("评估失败，默认保留原文")
            return (5, "评估失败，保留原文", False)
        
        try:
            # 尝试解析JSON响应
            response_text = result['text']
            
            # 如果响应被包裹在```json```中，提取出来
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            eval_result = json.loads(response_text)
            score = int(eval_result.get('score', 5))
            reason = eval_result.get('reason', '无理由')
            needs_refinement = eval_result.get('needs_refinement', score >= 6)
            
            # 记录评分分布
            score_key = f"{score}分"
            self.stats['score_distribution'][score_key] = \
                self.stats['score_distribution'].get(score_key, 0) + 1
            
            return (score, reason, needs_refinement)
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析评估结果失败: {e}, 响应: {result['text'][:100]}")
            return (5, "解析失败，保留原文", False)
        except Exception as e:
            logger.error(f"处理评估结果异常: {e}")
            return (5, "处理异常，保留原文", False)
    
    def refine_chunk(self, chunk: str) -> Dict[str, any]:
        """
        精简文本段
        
        Args:
            chunk: 待精简的文本段
            
        Returns:
            包含精简文本和状态的字典
        """
        result = self.send_api_request(self.create_refinement_prompt(), chunk)
        
        if result['success']:
            return {'text': result['text'], 'success': True, 'error': None}
        else:
            logger.warning("精简失败，返回原文")
            return {'text': chunk, 'success': False, 'error': result['error']}
    
    def save_progress(self, total_chunks: int, current_index: int):
        """保存处理进度到文件"""
        try:
            progress_data = {
                'current_index': current_index,
                'total_chunks': total_chunks,
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"进度已保存: {current_index}/{total_chunks}")
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
    
    def smart_refine_textbook(self, input_file: str, output_file: str, 
                             chunk_size: int = 2000, resume: bool = True,
                             refinement_threshold: int = 6):
        """
        主处理函数：智能二次精简教材内容
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            chunk_size: 文本分段大小
            resume: 是否从上次中断处继续
            refinement_threshold: 精简阈值（评分>=此值才精简）
        """
        logger.info("="*60)
        logger.info("开始智能二次精简处理...")
        logger.info(f"精简阈值: {refinement_threshold}分")
        self.stats['start_time'] = time.time()
        
        # 检查进度
        progress_data = None
        if resume:
            progress_data = self.load_progress()
            if progress_data:
                try:
                    user_input = input("发现未完成的处理进度，是否继续？(y/n): ").lower()
                    if user_input != 'y':
                        progress_data = None
                        self.clear_progress()
                except:
                    logger.info("非交互式环境，自动继续上次进度")
        
        # 读取文本
        original_text = self.read_textbook(input_file)
        if not original_text:
            logger.error("文本为空，退出处理")
            return
        
        # 分割文本
        chunks = self.split_text_into_chunks(original_text, chunk_size)
        del original_text
        
        # 恢复进度
        if progress_data and progress_data['total_chunks'] == len(chunks):
            start_index = progress_data['current_index']
            self.stats = progress_data.get('stats', self.stats)
            logger.info(f"从第 {start_index + 1} 段继续处理")
        else:
            start_index = 0
            if progress_data:
                logger.warning("进度文件与当前文本不匹配，重新开始处理")
                self.clear_progress()
        
        # 创建输出目录
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_mode = 'a' if start_index > 0 and os.path.exists(output_file) else 'w'
        total_chunks = len(chunks)
        
        try:
            with open(output_file, file_mode, encoding='utf-8') as output_f:
                for i in range(start_index, total_chunks):
                    chunk = chunks[i]
                    chunk_start_time = time.time()
                    
                    # 显示进度
                    progress_percent = ((i + 1) / total_chunks) * 100
                    elapsed_time = time.time() - self.stats['start_time']
                    
                    logger.info(f"\n{'='*60}")
                    logger.info(f"处理进度: {i+1}/{total_chunks} ({progress_percent:.1f}%)")
                    
                    if i > start_index:
                        avg_time_per_chunk = elapsed_time / (i - start_index + 1)
                        remaining_chunks = total_chunks - i - 1
                        est_remaining_time = avg_time_per_chunk * remaining_chunks
                        logger.info(f"已用时间: {self.format_time(elapsed_time)}")
                        logger.info(f"预计剩余: {self.format_time(est_remaining_time)}")
                    
                    logger.info(f"原文预览 ({len(chunk)}字): {chunk[:100]}...")
                    
                    # 第一阶段：评估是否需要精简
                    logger.info("🤔 阶段1: AI评估中...")
                    score, reason, needs_refinement = self.evaluate_chunk(chunk)
                    self.stats['evaluated_chunks'] += 1
                    
                    logger.info(f"📊 评分: {score}/10")
                    logger.info(f"💭 理由: {reason}")
                    logger.info(f"🎯 决策: {'需要精简' if needs_refinement else '保留原文'}")
                    
                    # 记录到评估日志
                    eval_logger.info(f"\n{'='*60}")
                    eval_logger.info(f"段落 {i+1}/{total_chunks}")
                    eval_logger.info(f"评分: {score}/10")
                    eval_logger.info(f"理由: {reason}")
                    eval_logger.info(f"决策: {'需要精简' if needs_refinement else '保留原文'}")
                    eval_logger.info(f"原文: {chunk[:200]}...")
                    
                    # 第二阶段：根据评估结果处理
                    if needs_refinement and score >= refinement_threshold:
                        logger.info("✂️ 阶段2: 执行精简...")
                        result = self.refine_chunk(chunk)
                        final_chunk = result['text']
                        
                        if result['success']:
                            self.stats['refined_chunks'] += 1
                            compression_rate = (1 - len(final_chunk) / len(chunk)) * 100 if len(chunk) > 0 else 0
                            logger.info(f"✅ 精简成功，压缩率: {compression_rate:.1f}%")
                            logger.info(f"精简后预览 ({len(final_chunk)}字): {final_chunk[:100]}...")
                            eval_logger.info(f"精简后: {final_chunk[:200]}...")
                        else:
                            self.stats['failed_chunks'] += 1
                            logger.warning(f"❌ 精简失败，保留原文")
                    else:
                        logger.info("✓ 保留原文，无需精简")
                        final_chunk = chunk
                        self.stats['kept_original'] += 1
                    
                    # 写入文件
                    if i > start_index or file_mode == 'w':
                        output_f.write("\n\n")
                    output_f.write(final_chunk)
                    output_f.flush()
                    
                    self.stats['final_length'] += len(final_chunk)
                    
                    # 保存进度
                    if (i + 1) % 5 == 0 or i == total_chunks - 1:
                        self.save_progress(total_chunks, i + 1)
                    
                    chunk_time = time.time() - chunk_start_time
                    logger.info(f"⏱️ 本段耗时: {chunk_time:.1f}秒")
                    
                    # 延迟避免频率限制
                    if i < total_chunks - 1:
                        time.sleep(2)
        
        except KeyboardInterrupt:
            logger.warning("\n处理被用户中断！")
            logger.info("进度已保存，下次运行时可继续")
            self.save_progress(total_chunks, i)
            return
        except Exception as e:
            logger.error(f"处理过程中出现错误: {e}")
            self.save_progress(total_chunks, i)
            raise
        
        # 清除进度文件
        self.clear_progress()
        
        # 统计信息
        total_time = time.time() - self.stats['start_time']
        original_length = self.stats['original_length']
        final_length = self.stats['final_length']
        reduction_rate = (original_length - final_length) / original_length * 100 if original_length > 0 else 0
        
        logger.info(f"\n{'='*60}")
        logger.info("🎉 智能二次精简完成！统计信息:")
        logger.info(f"{'='*60}")
        logger.info(f"⏱️ 总处理时间: {self.format_time(total_time)}")
        logger.info(f"📝 原始长度: {original_length:,} 字符")
        logger.info(f"📄 最终长度: {final_length:,} 字符")
        logger.info(f"📊 总精简率: {reduction_rate:.1f}%")
        logger.info(f"📚 总段数: {total_chunks}")
        logger.info(f"✅ 保留原文: {self.stats['kept_original']} 段 ({self.stats['kept_original']/total_chunks*100:.1f}%)")
        logger.info(f"✂️ 执行精简: {self.stats['refined_chunks']} 段 ({self.stats['refined_chunks']/total_chunks*100:.1f}%)")
        logger.info(f"❌ 处理失败: {self.stats['failed_chunks']} 段")
        logger.info(f"🔢 API调用次数: {self.stats['api_calls']}")
        logger.info(f"⏱️ 平均每段耗时: {total_time/total_chunks:.1f}秒")
        logger.info(f"\n📊 评分分布:")
        for score_key in sorted(self.stats['score_distribution'].keys()):
            count = self.stats['score_distribution'][score_key]
            percentage = count / total_chunks * 100
            logger.info(f"  {score_key}: {count} 段 ({percentage:.1f}%)")
        logger.info(f"\n💾 结果文件: {output_file}")
        logger.info(f"📋 评估日志: refiner_v3_evaluation.log")
        logger.info(f"{'='*60}")


def main():
    """
    主函数 - 配置参数并启动智能精简流程
    """
    parser = argparse.ArgumentParser(description='教材内容智能二次精简工具 v3.0')
    parser.add_argument('--input', '-i', default='refined_textbook.txt', 
                       help='输入文件路径（一次精简后的文本）')
    parser.add_argument('--output', '-o', default='refined_textbook_v2.txt', 
                       help='输出文件路径（二次精简后的文本）')
    parser.add_argument('--chunk-size', '-c', type=int, default=2000, 
                       help='每段字符数')
    parser.add_argument('--threshold', '-t', type=int, default=6, 
                       help='精简阈值（评分>=此值才精简，1-10）')
    parser.add_argument('--api-key', '-k', 
                       help='DeepSeek API密钥（也可通过环境变量DEEPSEEK_API_KEY设置）')
    parser.add_argument('--no-resume', action='store_true', 
                       help='不使用断点续传，从头开始')
    
    args = parser.parse_args()
    
    # 验证阈值
    if not 1 <= args.threshold <= 10:
        logger.error("精简阈值必须在1-10之间")
        return
    
    try:
        # 创建精简器实例
        refiner = SmartTextbookRefiner(api_key=args.api_key)
        
        # 开始智能处理
        refiner.smart_refine_textbook(
            input_file=args.input,
            output_file=args.output,
            chunk_size=args.chunk_size,
            resume=not args.no_resume,
            refinement_threshold=args.threshold
        )
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        logger.info("提示：请设置环境变量 export DEEPSEEK_API_KEY='your-api-key'")
        logger.info("或使用参数 --api-key 'your-api-key'")
    except FileNotFoundError as e:
        logger.error(f"文件错误: {e}")
    except Exception as e:
        logger.error(f"发生错误: {e}", exc_info=True)


if __name__ == "__main__":
    main()
