"""
Stock Analysis System - Setup Configuration
股票分析系统安装配置
"""

from pathlib import Path

from setuptools import find_packages, setup

# 读取README文件
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 读取requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    requirements = [
        line.strip() for line in requirements_file.read_text().splitlines() 
        if line.strip() and not line.startswith("#")
    ]
else:
    requirements = [
        "pandas>=1.5.0",
 
        "pandas-datareader>=0.10.0",
        "numpy>=1.21.0",
        "requests>=2.28.0",
        "python-dateutil>=2.8.0",
    ]

setup(
    # 基本信息
    name="stock-analysis",
    version="1.0.0",
    author="Jiulong Shan",
    author_email="jiulong.shan@gmail.com",
    description="一个现代化的股票数据获取、存储和技术分析系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    # 项目信息
    url="https://github.com/llshan/stock",
    project_urls={
        "Bug Reports": "https://github.com/llshan/stock/issues",
        "Source": "https://github.com/llshan/stock",
    },
    
    # 包配置
    packages=find_packages(),
    include_package_data=True,
    
    # 依赖
    install_requires=requirements,
    python_requires=">=3.8",
    
    # 分类
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    
    # 命令行工具
    entry_points={
        'console_scripts': [
            'stock-data=stock_analysis.cli.data_manager:main',
            'stock-analyze=stock_analysis.cli.data_analyzer:main', 
            'stock-db=stock_analysis.cli.db_print:main',
            'financial-metrics=stock_analysis.cli.financial_metrics:main',
            'stock-trading=stock_analysis.cli.trading_manager:main',
        ],
    },
    
    # 可选依赖
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "isort>=5.10.0",
        ],
        "plotting": [
            "matplotlib>=3.5.0",
            "plotly>=5.0.0",
        ],
    },
)
