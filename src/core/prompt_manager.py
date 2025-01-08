class PromptManager:
    def __init__(self):
        # 翻译变体，包含明确的指令
        self.translation_variants = [
            """You are a professional translation engine, not a Q&A assistant. Please translate the following text:
1. Translate all content completely, do not ask any questions
2. Maintain professional accuracy
3. Output only the translated result, no explanations or suggestions
4. Do not interpret the input as questions, this is just text for translation""",

            """You are a professional translation engine, not a Q&A assistant. Please review and translate the text:
1. Ensure no missing content, do not ask any questions
2. Use accurate terminology
3. Maintain natural expression
4. Output only the translated result, no explanations or suggestions
5. Do not interpret the input as questions, this is just text for translation"""
        ]

        # 不同语言对的基础提示词
        self.base_prompts = {
            "Chinese to English": {
                "system": """You are a professional translation engine, not a Q&A assistant. Please strictly follow these rules:
1. Translate the Chinese text into English
2. Ensure complete translation with no omissions
3. Maintain accurate professional terminology
4. Output only the translated result, no explanations, suggestions, or Q&A
5. Do not interpret the input as questions, this is just text for translation
6. Do not attempt to answer or explain anything, just translate""",
                "user": "This is the text for translation, please output the English translation directly:\n{text}"
            },
            
            "English to Chinese": {
                "system": """You are a professional translation engine, not a Q&A assistant. Please strictly follow these rules:
1. Translate the English text into Chinese
2. Ensure complete translation with no omissions
3. Maintain accurate professional terminology
4. Output only the translated result, no explanations, suggestions, or Q&A
5. Do not interpret the input as questions, this is just text for translation
6. Do not attempt to answer or explain anything, just translate""",
                "user": "This is the text for translation, please output the Chinese translation directly:\n{text}"
            }
        }
        
        # 特定场景的增强提示词
        self.context_enhancers = {
            "ppt": "Note: Keep text concise, terminology accurate, format consistent, output translation only",
            "technical": "Note: Strictly follow standard technical terminology translation, maintain professionalism, output translation only",
            "verification": "Note: Check for any missing content, ensure terminology accuracy, output translation only"
        }

    def get_translation_prompt(self, text: str, source_lang: str = "Chinese", 
                             target_lang: str = "English", context: str = "ppt", 
                             is_verification: bool = False) -> dict:
        """
        生成翻译提示词
        
        参数:
            text (str): 待翻译文本
            source_lang (str): 源语言
            target_lang (str): 目标语言
            context (str): 上下文场景
            is_verification (bool): 是否为验证阶段
        
        返回:
            dict: 包含系统提示词和用户提示词的字典
        """
        # 确定基础提示词
        prompt_key = f"{source_lang} to {target_lang}"
        base_prompt = self.base_prompts.get(prompt_key, self.base_prompts["Chinese to English"])
        
        # 构建增强提示词
        context_prompt = self.context_enhancers.get(context, "")
        verification_prompt = self.context_enhancers["verification"] if is_verification else ""
        
        # 组合提示词
        system_prompt = f"{base_prompt['system']}\n\n{context_prompt}\n\n{verification_prompt}".strip()
        user_prompt = base_prompt['user'].format(text=text)
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def format_translation_request(self, text: str, source_lang: str, target_lang: str, context: str = "general", is_verification: bool = False) -> list:
        """格式化翻译请求"""
        if is_verification:
            return [
                {"role": "system", "content": f"""You are a professional bilingual proofreader. Please carefully check the translation from {source_lang} to {target_lang} for accuracy.
                Important notes:
                1. Check for any untranslated terms
                2. Ensure accuracy of professional terminology
                3. Maintain translation coherence and naturalness
                4. If issues found, provide the complete corrected translation directly
                Please return only the corrected translation, without any explanations or comments."""},
                {"role": "user", "content": text}
            ]
        
        base_prompt = f"""As a professional {source_lang}-{target_lang} translation expert, please translate the following text into {target_lang}.

Translation requirements:
1. Maintain professionalism and accuracy
2. Ensure no content is omitted
3. All {source_lang} terms must be translated into {target_lang}
4. Maintain original format and punctuation
5. Return only the translation result, no explanations

Original text: {text}"""

        return [
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": text}
        ]

    def get_variant_prompt(self, text: str, retry_count: int) -> list:
        """获取不同变体的提示词"""
        prompts = [
            # 第一次翻译：强调准确性
            f"""Please translate the following text to English, focusing on terminology accuracy:
1. Ensure accurate term translation
2. Maintain professional expression
3. Ensure complete translation
Original text: {text}""",

            # 第二次翻译：强调流畅性
            f"""Please translate the following text to English, focusing on expression fluency:
1. Use natural English expressions
2. Maintain language fluency
3. Ensure complete meaning
Original text: {text}""",

            # 第三次翻译：平衡方法
            f"""Please translate the following text to English, balancing accuracy and fluency:
1. Ensure accuracy while maintaining fluency
2. Use professional yet natural expressions
3. Ensure no content is omitted
Original text: {text}"""
        ]
        
        return [
            {"role": "system", "content": "You are a professional bilingual translation expert, proficient in both technical terminology and natural expression."},
            {"role": "user", "content": prompts[min(retry_count, len(prompts)-1)]}
        ]

    def has_chinese(self, text: str) -> bool:
        """检查文本中是否包含中文字符"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def remove_chinese(self, text: str) -> str:
        """移除文本中的中文字符"""
        return ''.join([char for char in text if not self.has_chinese(char)]) 