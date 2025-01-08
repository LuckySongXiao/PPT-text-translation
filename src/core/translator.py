from typing import Optional, Dict, Any, List
from pathlib import Path
import pandas as pd
import threading
from queue import Queue
from pptx import Presentation
from pptx.dml.color import RGBColor
import shutil
from datetime import datetime
import os
from .terminology import TerminologyManager
from .prompt_manager import PromptManager
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pptx.util import Pt
import re
from langdetect import detect

class Translator:
    def __init__(self, config):
        self.config = config
        self.terminology_manager = TerminologyManager()
        self.prompt_manager = PromptManager()
        self.progress_callback = None
        self.status_callback = None
        self.excel_queue = Queue()
        self.translation_lock = threading.Lock()
        self.max_retries = 3  # 最大重试次数
        self.executor = ThreadPoolExecutor(max_workers=3)  # 设置线程池大小
        self.init_client()
        
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置并重新初始化客户端"""
        try:
            # 更新配置
            self.config.config.update(new_config)
            
            # 重新初始化客户端
            self.init_client()
        except Exception as e:
            print(f"更新配置失败: {str(e)}")
            raise

    def init_client(self):
        """初始化翻译客户端"""
        try:
            if self.config.config.get("use_online", True):
                from ..api.zhipuai_client import ZhipuAIClient
                self.client = ZhipuAIClient(self.config.config["api_key"])
            else:
                from ..api.ollama_client import OllamaClient
                self.client = OllamaClient(self.config.config["server_url"])
        except Exception as e:
            print(f"初始化翻译客户端失败: {str(e)}")
            raise

    def translate_ppt(self, input_path: str, use_terminology: bool = False) -> Dict[str, Any]:
        try:
            # 获取文件名和时间戳
            file_name = Path(input_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建输出文件路径
            output_dir = Path("src/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / f"{file_name}_{timestamp}_translated.pptx"
            excel_path = output_dir / f"{file_name}_{timestamp}_record.xlsx"
            
            # 启动Excel写入线程
            self.excel_thread = threading.Thread(
                target=self._excel_writer_thread,
                args=(excel_path,),
                daemon=True
            )
            self.excel_thread.start()
            
            # 加载PPT
            prs = Presentation(input_path)
            total_slides = len(prs.slides)
            
            # 计算总任务数
            total_tasks = self._calculate_total_tasks(prs)
            completed_tasks = 0
            
            # 创建进度追踪变量
            current_progress = {
                "slide": 0,
                "shape": 0,
                "text": "",
                "translation": ""
            }
            
            # 处理每一页
            for slide_idx, slide in enumerate(prs.slides, 1):
                current_progress["slide"] = slide_idx
                
                for shape_idx, shape in enumerate(slide.shapes, 1):
                    current_progress["shape"] = shape_idx
                    
                    # 处理形状并等待完成
                    result = self._process_shape_with_progress(
                        shape, 
                        slide_idx, 
                        use_terminology,
                        current_progress
                    )
                    
                    if result:
                        # 更新进度信息
                        self._update_progress(current_progress)
                        
                        # 保存当前进度
                        try:
                            prs.save(output_path)
                        except Exception as e:
                            print(f"保存进度时出错: {str(e)}")
            
            # 等待所有Excel写入任务完成
            self.excel_queue.put(None)  # 发送结束信号
            self.excel_queue.join()
            self.excel_thread.join()
            
            # 完成翻译后显示复检完成消息
            final_status = {
                "current_location": "翻译和复检已完成",
                "original_text": "",
                "translated_text": "请查收翻译结果文件",
                "preview_data": pd.read_excel(excel_path).values.tolist(),
                "output_file": str(output_path)
            }
            
            if self.status_callback:
                self.status_callback(final_status)
                
            return final_status
            
        except Exception as e:
            raise Exception(f"PPT翻译失败: {str(e)}")
    
    def _calculate_total_tasks(self, prs) -> int:
        """计算总任务数"""
        total = 0
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_table:
                    table = shape.table
                    total += len(table.rows) * len(table.columns)
                if hasattr(shape, "text_frame"):
                    total += 1
        return total
    
    def _process_shape_with_progress(self, shape, slide_idx: int, use_terminology: bool, progress: dict) -> bool:
        """处理单个形状并更新进度"""
        try:
            texts_to_translate = []
            text_locations = []

            # 收集需要翻译的文本
            if shape.has_table:
                for row_idx, row in enumerate(shape.table.rows):
                    for col_idx, cell in enumerate(row.cells):
                        if cell.text.strip():
                            location = f"Slide{slide_idx}-Table-Row{row_idx+1}-Column{col_idx+1}"
                            texts_to_translate.append(cell.text.strip())
                            text_locations.append((cell.text_frame, location, shape))

            elif hasattr(shape, "text_frame") and shape.text_frame.text.strip():
                location = f"Slide{slide_idx}-TextBox"
                texts_to_translate.append(shape.text_frame.text.strip())
                text_locations.append((shape.text_frame, location, shape))

            # 批量翻译文本
            if texts_to_translate:
                translations = self.batch_translate_texts(texts_to_translate, use_terminology)

                # 更新文本框
                for (text_frame, location, shape), translated_text in zip(text_locations, translations):
                    self._update_text_frame_with_translation(
                        text_frame, location, shape, translated_text, progress
                    )

            # 处理组合形状
            if hasattr(shape, "group_items"):
                for item in shape.group_items:
                    self._process_shape_with_progress(item, slide_idx, use_terminology, progress)

            return True

        except Exception as e:
            print(f"处理形状时出错: {str(e)}")
            return False

    def _update_text_frame_with_translation(self, text_frame, location: str, shape, translated_text: str, progress: dict):
        """更新文本框内容并记录翻译结果"""
        try:
            original_text = text_frame.text.strip()
            progress["text"] = original_text
            progress["translation"] = translated_text

            # 更新文本框
            self._adjust_text_frame(text_frame, translated_text)

            # 添加到Excel队列
            self.excel_queue.put([{
                "页码": location.split("-")[0].replace("幻灯片", ""),
                "位置": location,
                "格式": "文本框" if not hasattr(shape, "table") else "表格",
                "原文": original_text,
                "翻译结果": translated_text
            }])

        except Exception as e:
            print(f"更新文本框时出错: {str(e)}")
    
    def _update_progress(self, progress: dict):
        """更新进度信息到UI"""
        if self.status_callback:
            status = {
                "current_location": f"幻灯片 {progress['slide']} - 形状 {progress['shape']}",
                "original_text": progress["text"],
                "translated_text": progress["translation"]
            }
            self.status_callback(status)
    
    def _process_and_translate_text(self, text: str, location: str, use_terminology: bool) -> Dict[str, str]:
        """处理和翻译文本"""
        # 如果文本只包含数字或英文字母，直接返回原文
        if not self._is_translatable(text):
            return {
                "location": location,
                "original": text,
                "first_translation": text,
                "verified_translation": text,
                "final_translation": text
            }
        
        # 应用术语库（如果启用）
        if use_terminology:
            text = self.terminology_manager.apply_terminology(text)
        
        # 进行翻译
        first_translation = self.translate_text(text)
        verified_translation = self.translate_text(first_translation)  # 复检翻译
        
        return {
            "location": location,
            "original": text,
            "first_translation": first_translation,
            "verified_translation": verified_translation,
            "final_translation": verified_translation
        }
    
    def _excel_writer_thread(self, excel_path: Path):
        """Excel写入线程"""
        records = []
        while True:
            batch = self.excel_queue.get()
            if batch is None:  # 结束信号
                break
            records.extend(batch)
            self.excel_queue.task_done()
        
        # 创建DataFrame并保存
        df = pd.DataFrame(records, columns=[
            "页码", "位置", "格式", "原文", "翻译结果"
        ])
        df.to_excel(excel_path, index=False)
        self.excel_queue.task_done()
    
    def _is_translatable(self, text: str) -> bool:
        """检查文本是否需要翻译"""
        # 如果文本是纯数字或英文编号，则不需要翻译
        if text.strip().isdigit():  # 纯数字
            return False
        
        # 检查是否为英文编号格式（如 A01, B-02 等）
        if re.match(r'^[A-Za-z0-9\-_.]+$', text.strip()):
            return False
        
        # 如果目标是英文，检查是否包含中文字符
        if self.config.config["target_language"] == "英文":
            return self.prompt_manager.has_chinese(text)
        
        # 如果目标是中文，检查是否包含英文字符
        return bool(re.search(r'[a-zA-Z]', text))
    
    def _adjust_text_frame(self, text_frame, new_text: str):
        """调整文本框内容，保持原有格式"""
        try:
            # 更新文本
            text_frame.text = new_text
            
            # 遍历所有段落和文字块，统一设置格式
            for paragraph in text_frame.paragraphs:
                for run in paragraph.runs:
                    # 设置字体大小为7.0磅
                    if run.font.size and run.font.size.pt > 7.0:
                        run.font.size = Pt(7.0)
                    # 如果未设置字体大小，则设置为7.0磅
                    elif not run.font.size:
                        run.font.size = Pt(7.0)
                        
                    # 统一设置字体颜色为黑色
                    run.font.color.rgb = RGBColor(0, 0, 0)
                    
        except Exception as e:
            print(f"调整文本框格式时出错: {str(e)}")

    def translate_text(self, text: str, use_terminology: bool = False) -> str:
        """翻译文本"""
        try:
            if not text.strip():
                return text
            
            # 如果文本只包含数字或英文字母，直接返回原文
            if not self._is_translatable(text):
                return text
            
            # 应用术语库（如果启用）
            if use_terminology:
                text = self.terminology_manager.apply_terminology(text)
            
            # 获取翻译提示词
            messages = self.prompt_manager.format_translation_request(
                text=text,
                source_lang="中文" if self.config.config["target_language"] == "英文" else "英文",
                target_lang=self.config.config["target_language"],
                context="ppt"
            )
            
            # 使用客户端进行翻译
            return self.client.translate(messages, self.config.config["model"])
            
        except Exception as e:
            print(f"翻译文本失败: {str(e)}")
            return text

    def translate_text_with_retry(self, text: str, use_terminology: bool = False) -> str:
        """带重试机制的文本翻译"""
        if not text.strip() or not self._is_translatable(text):
            return text
        
        translations = []  # 存储多次翻译结果
        retry_count = 0
        max_retries = 3
        
        # 进行多次翻译尝试
        while retry_count < max_retries and len(translations) < 3:
            try:
                # 使用不同的提示词变体
                messages = self.prompt_manager.get_variant_prompt(text, retry_count)
                translated = self.client.translate(messages, self.config.config["model"])
                
                # 验证翻译结果
                if translated and translated.strip():
                    if self.config.config["target_language"] == "英文":
                        # 对于英文翻译，确保没有中文
                        if not self.prompt_manager.has_chinese(translated):
                            translations.append(translated)
                    else:
                        # 对于其他语言的翻译，直接添加
                        translations.append(translated)
                
                retry_count += 1
                time.sleep(1)  # 添加短暂延迟避免请求过快
                
            except Exception as e:
                print(f"翻译重试 {retry_count + 1} 失败: {str(e)}")
                retry_count += 1
                time.sleep(2)
        
        # 如果有任何有效的翻译结果，进行选择
        if translations:
            # 使用复检提示词评估翻译质量
            best_translation = self._select_best_translation(text, translations)
            return best_translation
            
        return text  # 如果所有尝试都失败，返回原文

    def _select_best_translation(self, original_text: str, translations: list) -> str:
        """选择最佳翻译结果"""
        try:
            # 如果只有一个翻译结果，直接返回
            if len(translations) == 1:
                return translations[0]
            
            # 如果有两个或更多翻译结果，构建评估提示词
            evaluation_prompt = f"""Please evaluate the quality of the following translation versions and select the most accurate and fluent one.
