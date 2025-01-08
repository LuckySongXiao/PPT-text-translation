# PPT Translator / PPT翻译工具

## Introduction / 简介
A professional PowerPoint translation tool that supports Chinese-English bidirectional translation with terminology management.
专业的PPT翻译工具，支持中英双向翻译，并具备术语库管理功能。

## Features / 功能特点
- Support PPT/PPTX file translation / 支持PPT/PPTX文件翻译
- Professional terminology management / 专业术语库管理
- Multiple translation models support / 支持多种翻译模型
  - Online models (GLM-4) / 在线模型 (智谱GLM-4)
  - Local models (Ollama) / 本地模型 (Ollama)
- Translation verification system / 翻译复检机制
- Real-time translation progress tracking / 实时翻译进度跟踪
- Translation record export / 翻译记录导出功能

## Installation / 安装方法

bash
git clone https://github.com/LuckySongXiao/PPT-text-translation.git/n
cd PPT-text-translation/n
pip install -r requirements.txt

## Usage / 使用方法
1. Start the application / 启动应用：

Modify your own zhipuai API key in the path PPT text translation\src\utils\config.py
//n
在路径PPT text  translation\src\utils\config.py中修改自己的zhipuai的APIkey

bash
python main.py


2. Access the web interface / 访问Web界面：

http://localhost:7860

3.Model Recommendation/模型推荐
GLM4-1M is recommended for offline models/离线模型推荐使用GLM4-1M
The online model API recommends using glm-4-long/在线模型API建议使用glm-4-long

4. Select PPT file and configure translation settings / 选择PPT文件并配置翻译设置
5. Click "Start Translation" / 点击"开始翻译"
6. Monitor translation progress and verify results / 监控翻译进度并验证结果

## Configuration / 配置说明
- `data/config.json`: Main configuration file / 主配置文件
- `src/json/terminology.json`: Terminology database / 术语库文件

## Requirements / 环境要求
- Python 3.12+
- gradio
- python-pptx
- zhipuai
- requests
- pandas

## License / 许可证
This project is licensed under the MIT License - see the LICENSE file for details.
本项目采用 MIT 许可证 - 详见 LICENSE 文件。
