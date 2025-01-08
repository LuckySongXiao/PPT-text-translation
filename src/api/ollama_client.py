import requests
from typing import Optional

class OllamaClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        
    def translate(self, messages: list, model: str) -> str:
        """使用Ollama进行翻译"""
        try:
            # 将消息列表转换为单个提示词
            prompt = "\n\n".join([msg["content"] for msg in messages])
            
            response = requests.post(
                f"{self.server_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            raise Exception(f"API调用失败: HTTP {response.status_code}")
            
        except Exception as e:
            raise Exception(f"Ollama调用失败: {str(e)}") 
