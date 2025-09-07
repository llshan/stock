#!/usr/bin/env python3
"""
GCP数据库设置模块
配置Cloud SQL PostgreSQL数据库
"""

import os
import sys
import logging
from logging_utils import setup_logging
from typing import Dict, Optional

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.cloud.sql.connector import Connector
    import sqlalchemy
    from analyzer.database import StockDatabase
except ImportError as e:
    logging.getLogger(__name__).error(f"需要安装GCP依赖: {e}")
    logging.getLogger(__name__).info("请运行: pip install google-cloud-sql-python-connector sqlalchemy psycopg2-binary")

class GCPStockDatabase(StockDatabase):
    def __init__(self, project_id: str, region: str, instance_name: str, 
                 database_name: str, username: str, password: str):
        """
        初始化GCP Cloud SQL数据库连接
        
        Args:
            project_id: GCP项目ID
            region: Cloud SQL实例区域
            instance_name: Cloud SQL实例名
            database_name: 数据库名
            username: 数据库用户名
            password: 数据库密码
        """
        self.project_id = project_id
        self.region = region
        self.instance_name = instance_name
        self.database_name = database_name
        self.username = username
        self.password = password
        
        self.logger = logging.getLogger(__name__)
        
        # 创建连接
        self._create_connection()
        
        # 调用父类初始化（创建表结构）
        self._create_tables()
    
    def _create_connection(self):
        """创建到Cloud SQL的连接"""
        try:
            # 初始化连接器
            self.connector = Connector()
            
            # 构建连接字符串
            instance_connection_name = f"{self.project_id}:{self.region}:{self.instance_name}"
            
            def getconn():
                conn = self.connector.connect(
                    instance_connection_name,
                    "pg8000",
                    user=self.username,
                    password=self.password,
                    db=self.database_name,
                )
                return conn
            
            # 创建SQLAlchemy引擎
            self.engine = sqlalchemy.create_engine(
                "postgresql+pg8000://",
                creator=getconn,
            )
            
            # 获取原始连接用于执行SQL
            self.connection = self.engine.raw_connection()
            self.cursor = self.connection.cursor()
            
            self.logger.info(f"✅ 已连接到 Cloud SQL: {instance_connection_name}")
            
        except Exception as e:
            self.logger.error(f"❌ 连接 Cloud SQL 失败: {str(e)}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        try:
            if hasattr(self, 'connector'):
                self.connector.close()
            if hasattr(self, 'connection'):
                self.connection.close()
            if hasattr(self, 'engine'):
                self.engine.dispose()
            self.logger.info("📊 Cloud SQL 连接已关闭")
        except Exception as e:
            self.logger.warning(f"关闭连接时出现警告: {str(e)}")

def create_cloud_sql_instance():
    """
    创建Cloud SQL实例的gcloud命令
    这些命令需要在部署时手动执行
    """
    commands = [
        "# 创建 Cloud SQL PostgreSQL 实例",
        "gcloud sql instances create stock-analysis-db \\",
        "    --database-version=POSTGRES_14 \\",
        "    --tier=db-f1-micro \\",
        "    --region=us-central1 \\",
        "    --storage-type=SSD \\",
        "    --storage-size=10GB \\",
        "    --backup \\",
        "    --maintenance-window-day=SUN \\",
        "    --maintenance-window-hour=02",
        "",
        "# 创建数据库",
        "gcloud sql databases create stockdb \\",
        "    --instance=stock-analysis-db",
        "",
        "# 创建数据库用户",
        "gcloud sql users create stockuser \\",
        "    --instance=stock-analysis-db \\",
        "    --password=YOUR_SECURE_PASSWORD",
        "",
        "# 获取连接信息",
        "gcloud sql instances describe stock-analysis-db \\",
        "    --format='value(connectionName)'"
    ]
    
    return "\n".join(commands)

def get_database_config() -> Dict[str, str]:
    """从环境变量获取数据库配置"""
    return {
        'project_id': os.environ.get('GCP_PROJECT_ID'),
        'region': os.environ.get('CLOUD_SQL_REGION', 'us-central1'),
        'instance_name': os.environ.get('CLOUD_SQL_INSTANCE', 'stock-analysis-db'),
        'database_name': os.environ.get('CLOUD_SQL_DATABASE', 'stockdb'),
        'username': os.environ.get('CLOUD_SQL_USERNAME', 'stockuser'),
        'password': os.environ.get('CLOUD_SQL_PASSWORD')
    }

def create_database_connection() -> Optional[GCPStockDatabase]:
    """创建数据库连接（用于Cloud Function）"""
    try:
        config = get_database_config()
        
        # 检查必需的配置
        required_configs = ['project_id', 'password']
        for key in required_configs:
            if not config[key]:
                raise ValueError(f"缺少必需的环境变量: {key.upper()}")
        
        # 创建数据库连接
        db = GCPStockDatabase(
            project_id=config['project_id'],
            region=config['region'],
            instance_name=config['instance_name'],
            database_name=config['database_name'],
            username=config['username'],
            password=config['password']
        )
        
        return db
        
    except Exception as e:
        logging.error(f"创建数据库连接失败: {str(e)}")
        return None

if __name__ == "__main__":
    setup_logging()
    logging.getLogger(__name__).info("🗄️ GCP Cloud SQL 设置指南")
    logging.getLogger(__name__).info("=" * 50)
    logging.getLogger(__name__).info("\n1. 执行以下命令创建 Cloud SQL 实例:")
    logging.getLogger(__name__).info(create_cloud_sql_instance())
    
    logging.getLogger(__name__).info("\n2. 设置环境变量:")
    config = get_database_config()
    for key, value in config.items():
        env_key = key.upper().replace('_', '_')
        if key in ['project_id', 'password']:
            env_key = f"GCP_{env_key}" if key == 'project_id' else f"CLOUD_SQL_{env_key}"
        else:
            env_key = f"CLOUD_SQL_{env_key}"
        logging.getLogger(__name__).info(f"export {env_key}={value or 'YOUR_VALUE_HERE'}")
    
    logging.getLogger(__name__).info("\n3. 测试数据库连接:")
    logging.getLogger(__name__).info("python cloud/database_setup.py")
