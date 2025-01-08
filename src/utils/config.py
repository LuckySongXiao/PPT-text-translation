from typing import Dict, Any
import json
from pathlib import Path

class Config:
    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self.load()
        
    def load(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                # 创建默认配置
                default_config = {
                    "api_key": "Please enter your API key",
                    "target_language": "英文",
                    "model": "glm-4-flash",
                    "model_config": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 2000
                    },
                    "use_online": True,
                    "server_url": "http://localhost:11434",
                    "api_type": "zhipuai"
                }
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            raise Exception(f"加载配置文件失败: {str(e)}") 
