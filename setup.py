#!/usr/bin/env python3
"""
Stock Analysis Package Setup
股票数据下载和分析工具包
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    """读取README文件内容"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Stock data download and analysis toolkit"

# 读取requirements
def read_requirements():
    """读取requirements.txt文件"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [
        'yfinance>=0.2.0',
        'pandas>=1.5.0',
        'pandas-datareader>=0.10.0',
        'numpy>=1.20.0',
        'matplotlib>=3.5.0',
        'seaborn>=0.11.0',
        'requests>=2.28.0',
        'plotly>=5.10.0',
        'kaleido>=0.2.1'
    ]

setup(
    name="stock-analysis",
    version="1.0.0",
    description="Stock data download and analysis toolkit",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Stock Analysis Team",
    author_email="your-email@example.com",
    url="https://github.com/your-username/stock-analysis",
    
    # 包配置
    packages=find_packages(),
    include_package_data=True,
    
    # Python版本要求
    python_requires=">=3.8",
    
    # 依赖
    install_requires=read_requirements(),
    
    # 可选依赖
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=1.0.0',
        ],
        'cloud': [
            'boto3>=1.26.0',
            'google-cloud-storage>=2.7.0',
        ],
    },
    
    # 命令行工具
    entry_points={
        'console_scripts': [
            'stock-download=Stock.data_service.yfinance_downloader:main',
            'stock-hybrid=Stock.data_service.hybrid_downloader:main',
            'stock-analyze=Stock.analyzer.comprehensive_analyzer:main',
        ],
    },
    
    # 分类信息
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    
    # 关键词
    keywords="stock, finance, data, analysis, yfinance, stooq, trading",
    
    # 项目URLs
    project_urls={
        "Bug Reports": "https://github.com/your-username/stock-analysis/issues",
        "Source": "https://github.com/your-username/stock-analysis",
        "Documentation": "https://github.com/your-username/stock-analysis/wiki",
    },
    
    # 许可证
    license="MIT",
    
    # 包数据
    package_data={
        'Stock': ['*.md', '*.txt', '*.yml', '*.yaml'],
        'Stock.data_service': ['*.sql'],
        'Stock.analyzer': ['templates/*.html'],
    },
    
    # 排除的包
    exclude_package_data={
        '': ['*.pyc', '__pycache__', '*.so', '*.dylib'],
    },
    
    # Zip安全
    zip_safe=False,
)