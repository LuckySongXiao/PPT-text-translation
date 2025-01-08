import gradio as gr
import pandas as pd
from typing import Dict, List, Tuple
from ..core.terminology import TerminologyManager
import json

class TerminologyManagerUI:
    def __init__(self, terminology_manager: TerminologyManager):
        self.terminology_manager = terminology_manager
        
    def create_ui(self) -> gr.Blocks:
        with gr.Blocks() as ui:
            gr.Markdown("## 专业术语库管理")
            
            # 术语库预览
            with gr.Row():
                terminology_table = gr.Dataframe(
                    headers=["中文", "英文"],
                    value=self._get_terminology_list(),
                    label="当前术语库",
                    interactive=False
                )
            
            # 添加新术语
            with gr.Row():
                with gr.Column():
                    cn_term = gr.Textbox(label="中文术语")
                    en_term = gr.Textbox(label="英文术语")
                    add_btn = gr.Button("添加术语", variant="primary")
            
            # 导入导出
            with gr.Row():
                with gr.Column():
                    import_file = gr.File(
                        label="导入术语库文件",
                        file_types=[".json", ".xlsx", ".csv"]
                    )
                    import_btn = gr.Button("导入")
                
                with gr.Column():
                    export_btn = gr.Button("导出术语库")
                    export_path = gr.Textbox(
                        label="导出路径",
                        interactive=False
                    )
            
            # 搜索和删除
            with gr.Row():
                search_term = gr.Textbox(
                    label="搜索术语",
                    placeholder="输入中文或英文术语"
                )
            
            with gr.Row():
                filtered_table = gr.Dataframe(
                    headers=["中文", "英文"],
                    label="搜索结果",
                    interactive=True,
                    value=[]
                )
            
            with gr.Row():
                delete_btn = gr.Button("删除选中术语", variant="stop")
                clear_btn = gr.Button("清空术语库", variant="stop")
            
            # 绑定事件
            def add_term(cn: str, en: str) -> Tuple[List[List[str]], str, str]:
                """添加新术语"""
                if not cn or not en:
                    return self._get_terminology_list(), cn, en
                
                self.terminology_manager.add_term(cn, en)
                return self._get_terminology_list(), "", ""
            
            def import_terminology(file) -> List[List[str]]:
                """导入术语库"""
                if file:
                    try:
                        count = self.terminology_manager.import_terminology(file.name)
                        gr.Info(f"成功导入 {count} 个术语")
                        return self._get_terminology_list()
                    except Exception as e:
                        gr.Error(f"导入失败: {str(e)}")
                return self._get_terminology_list()
            
            def export_terminology() -> str:
                """导出术语库"""
                try:
                    path = self.terminology_manager.export_terminology()
                    return path
                except Exception as e:
                    gr.Error(f"导出失败: {str(e)}")
                    return ""
            
            def search_terminology(term: str) -> List[List[str]]:
                """搜索术语"""
                if not term:
                    return []
                    
                results = []
                for cn, en in self.terminology_manager.terminology.items():
                    if term.lower() in cn.lower() or term.lower() in en.lower():
                        results.append([cn, en])
                return results
            
            def delete_terms(selected_data: pd.DataFrame) -> List[List[str]]:
                """删除选中的术语"""
                if not selected_data:
                    return self._get_terminology_list()
                
                for _, row in selected_data.iterrows():
                    cn = row[0]
                    if cn in self.terminology_manager.terminology:
                        del self.terminology_manager.terminology[cn]
                
                self.terminology_manager.save()
                return self._get_terminology_list()
            
            def clear_terminology() -> List[List[str]]:
                """清空术语库"""
                self.terminology_manager.clear_terminology()
                return []
            
            # 绑定事件处理函数
            add_btn.click(
                fn=add_term,
                inputs=[cn_term, en_term],
                outputs=[terminology_table, cn_term, en_term]
            )
            
            import_btn.click(
                fn=import_terminology,
                inputs=import_file,
                outputs=terminology_table
            )
            
            export_btn.click(
                fn=export_terminology,
                outputs=export_path
            )
            
            search_term.change(
                fn=search_terminology,
                inputs=search_term,
                outputs=filtered_table
            )
            
            delete_btn.click(
                fn=delete_terms,
                inputs=filtered_table,
                outputs=terminology_table
            )
            
            clear_btn.click(
                fn=clear_terminology,
                outputs=terminology_table
            )
            
        return ui
    
    def _get_terminology_list(self) -> List[List[str]]:
        """获取术语库列表"""
        return [[cn, en] for cn, en in self.terminology_manager.terminology.items()] 