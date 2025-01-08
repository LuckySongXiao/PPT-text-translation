from typing import Dict, Optional, List
import json
from pathlib import Path

class TerminologyManager:
    def __init__(self, file_path: Optional[str] = None):
        self.json_dir = Path("src/json")  # 术语库目录
        self.file_path = Path(file_path or self.json_dir / "terminology.json")
        self.terminology: Dict[str, str] = self.load()
        
    def get_available_files(self) -> List[str]:
        """获取可用的术语库文件列表"""
        try:
            return [f.name for f in self.json_dir.glob("*.json")]
        except Exception as e:
            print(f"获取术语库文件列表失败: {str(e)}")
            return []
            
    def load(self, file_name: Optional[str] = None) -> Dict[str, str]:
        """加载术语库"""
        try:
            if file_name:
                self.file_path = self.json_dir / file_name
                
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 处理新的术语库格式
                    if "中文" in data and "英语" in data["中文"]:
                        return data["中文"]["英语"]
                    return data if isinstance(data, dict) else {}
            return {}
        except Exception as e:
            print(f"加载术语库失败: {str(e)}")
            return {}
    
    def save(self):
        """保存术语库"""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.terminology, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存术语库失败: {str(e)}")
    
    def apply_terminology(self, text: str) -> str:
        """应用术语库进行精确替换"""
        # 按照术语长度降序排序，确保优先替换较长的术语
        sorted_terms = sorted(self.terminology.items(), key=lambda x: len(x[0]), reverse=True)
        
        # 使用分词方式进行精确替换
        words = text.split()
        result = []
        
        for word in words:
            replaced = False
            for cn, en in sorted_terms:
                if word == cn:  # 精确匹配
                    result.append(en)
                    replaced = True
                    break
            if not replaced:
                result.append(word)
        
        return ' '.join(result) 