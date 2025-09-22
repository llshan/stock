#!/usr/bin/env python3
"""
数据一致性检查脚本
定期验证批次数据与交易记录的一致性
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stock_analysis.data.storage import create_storage
from stock_analysis.trading.services.lot_transaction_service import LotTransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG


def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_user_consistency(service: LotTransactionService, user_id: str, alert_on_failure: bool = False) -> dict:
    """检查单个用户的数据一致性"""
    print(f"\n=== 检查用户: {user_id} ===")
    
    result = service.validate_data_consistency(user_id)
    
    print(f"检查股票数: {result['symbols_checked']}")
    print(f"发现问题: {result['issues_found']}")
    print(f"一致性状态: {'✅ 通过' if result['is_consistent'] else '❌ 失败'}")
    
    if result['issues']:
        print("\n发现的问题:")
        for issue in result['issues']:
            print(f"  • {issue['description']}")
            if 'symbol' in issue:
                print(f"    股票: {issue['symbol']}")
    
    if result['statistics']:
        print("\n统计信息:")
        for symbol, stats in result['statistics'].items():
            print(f"  {symbol}:")
            print(f"    买入交易: {stats['buy_transactions']}")
            print(f"    卖出交易: {stats['sell_transactions']}")
            print(f"    持仓批次: {stats['position_lots']}")
            print(f"    活跃批次: {stats['active_lots']}")
            print(f"    已关闭批次: {stats['closed_lots']}")
    
    # 如果启用告警且检查失败，发送告警
    if alert_on_failure and not result['is_consistent']:
        send_alert(user_id, result)
    
    return result


def send_alert(user_id: str, result: dict):
    """发送告警（简化实现）"""
    print(f"\n🚨 告警: 用户 {user_id} 数据一致性检查失败")
    print(f"问题数量: {result['issues_found']}")
    
    # 在实际部署中，这里可以发送邮件、Slack消息等
    # 示例：
    # import smtplib
    # send_email(subject=f"数据一致性告警: {user_id}", body=str(result['issues']))


def get_all_users(storage) -> list:
    """获取系统中的所有用户ID"""
    try:
        # 从交易记录中获取所有用户
        cursor = storage.cursor
        sql = f"""
        SELECT DISTINCT {storage.config.Fields.Transactions.USER_ID}
        FROM {storage.config.Tables.TRANSACTIONS}
        ORDER BY {storage.config.Fields.Transactions.USER_ID}
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='数据一致性检查工具')
    parser.add_argument('--db-path', default='database/stock_data.db', help='数据库路径')
    parser.add_argument('--user-id', help='检查特定用户（可选）')
    parser.add_argument('--all-users', action='store_true', help='检查所有用户')
    parser.add_argument('--alert-on-failure', action='store_true', help='失败时发送告警')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    print(f"数据一致性检查开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库路径: {args.db_path}")
    
    try:
        # 创建存储和服务
        storage = create_storage('sqlite', db_path=args.db_path)
        service = LotTransactionService(storage, DEFAULT_TRADING_CONFIG)
        
        # 检查批次追踪表是否存在
        if not storage.lot_tracking_tables_exist():
            print("❌ 批次追踪表不存在，请先执行迁移")
            return 1
        
        results = []
        
        if args.user_id:
            # 检查特定用户
            result = check_user_consistency(service, args.user_id, args.alert_on_failure)
            results.append(result)
            
        elif args.all_users:
            # 检查所有用户
            users = get_all_users(storage)
            if not users:
                print("未找到任何用户数据")
                return 0
            
            print(f"找到 {len(users)} 个用户，开始检查...")
            
            for user_id in users:
                try:
                    result = check_user_consistency(service, user_id, args.alert_on_failure)
                    results.append(result)
                except Exception as e:
                    print(f"检查用户 {user_id} 时出错: {e}")
                    if args.alert_on_failure:
                        send_alert(user_id, {'issues': [f"检查过程出错: {e}"], 'issues_found': 1})
        
        else:
            print("请指定 --user-id 或 --all-users")
            return 1
        
        # 汇总结果
        total_users = len(results)
        consistent_users = sum(1 for r in results if r['is_consistent'])
        total_issues = sum(r['issues_found'] for r in results)
        
        print(f"\n=== 检查汇总 ===")
        print(f"检查用户数: {total_users}")
        print(f"一致性通过: {consistent_users}")
        print(f"一致性失败: {total_users - consistent_users}")
        print(f"总问题数: {total_issues}")
        
        if total_issues == 0:
            print("✅ 所有检查通过，数据一致性良好")
            return 0
        else:
            print("❌ 发现数据一致性问题，请检查详细信息")
            return 1
        
    except Exception as e:
        print(f"检查过程出错: {e}")
        if args.alert_on_failure:
            send_alert("SYSTEM", {'issues': [f"系统检查出错: {e}"], 'issues_found': 1})
        return 1
    
    finally:
        if 'storage' in locals():
            storage.close()


if __name__ == '__main__':
    sys.exit(main())