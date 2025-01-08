from src.core.translator import Translator
from src.ui.gradio_app import TranslatorUI
from src.utils.config import Config

def main():
    # 加载配置
    config = Config()
    
    # 初始化翻译器
    translator = Translator(config)
    
    # 创建并启动UI
    ui = TranslatorUI(translator)
    ui.create_ui().launch(share=True)

if __name__ == "__main__":
    main() 