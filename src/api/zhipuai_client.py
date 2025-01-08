from typing import Optional
import zhipuai

class ZhipuAIClient:
    def __init__(self, api_key: str):
        self.client = zhipuai.ZhipuAI(api_key=api_key)
        
    def translate(self, messages: list, model: str, **kwargs) -> str:
        """使用智谱AI进行翻译"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages
            )
            
            if hasattr(response, 'choices') and len(response.choices) > 0:
                return response.choices[0].message.content
            raise Exception("API返回结果异常")
            
        except Exception as e:
            raise Exception(f"智谱AI调用失败: {str(e)}") 