Original text: {original_text}

"""
            # 动态添加翻译版本
            for i, trans in enumerate(translations, 1):
                evaluation_prompt += f"Version {i}: {trans}\n"
            
            evaluation_prompt += "\nPlease return the best translation directly without any explanation."

            messages = [
                {"role": "system", "content": "You are a professional translation evaluator. Please select the best translation version."},
                {"role": "user", "content": evaluation_prompt}
            ]
            
            # 获取评估结果
            best_translation = self.client.translate(messages, self.config.config["model"])
            
            # 如果评估结果不在translations中，返回最后一个翻译
            if best_translation not in translations:
                return translations[-1]
            
            return best_translation
            
        except Exception as e:
            print(f"选择最佳翻译失败: {str(e)}")
            # 出错时返回最后一个翻译结果（通常是最好的一次）
            return translations[-1] if translations else original_text

    def translate_text_with_verification(self, text: str, use_terminology: bool = False) -> str:
        """带三重验证的文本翻译"""
        if not text.strip() or not self._is_translatable(text):
            return text

        try:
            # 第一次翻译
            first_translation = self.translate_text_with_retry(text, use_terminology)

            # 检查翻译结果是否属于目标语种
            if not self.is_target_language(first_translation):
                # 如果不属于目标语种，重新翻译
                first_translation = self.translate_text_with_retry(text, use_terminology)

            # 第二次翻译(反向验证)
            verification_prompt = f"""Please verify if the following translation is accurate:
