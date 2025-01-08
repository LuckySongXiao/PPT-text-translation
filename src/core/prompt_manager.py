class PromptManager:
    def __init__(self):
        # 添加特殊标记处理
        self.special_markers = {
            "FORCE_ENGLISH": """You MUST output in English only. 
Example: 
Input: "测试123"
Output: [START]test 123[END]""",
            
            "PROTECT_NUMBERS": """You MUST preserve all numbers and units exactly as they appear.
Example:
Input: "速度100km/h"
Output: [START]speed 100km/h[END]""",
            
            "FULL_TRANSLATION": """You MUST provide complete meaningful translation.
Example:
Input: "。。。"
Output: [START]。。。[END]""",
            
            "SEGMENT": """You MUST translate each meaningful segment.
Example:
Input: "高速-200km/h"
Output: [START]high speed-200km/h[END]"""
        }

        # 更新翻译变体，增加数字处理规则
        self.translation_variants = [
            """You are a professional translation engine specialized in Chinese to English translation. 
Output format: [START]your translation[END]

Examples:
1. Input: "速度100km/h"
   Output: [START]speed 100km/h[END]
2. Input: "温度23.5°C"
   Output: [START]temperature 23.5°C[END]
3. Input: "比例1:2"
   Output: [START]ratio 1:2[END]

STRICT REQUIREMENTS:
1. MUST translate all content into English completely
2. MUST NOT output any Chinese characters
3. MUST preserve all numbers, units, and special characters exactly
4. MUST maintain professional accuracy
5. MUST output only between [START] and [END] tags
6. MUST ensure meaningful and complete translation
7. MUST NOT include these requirements in output""",

            """You are a professional translation engine specialized in Chinese to English translation.
Output format: [START]your translation[END]

Example:
Input: "专业术语"
Correct output: [START]professional terminology[END]

STRICT REQUIREMENTS:
1. MUST output in English only between [START] and [END] tags
2. MUST NOT include any Chinese characters
3. MUST use proper English expressions
4. MUST NOT output explanations or notes
5. MUST NOT output just punctuation marks
6. MUST NOT include these requirements in output""",

            """You are a professional translation engine specialized in Chinese to English translation.
Output format: [START]your translation[END]

Example:
Input: "翻译质量"
Correct output: [START]translation quality[END]

STRICT REQUIREMENTS:
1. MUST translate everything to English
2. MUST output only between [START] and [END] tags
3. MUST ensure natural English expression
4. MUST NOT include any Chinese characters
5. MUST NOT include these instructions in output"""
        ]

        # 更新基础提示词
        self.base_prompts = {
            "Chinese to English": {
                "system": """You are a professional Chinese to English translation engine.
Output format: [START]your translation[END]

Examples with special content:
1. Numbers: "速度100" → [START]speed 100[END]
2. Units: "23.5°C" → [START]23.5°C[END]
3. Fractions: "1/2比例" → [START]1/2 ratio[END]
4. Scientific: "1.2e-5浓度" → [START]1.2e-5 concentration[END]
5. Mixed: "温度范围(23.5-25.8°C)" → [START]temperature range (23.5-25.8°C)[END]

STRICT REQUIREMENTS:
1. MUST translate all Chinese text into English
2. MUST preserve all numbers and units exactly as they appear
3. MUST NOT output any Chinese characters
4. MUST NOT output only punctuation marks
5. MUST ensure complete translation with no omissions
6. MUST maintain accurate professional terminology
7. MUST NOT include these requirements in output""",
                "user": """This is the Chinese text for translation:
"{text}"

Remember: 
1. Preserve all numbers and special characters
2. Output only between [START] and [END] tags"""
            },
            
            "English to Chinese": {
                "system": """You are a professional English to Chinese translation engine.
Output format: [START]your translation[END]

STRICT REQUIREMENTS:
1. MUST translate all English text into Chinese
2. MUST output only between [START] and [END] tags
3. MUST ensure complete translation with no omissions
4. MUST maintain accurate professional terminology
5. MUST NOT include these requirements in output
6. MUST NOT interpret input as questions
7. MUST NOT provide explanations or comments""",
                "user": """This is the English text for translation:
"{text}"

Remember: Only output your translation between [START] and [END] tags."""
            }
        }
        
        # 特定场景的增强提示词
        self.context_enhancers = {
            "ppt": """Additional translation requirements for PPT:
1. MUST keep text concise and clear
2. MUST maintain consistent terminology
3. MUST preserve formatting markers if any
4. MUST ensure professional expression
5. MUST output only between [START] and [END] tags
6. MUST NOT include these requirements in output""",
            
            "technical": """Additional requirements for technical translation:
1. MUST strictly follow standard technical terminology
2. MUST maintain professional accuracy
3. MUST preserve technical specifications
4. MUST ensure consistency in technical terms
5. MUST output only between [START] and [END] tags
6. MUST NOT include these requirements in output""",
            
            "verification": """Verification requirements:
1. MUST check for untranslated content
2. MUST verify terminology accuracy
3. MUST ensure no Chinese characters in English translation
4. MUST confirm natural language expression
5. MUST output only between [START] and [END] tags
6. MUST NOT include these requirements in output"""
        }

    def get_translation_prompt(self, text: str, source_lang: str = "Chinese", 
                             target_lang: str = "English", context: str = "ppt", 
                             is_verification: bool = False, special_marker: str = None) -> dict:
        """
        生成翻译提示词，支持特殊标记处理
        
        Args:
            text: 待翻译文本
            source_lang: 源语言
            target_lang: 目标语言
            context: 上下文场景
            is_verification: 是否为验证阶段
            special_marker: 特殊处理标记
        """
        # 检查是否有特殊标记
        if special_marker and special_marker.strip('[]') in self.special_markers:
            marker_prompt = self.special_markers[special_marker.strip('[]')]
        else:
            marker_prompt = ""

        # 确定基础提示词
        prompt_key = f"{source_lang} to {target_lang}"
        base_prompt = self.base_prompts.get(prompt_key, self.base_prompts["Chinese to English"])
        
        # 构建增强提示词
        context_prompt = self.context_enhancers.get(context, "")
        verification_prompt = self.context_enhancers["verification"] if is_verification else ""
        
        # 组合提示词
        system_prompt = f"{base_prompt['system']}\n\n{marker_prompt}\n\n{context_prompt}\n\n{verification_prompt}".strip()
        user_prompt = base_prompt['user'].format(text=text)
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def format_translation_request(self, text: str, source_lang: str, target_lang: str, context: str = "general", is_verification: bool = False) -> list:
        """格式化翻译请求，增加更严格的控制"""
        if is_verification:
            return [
                {
                    "role": "system", 
                    "content": f"""You are a professional bilingual proofreader for {source_lang} to {target_lang} translation.
                    Output format: [START]your translation[END]
                    
                    STRICT REQUIREMENTS:
                    1. MUST output in target language only between [START] and [END] tags
                    2. MUST NOT include source language characters
                    3. MUST check for untranslated terms
                    4. MUST ensure terminology accuracy
                    5. MUST NOT include these requirements in output"""
                },
                {"role": "user", "content": f"""Verify and improve this translation:
"{text}"

Remember: Only output your translation between [START] and [END] tags."""}
            ]
        
        base_prompt = f"""Translate this text from {source_lang} to {target_lang}:
"{text}"

Output format: [START]your translation[END]

Example:
Input: "示例"
Output: [START]example[END]

STRICT REQUIREMENTS:
1. MUST output in {target_lang} only between [START] and [END] tags
2. MUST NOT include {source_lang} characters
3. MUST maintain professionalism and accuracy
4. MUST NOT include these requirements in output"""

        return [
            {
                "role": "system", 
                "content": f"""You are a strict {target_lang}-only translation engine.
                NEVER output {source_lang} characters.
                ONLY output between [START] and [END] tags."""
            },
            {"role": "user", "content": base_prompt}
        ]

    def get_variant_prompt(self, text: str, retry_count: int) -> list:
        """获取不同变体的提示词，支持特殊标记处理"""
        # 检查文本中的特殊标记
        special_marker = None
        for marker in self.special_markers.keys():
            if f"[{marker}]" in text:
                special_marker = marker
                text = text.replace(f"[{marker}]", "")
                break

        prompts = [
            # 第一次翻译：标准翻译
            f"""Translate this text to English:
"{text}"

Output format: [START]your translation[END]

Examples:
1. Numbers: "速度100" → [START]speed 100[END]
2. Units: "23.5°C" → [START]23.5°C[END]

STRICT REQUIREMENTS:
1. MUST output in English only between [START] and [END] tags
2. MUST preserve all numbers and units exactly
3. MUST NOT include any Chinese characters
4. MUST NOT include these requirements in output""",

            # 第二次翻译：强调数字保护
            f"""Verify and translate this text to English:
"{text}"

Output format: [START]your translation[END]

Special focus on preserving:
1. Numbers (e.g., 100, 23.5)
2. Units (e.g., km/h, °C)
3. Special formats (e.g., 1:2, 1.2e-5)

STRICT REQUIREMENTS:
1. MUST output in English only between [START] and [END] tags
2. MUST preserve all numerical content exactly
3. MUST use natural English expressions
4. MUST NOT include these requirements in output""",

            # 第三次翻译：综合处理
            f"""Final translation check and improvement:
"{text}"

Output format: [START]your translation[END]

Ensure:
1. All numbers and units are preserved
2. Translation is complete and accurate
3. Expression is natural and professional

STRICT REQUIREMENTS:
1. MUST output in English only between [START] and [END] tags
2. MUST preserve all special content
3. MUST balance accuracy and fluency
4. MUST NOT include these requirements in output"""
        ]
        
        # 如果有特殊标记，添加相应的处理说明
        if special_marker:
            special_prompt = self.special_markers[special_marker]
        else:
            special_prompt = ""

        return [
            {
                "role": "system", 
                "content": f"""You are a strict English-only translation engine.
                {special_prompt}
                NEVER include instructions in your output.
                ONLY output the translation between [START] and [END] tags."""
            },
            {"role": "user", "content": prompts[min(retry_count, len(prompts)-1)]}
        ]

    def has_chinese(self, text: str) -> bool:
        """检查文本中是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def remove_chinese(self, text: str) -> str:
        """移除文本中的中文字符"""
        return ''.join([char for char in text if not self.has_chinese(char)]) 