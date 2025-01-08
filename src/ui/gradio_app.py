import gradio as gr
from typing import Optional
import requests
from ..core.translator import Translator
from .terminology_manager_ui import TerminologyManagerUI
from pathlib import Path
import pandas as pd
import shutil
from datetime import datetime
from queue import Queue  # 添加这个导入
import os

class TranslatorUI:
    def __init__(self, translator: Translator, ppt_file_name: str = None):
        self.translator = translator
        self.ppt_file_name = ppt_file_name
        self.output_dir = "src/output"
        self.current_excel_path = None  # 初始化时设为None
        self.translation_preview = None
        self.is_processing = False
        self.excel_queue = Queue()

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_excel_file_path(self):
        if not self.ppt_file_name:  # 如果没有文件名，返回None
            return None
            
        # 获取当前日期和时间
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 构建Excel文件名称
        excel_file_name = f"{self.ppt_file_name}_{current_time}_record.xlsx"
        # 构建完整路径
        return os.path.join(self.output_dir, excel_file_name)

    def translate_ppt(self, input_file, target_lang, use_terminology, model_type, online_model, server_url, local_model):
        try:
            if self.is_processing:
                return ["正在处理其他任务，请稍后再试", "", "", []]

            self.is_processing = True
            
            if not input_file:
                return ["请选择要翻译的PPT文件", "", "", []]
                
            # 处理上传的文件
            if isinstance(input_file, dict):  # Gradio 新版本返回字典
                file_name = Path(input_file['name']).name
                temp_path = input_file['name']
            else:  # 处理其他可能的情况
                temp_path = input_file
                file_name = Path(temp_path).name
            
            # 构建输出路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(self.output_dir) / f"{Path(file_name).stem}_{timestamp}_translated.pptx"
            self.current_excel_path = Path(self.output_dir) / f"{Path(file_name).stem}_{timestamp}_record.xlsx"
            
            # 复制文件到 user_data 目录
            input_file_path = Path("user_data") / file_name
            input_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(temp_path, input_file_path)
            
            # 更新翻译器配置
            self.translator.update_config({
                "use_online": model_type == "在线模型",
                "model": online_model if model_type == "在线模型" else local_model,
                "target_language": "英文" if target_lang == "English" else "中文",
                "server_url": server_url if model_type == "本地模型" else None,
            })
            
            # 执行翻译
            result = self.translator.translate_ppt(
                str(input_file_path),
                use_terminology=use_terminology
            )
            
            # 清理用户上传的文件
            input_file_path.unlink(missing_ok=True)
            
            # 从结果中获取翻译记录
            translation_records = []
            for record in result.get("translation_records", []):
                translation_records.append({
                    "页码": record.get("slide_number", ""),
                    "位置": record.get("location", ""),
                    "格式": record.get("format", "文本框"),
                    "原文": record.get("original_text", ""),
                    "翻译结果": record.get("translated_text", ""),
                    "复检": 0
                })
            
            # 实时更新Excel文件
            if translation_records:
                df = pd.DataFrame(translation_records)
                df.to_excel(self.current_excel_path, index=False)
                self.excel_queue.put(translation_records)
            
            # 修改返回数据的格式，确保包含表头信息
            preview_data = {
                "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                "data": translation_records
            }
            
            return [
                result.get("current_location", ""),
                result.get("original_text", ""),
                result.get("translated_text", ""),
                preview_data
            ]
            
        except Exception as e:
            error_msg = f"翻译失败: {str(e)}"
            return [error_msg, "", "", {"headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"], "data": []}]
            
        finally:
            self.is_processing = False
    
    def create_ui(self):
        with gr.Blocks(title="PPT翻译工具") as ui:
            with gr.Tabs():
                with gr.Tab("翻译"):
                    gr.Markdown("## PPT文本翻译工具")
                    
                    with gr.Row():
                        input_file = gr.File(label="选择PPT文件", file_types=[".pptx", ".ppt"])
                        target_lang = gr.Dropdown(
                            choices=["English", "中文"],
                            value="English",
                            label="目标语言"
                        )
                    
                    # 添加术语使用开关
                    use_terminology = gr.Checkbox(
                        label="启用专业术语库",
                        value=False,
                        info="启用后，翻译将参考专业术语库进行更准确的翻译"
                    )
                    
                    # 翻译设置
                    with gr.Accordion("翻译设置", open=False):
                        model_type = gr.Radio(
                            choices=["在线模型", "本地模型"],
                            value="在线模型",
                            label="模型类型"
                        )
                        
                        with gr.Group() as online_group:
                            online_model = gr.Dropdown(
                                choices=["glm-4-flash", "glm-4-plus", "glm-zero-preview"],
                                value="glm-4-flash",
                                label="在线模型"
                            )
                        
                        with gr.Group() as local_group:
                            server_url = gr.Textbox(
                                value="http://localhost:11434",
                                label="Ollama服务器地址"
                            )
                            local_model = gr.Dropdown(
                                choices=self._get_local_models("http://localhost:11434"),
                                label="本地模型"
                            )
                            refresh_btn = gr.Button("刷新模型列表")
                        
                        # 添加术语库选择
                        terminology_files = gr.Dropdown(
                            choices=self.translator.terminology_manager.get_available_files(),
                            value="terminology.json",
                            label="选择术语库",
                            info="选择要使用的专业术语库文件"
                        )
                        
                        def update_terminology(file_name):
                            self.translator.terminology_manager.load(file_name)
                            return f"已加载术语库: {file_name}"
                            
                        terminology_files.change(
                            fn=update_terminology,
                            inputs=[terminology_files],
                            outputs=[gr.Textbox(label="状态")]
                        )
                    
                    # 翻译按钮和进度显示
                    with gr.Row():
                        translate_btn = gr.Button("开始翻译", variant="primary")
                    
                    # 翻译状态显示
                    with gr.Row():
                        with gr.Column():
                            current_location = gr.Textbox(
                                label="当前位置",
                                value="",
                                interactive=False
                            )
                            original_text = gr.Textbox(
                                label="原文",
                                value="",
                                interactive=False,
                                lines=3
                            )
                            translated_text = gr.Textbox(
                                label="翻译结果",
                                value="",
                                interactive=False,
                                lines=3
                            )
                    
                    # 修改复检部分的UI
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 翻译记录与复检")
                            preview_table = gr.Dataframe(
                                headers=["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                                label="翻译记录",
                                interactive=True,
                                wrap=True,
                                col_count=(6, "fixed"),
                                datatype=["str", "str", "str", "str", "str", "number"],
                                column_widths=["10%", "15%", "10%", "25%", "25%", "15%"],
                                value=[]  # 初始化空数据
                            )
                            
                            with gr.Row():
                                select_all_btn = gr.Button("全选")
                                deselect_all_btn = gr.Button("取消全选")
                                recheck_btn = gr.Button("复检选中内容", variant="primary")
                                
                            with gr.Row():
                                manual_edit = gr.Textbox(
                                    label="手动编辑翻译结果",
                                    lines=3,
                                    interactive=True
                                )
                                apply_edit_btn = gr.Button("应用修改")
                                
                            recheck_status = gr.Textbox(
                                label="操作状态",
                                value="",
                                interactive=False
                            )

                    # 修改事件处理函数
                    def select_all(data):
                        if not isinstance(data, list) or not data:
                            return {"headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"], "data": []}
                        return {
                            "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                            "data": [[*row[:-1], 1] for row in data]
                        }
                            
                    def deselect_all(data):
                        if not isinstance(data, list) or not data:
                            return {"headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"], "data": []}
                        return {
                            "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                            "data": [[*row[:-1], 0] for row in data]
                        }
                            
                    def recheck_selected(data):
                        """重新翻译选中的内容"""
                        try:
                            if not isinstance(data, list) or not data:
                                return {
                                    "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                                    "data": []
                                }, "没有可用的翻译记录"

                            # 转换数据为DataFrame
                            df = pd.DataFrame(data, columns=["页码", "位置", "格式", "原文", "翻译结果", "复检"])
                            
                            # 确保复检列的值为数值类型
                            df['复检'] = pd.to_numeric(df['复检'], errors='coerce').fillna(0)
                            
                            # 获取选中的行（复检值为1的行）
                            selected_rows = df[df["复检"] == 1]
                            
                            if selected_rows.empty:
                                return {
                                    "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                                    "data": df.values.tolist()
                                }, "请选择需要复检的内容"

                            # 对选中的内容进行重新翻译
                            updated_count = 0
                            for idx in selected_rows.index:
                                try:
                                    # 获取原文
                                    original_text = df.at[idx, "原文"]
                                    if not original_text.strip():
                                        continue
                                        
                                    # 重新翻译
                                    new_translation = self.translator.translate_text_with_verification(
                                        original_text,
                                        use_terminology=True
                                    )
                                    
                                    if new_translation and new_translation.strip():
                                        # 更新翻译结果
                                        df.at[idx, "翻译结果"] = new_translation
                                        df.at[idx, "复检"] = 0  # 复检完成后重置选择状态
                                        updated_count += 1
                                    
                                except Exception as e:
                                    print(f"复检失败 - 位置: {df.at[idx, '位置']}, 错误: {str(e)}")
                                    continue

                            # 如果有Excel文件，同步更新
                            if hasattr(self, 'current_excel_path') and self.current_excel_path:
                                df.to_excel(self.current_excel_path, index=False)

                            return {
                                "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                                "data": df.values.tolist()
                            }, f"已完成 {updated_count} 项内容的复检"

                        except Exception as e:
                            print(f"复检过程出错: {str(e)}")
                            return {
                                "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                                "data": data
                            }, f"复检过程出错: {str(e)}"
                            
                    def apply_manual_edit(data, edit_text):
                        if not isinstance(data, list) or not data:
                            return (
                                {"headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"], "data": []},
                                "请先选择要编辑的内容"
                            )
                            
                        df = pd.DataFrame(data, columns=["页码", "位置", "格式", "原文", "翻译结果", "复检"])
                        selected_rows = df[df["复检"] == 1]
                            
                        if selected_rows.empty:
                            return {"headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"], "data": []}, "请选择要编辑的行"
                            
                        # 更新选中行的翻译结果
                        df.loc[df["复检"] == 1, "翻译结果"] = edit_text
                        df.loc[df["复检"] == 1, "复检"] = 0  # 编辑后重置选择状态
                            
                        # 如果有Excel文件，同步更新
                        if hasattr(self, 'current_excel_path') and self.current_excel_path:
                            df.to_excel(self.current_excel_path, index=False)
                            
                        return {
                            "headers": ["页码", "位置", "格式", "原文", "翻译结果", "复检"],
                            "data": df.values.tolist()
                        }, f"已更新 {len(selected_rows)} 行的翻译结果"

                    # 绑定事件处理函数
                    select_all_btn.click(fn=select_all, inputs=[preview_table], outputs=[preview_table])
                    deselect_all_btn.click(fn=deselect_all, inputs=[preview_table], outputs=[preview_table])
                    recheck_btn.click(
                        fn=recheck_selected,
                        inputs=[preview_table],
                        outputs=[preview_table, recheck_status]
                    )
                    apply_edit_btn.click(
                        fn=apply_manual_edit,
                        inputs=[preview_table, manual_edit],
                        outputs=[preview_table, recheck_status]
                    )

                    # 修改翻译按钮的事件处理
                    def process_translation_result(result):
                        """处理翻译结果"""
                        location, original, translated, preview = result
                        if isinstance(preview, dict):
                            return [
                                location,
                                original,
                                translated,
                                preview.get("data", [])
                            ]
                        return result

                    translate_btn.click(
                        fn=lambda *args: process_translation_result(self.translate_ppt(*args)),
                        inputs=[
                            input_file,
                            target_lang,
                            use_terminology,
                            model_type,
                            online_model,
                            server_url,
                            local_model
                        ],
                        outputs=[
                            current_location,
                            original_text,
                            translated_text,
                            preview_table
                        ]
                    )
                    
                    refresh_btn.click(
                        fn=self._get_local_models,
                        inputs=server_url,
                        outputs=local_model
                    )
                    
                with gr.Tab("术语库管理"):
                    terminology_ui = TerminologyManagerUI(self.translator.terminology_manager)
                    terminology_ui.create_ui()
            
        return ui
    
    def _get_local_models(self, server_url: str) -> list:
        """获取本地可用的模型列表"""
        try:
            response = requests.get(f"{server_url.rstrip('/')}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return []
        except Exception as e:
            print(f"获取本地模型列表失败: {str(e)}")
            return [] 

    def recheck_selected_translations(self, data) -> tuple:
        """复检选中的翻译内容"""
        try:
            if self.is_processing:
                return data, "正在处理其他任务，请稍后再试"

            self.is_processing = True
            
            if not isinstance(data, list) or not data:
                return data, "没有可用的翻译记录"

            # 转换数据为DataFrame
            df = pd.DataFrame(data, columns=["页码", "位置", "格式", "原文", "翻译结果", "选择"])
            
            # 获取选中的行
            selected_rows = df[df["选择"] == True]
            if selected_rows.empty:
                return data, "请选择需要复检的内容"

            # 对选中的内容进行重新翻译和复检
            updated_count = 0
            for idx, row in selected_rows.iterrows():
                try:
                    # 重新翻译和复检
                    new_translation = self.translator.translate_text_with_verification(
                        row["原文"],
                        use_terminology=True  # 启用术语库
                    )
                    
                    # 更新翻译结果
                    df.at[idx, "翻译结果"] = new_translation
                    df.at[idx, "选择"] = False  # 重置选择状态
                    updated_count += 1
                    
                except Exception as e:
                    print(f"复检失败 - 位置: {row['位置']}, 错误: {str(e)}")
                    continue

            # 如果有更新的Excel文件，更新它
            if hasattr(self, 'current_excel_path') and self.current_excel_path:
                df.to_excel(self.current_excel_path, index=False)

            return df.values.tolist(), f"已完成 {updated_count} 项内容的复检"

        except Exception as e:
            return data, f"复检过程出错: {str(e)}"
            
        finally:
            self.is_processing = False 

    def _excel_writer_thread(self, excel_path: Path):
        """Excel写入线程"""
        records = []
        while True:
            batch = self.excel_queue.get()
            if batch is None:  # 结束信号
                break
            records.extend(batch)
            self.excel_queue.task_done()
        
        # 创建DataFrame时确保列名唯一
        columns = ["页码", "位置", "格式", "原文", "翻译结果", "复检"]
        df = pd.DataFrame(records, columns=columns)
        
        # 确保列名唯一性
        df = df.loc[:, ~df.columns.duplicated()]
        
        # 保存到Excel
        df.to_excel(excel_path, index=False)
        self.excel_queue.task_done() 

    def update_translation_preview(self):
        # 检查Excel文件是否存在
        if not os.path.exists(self.current_excel_path):
            # 如果文件不存在，返回空数据
            return []

        # 读取Excel文件中的内容
        df = pd.read_excel(self.current_excel_path)

        # 将DataFrame转换为Gradio Dataframe的格式
        data = df.to_dict(orient='records')

        return data 