Original text: {text}
Translation: {first_translation}

Please return only the corrected translation without any other content. If the translation is accurate, return it as is."""
            
            second_translation = self.client.translate([
                {"role": "system", "content": "You are a professional translation reviewer."},
                {"role": "user", "content": verification_prompt}
            ], self.config.config["model"])

            # 检查翻译结果是否属于目标语种
            if not self.is_target_language(second_translation):
                # 如果不属于目标语种，重新翻译
                second_translation = self.client.translate([
                    {"role": "system", "content": "You are a professional translation reviewer."},
                    {"role": "user", "content": verification_prompt}
                ], self.config.config["model"])

            # 第三次翻译(最终确认)
            final_prompt = f"""Please make a final confirmation of the following translation:
Original text: {text}
First translation: {first_translation}
Second translation: {second_translation}

Please return only the final confirmed translation without any other content. If both translations are accurate, choose and return the more accurate one."""
            
            final_translation = self.client.translate([
                {"role": "system", "content": "You are a senior translation expert."},
                {"role": "user", "content": final_prompt}
            ], self.config.config["model"])

            # 检查翻译结果是否属于目标语种
            if not self.is_target_language(final_translation):
                # 如果不属于目标语种，重新翻译
                final_translation = self.client.translate([
                    {"role": "system", "content": "You are a senior translation expert."},
                    {"role": "user", "content": final_prompt}
                ], self.config.config["model"])

            # 确保最终结果不包含中文
            final_translation = self.prompt_manager.remove_chinese(final_translation)

            # 检查翻译结果是否为空或仅包含标点符号
            if not final_translation.strip() or final_translation.strip().isalnum():
                # 如果翻译结果为空或仅包含标点符号，返回原文
                return text

            return final_translation

        except Exception as e:
            print(f"翻译验证失败: {str(e)}")
            return text

    def is_target_language(self, text: str) -> bool:
        """检查文本是否属于目标语种"""
        # 这里可以使用语言检测库，如langdetect，来检测文本的语言
        # 以下是一个简单的示例，假设目标语种为英文
        try:
            detected_language = detect(text)
            return detected_language == 'en'
        except:
            return False

    def batch_translate_texts(self, texts: List[str], use_terminology: bool = False) -> List[str]:
        """批量翻译文本（包含复检）"""
        futures = []
        results = [""] * len(texts)

        # 提交所有翻译任务到线程池
        for i, text in enumerate(texts):
            future = self.executor.submit(
                self.translate_text_with_verification, 
                text, 
                use_terminology
            )
            futures.append((i, future))

        # 按顺序获取结果
        for i, future in futures:
            try:
                results[i] = future.result()
            except Exception as e:
                print(f"翻译任务 {i} 失败: {str(e)}")
                results[i] = texts[i]

        return results
