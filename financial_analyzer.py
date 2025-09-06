import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class FinancialDataFetcher:
    def __init__(self):
        pass
    
    def get_financial_statements(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """获取财务报表数据"""
        try:
            time.sleep(1)  # 避免请求限制
            ticker = yf.Ticker(symbol)
            
            # 获取财务报表
            income_stmt = ticker.financials  # 利润表
            balance_sheet = ticker.balance_sheet  # 资产负债表
            cash_flow = ticker.cashflow  # 现金流量表
            
            # 获取关键指标
            key_stats = ticker.info
            
            return {
                'income_statement': income_stmt,
                'balance_sheet': balance_sheet,
                'cash_flow': cash_flow,
                'key_stats': key_stats
            }
        except Exception as e:
            print(f"获取 {symbol} 财务数据时出错: {str(e)}")
            return {}
    
    def get_quarterly_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """获取季度财务数据"""
        try:
            time.sleep(1)
            ticker = yf.Ticker(symbol)
            
            # 获取季度财务报表
            quarterly_income = ticker.quarterly_financials
            quarterly_balance = ticker.quarterly_balance_sheet
            quarterly_cashflow = ticker.quarterly_cashflow
            
            return {
                'quarterly_income': quarterly_income,
                'quarterly_balance': quarterly_balance,
                'quarterly_cashflow': quarterly_cashflow
            }
        except Exception as e:
            print(f"获取 {symbol} 季度财务数据时出错: {str(e)}")
            return {}

class FinancialAnalyzer:
    def __init__(self, data_fetcher: FinancialDataFetcher):
        self.data_fetcher = data_fetcher
    
    def calculate_financial_ratios(self, symbol: str) -> Dict:
        """计算关键财务比率"""
        try:
            data = self.data_fetcher.get_financial_statements(symbol)
            if not data:
                return {'error': f'无法获取 {symbol} 的财务数据'}
            
            income_stmt = data['income_statement']
            balance_sheet = data['balance_sheet']
            cash_flow = data['cash_flow']
            key_stats = data['key_stats']
            
            # 获取最新年份数据
            latest_year = income_stmt.columns[0] if not income_stmt.empty else None
            if latest_year is None:
                return {'error': f'{symbol} 财务数据不完整'}
            
            # 提取关键财务指标
            ratios = {}
            
            # 盈利能力指标
            total_revenue = income_stmt.loc['Total Revenue', latest_year] if 'Total Revenue' in income_stmt.index else 0
            net_income = income_stmt.loc['Net Income', latest_year] if 'Net Income' in income_stmt.index else 0
            
            if total_revenue and total_revenue > 0:
                ratios['net_profit_margin'] = (net_income / total_revenue) * 100
            
            # ROE (净资产收益率)
            total_equity = balance_sheet.loc['Total Stockholder Equity', latest_year] if 'Total Stockholder Equity' in balance_sheet.index else 0
            if total_equity and total_equity > 0:
                ratios['roe'] = (net_income / total_equity) * 100
            
            # ROA (资产收益率)
            total_assets = balance_sheet.loc['Total Assets', latest_year] if 'Total Assets' in balance_sheet.index else 0
            if total_assets and total_assets > 0:
                ratios['roa'] = (net_income / total_assets) * 100
            
            # 负债率
            total_debt = balance_sheet.loc['Total Debt', latest_year] if 'Total Debt' in balance_sheet.index else 0
            if total_assets and total_assets > 0:
                ratios['debt_ratio'] = (total_debt / total_assets) * 100
            
            # 流动比率
            current_assets = balance_sheet.loc['Current Assets', latest_year] if 'Current Assets' in balance_sheet.index else 0
            current_liabilities = balance_sheet.loc['Current Liabilities', latest_year] if 'Current Liabilities' in balance_sheet.index else 0
            if current_liabilities and current_liabilities > 0:
                ratios['current_ratio'] = current_assets / current_liabilities
            
            # P/E比率和其他市场指标
            ratios['pe_ratio'] = key_stats.get('trailingPE', 0)
            ratios['pb_ratio'] = key_stats.get('priceToBook', 0)
            ratios['market_cap'] = key_stats.get('marketCap', 0)
            ratios['enterprise_value'] = key_stats.get('enterpriseValue', 0)
            
            # 历史数据趋势分析
            ratios['revenue_growth'] = self._calculate_growth_rate(income_stmt, 'Total Revenue')
            ratios['income_growth'] = self._calculate_growth_rate(income_stmt, 'Net Income')
            
            return {
                'symbol': symbol,
                'analysis_date': latest_year.strftime('%Y-%m-%d') if hasattr(latest_year, 'strftime') else str(latest_year),
                'ratios': ratios,
                'raw_data': data
            }
            
        except Exception as e:
            return {'error': f'计算 {symbol} 财务比率时出错: {str(e)}'}
    
    def _calculate_growth_rate(self, data: pd.DataFrame, metric: str) -> List[float]:
        """计算增长率"""
        try:
            if metric not in data.index:
                return []
            
            values = data.loc[metric].dropna()
            if len(values) < 2:
                return []
            
            growth_rates = []
            for i in range(len(values) - 1):
                current = values.iloc[i]
                previous = values.iloc[i + 1]
                if previous != 0:
                    growth_rate = ((current - previous) / abs(previous)) * 100
                    growth_rates.append(growth_rate)
            
            return growth_rates
        except:
            return []
    
    def analyze_financial_health(self, symbol: str) -> Dict:
        """综合财务健康评估"""
        ratios_data = self.calculate_financial_ratios(symbol)
        
        if 'error' in ratios_data:
            return ratios_data
        
        ratios = ratios_data['ratios']
        health_score = 0
        max_score = 100
        
        # 盈利能力评分 (30分)
        net_margin = ratios.get('net_profit_margin', 0)
        if net_margin > 15:
            health_score += 30
        elif net_margin > 10:
            health_score += 20
        elif net_margin > 5:
            health_score += 10
        
        # ROE评分 (20分)
        roe = ratios.get('roe', 0)
        if roe > 15:
            health_score += 20
        elif roe > 10:
            health_score += 15
        elif roe > 5:
            health_score += 10
        
        # 负债水平评分 (20分)
        debt_ratio = ratios.get('debt_ratio', 100)
        if debt_ratio < 30:
            health_score += 20
        elif debt_ratio < 50:
            health_score += 15
        elif debt_ratio < 70:
            health_score += 10
        
        # 流动性评分 (15分)
        current_ratio = ratios.get('current_ratio', 0)
        if current_ratio > 2:
            health_score += 15
        elif current_ratio > 1.5:
            health_score += 10
        elif current_ratio > 1:
            health_score += 5
        
        # 估值评分 (15分)
        pe_ratio = ratios.get('pe_ratio', 0)
        if 0 < pe_ratio < 15:
            health_score += 15
        elif 15 <= pe_ratio < 25:
            health_score += 10
        elif 25 <= pe_ratio < 35:
            health_score += 5
        
        # 确定财务健康等级
        if health_score >= 80:
            grade = 'A - 优秀'
        elif health_score >= 60:
            grade = 'B - 良好'
        elif health_score >= 40:
            grade = 'C - 一般'
        elif health_score >= 20:
            grade = 'D - 较差'
        else:
            grade = 'F - 差'
        
        return {
            'symbol': symbol,
            'health_score': health_score,
            'max_score': max_score,
            'grade': grade,
            'ratios': ratios,
            'recommendations': self._generate_recommendations(ratios)
        }
    
    def _generate_recommendations(self, ratios: Dict) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        # 盈利能力建议
        net_margin = ratios.get('net_profit_margin', 0)
        if net_margin < 5:
            recommendations.append("净利润率偏低，关注公司盈利能力改善")
        elif net_margin > 20:
            recommendations.append("净利润率优秀，盈利能力强")
        
        # ROE建议
        roe = ratios.get('roe', 0)
        if roe < 10:
            recommendations.append("净资产收益率偏低，股东回报率有待提高")
        elif roe > 20:
            recommendations.append("净资产收益率优秀，为股东创造良好回报")
        
        # 负债建议
        debt_ratio = ratios.get('debt_ratio', 0)
        if debt_ratio > 70:
            recommendations.append("负债率较高，需关注偿债风险")
        elif debt_ratio < 20:
            recommendations.append("负债率较低，财务结构稳健")
        
        # 估值建议
        pe_ratio = ratios.get('pe_ratio', 0)
        if pe_ratio > 30:
            recommendations.append("市盈率较高，估值可能偏高")
        elif 0 < pe_ratio < 15:
            recommendations.append("市盈率合理，估值相对合理")
        
        return recommendations

class FinancialChartGenerator:
    def __init__(self):
        try:
            plt.style.use('seaborn-v0_8')
        except:
            try:
                plt.style.use('seaborn')
            except:
                pass
    
    def create_revenue_trend_chart(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建营收趋势图"""
        try:
            raw_data = analysis_data['raw_data']
            income_stmt = raw_data['income_statement']
            
            if 'Total Revenue' not in income_stmt.index:
                print("未找到营收数据")
                return
            
            revenue_data = income_stmt.loc['Total Revenue'].dropna()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[str(date)[:4] for date in revenue_data.index],
                y=revenue_data.values / 1e9,  # 转换为十亿
                mode='lines+markers',
                name='总营收',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title=f'{analysis_data["symbol"]} 营收趋势 (过去5年)',
                xaxis_title='年份',
                yaxis_title='营收 (十亿美元)',
                template='plotly_white'
            )
            
            if save_path:
                fig.write_html(save_path)
            else:
                fig.show()
                
        except Exception as e:
            print(f"生成营收趋势图时出错: {str(e)}")
    
    def create_profitability_chart(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建盈利能力图表"""
        try:
            ratios = analysis_data['ratios']
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'{analysis_data["symbol"]} 财务指标分析', fontsize=16)
            
            # 盈利能力指标
            metrics = ['净利润率', 'ROE', 'ROA']
            values = [
                ratios.get('net_profit_margin', 0),
                ratios.get('roe', 0),
                ratios.get('roa', 0)
            ]
            
            ax1.bar(metrics, values, color=['lightblue', 'lightgreen', 'lightcoral'])
            ax1.set_title('盈利能力指标 (%)')
            ax1.set_ylabel('百分比')
            
            # 负债水平
            debt_ratio = ratios.get('debt_ratio', 0)
            equity_ratio = 100 - debt_ratio
            ax2.pie([debt_ratio, equity_ratio], labels=['负债', '权益'], autopct='%1.1f%%',
                   colors=['lightcoral', 'lightgreen'])
            ax2.set_title('资本结构')
            
            # 估值指标
            pe = ratios.get('pe_ratio', 0)
            pb = ratios.get('pb_ratio', 0)
            ax3.bar(['市盈率(PE)', '市净率(PB)'], [pe, pb], 
                   color=['lightsalmon', 'lightsteelblue'])
            ax3.set_title('估值指标')
            ax3.set_ylabel('倍数')
            
            # 流动性
            current_ratio = ratios.get('current_ratio', 0)
            ax4.bar(['流动比率'], [current_ratio], color='lightblue', width=0.5)
            ax4.axhline(y=1, color='r', linestyle='--', alpha=0.7, label='安全线')
            ax4.set_title('流动性指标')
            ax4.set_ylabel('倍数')
            ax4.legend()
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
            else:
                plt.show()
                
        except Exception as e:
            print(f"生成盈利能力图表时出错: {str(e)}")
    
    def create_financial_health_dashboard(self, health_data: Dict, save_path: Optional[str] = None):
        """创建财务健康仪表盘"""
        try:
            fig = go.Figure()
            
            # 添加仪表盘
            fig.add_trace(go.Indicator(
                mode="gauge+number+delta",
                value=health_data['health_score'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"{health_data['symbol']} 财务健康评分"},
                delta={'reference': 80},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 20], 'color': "red"},
                        {'range': [20, 40], 'color': "orange"},
                        {'range': [40, 60], 'color': "yellow"},
                        {'range': [60, 80], 'color': "lightgreen"},
                        {'range': [80, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(
                title=f'财务健康等级: {health_data["grade"]}',
                height=400
            )
            
            if save_path:
                fig.write_html(save_path)
            else:
                fig.show()
                
        except Exception as e:
            print(f"生成财务健康仪表盘时出错: {str(e)}")

# 模拟财务数据生成器 (用于演示)
class MockFinancialDataFetcher:
    def generate_mock_financial_data(self, symbol: str) -> Dict:
        """生成模拟财务数据"""
        np.random.seed(hash(symbol) % 2**32)
        
        # 生成5年财务数据
        years = [2019, 2020, 2021, 2022, 2023]
        
        # 模拟营收增长
        base_revenue = np.random.uniform(10, 100) * 1e9  # 100亿到1000亿
        revenues = []
        for i, year in enumerate(years):
            growth = np.random.uniform(-0.1, 0.15)  # -10%到15%增长
            if i == 0:
                revenues.append(base_revenue)
            else:
                revenues.append(revenues[-1] * (1 + growth))
        
        # 生成其他财务指标
        net_margins = np.random.uniform(5, 20, 5)  # 净利润率5%-20%
        net_incomes = [rev * margin / 100 for rev, margin in zip(revenues, net_margins)]
        
        mock_data = {
            'symbol': symbol,
            'years': years,
            'revenues': revenues,
            'net_incomes': net_incomes,
            'net_margins': net_margins,
            'ratios': {
                'net_profit_margin': net_margins[-1],
                'roe': np.random.uniform(8, 25),
                'roa': np.random.uniform(3, 15),
                'debt_ratio': np.random.uniform(20, 70),
                'current_ratio': np.random.uniform(1.2, 3.0),
                'pe_ratio': np.random.uniform(10, 35),
                'pb_ratio': np.random.uniform(1, 8),
                'market_cap': revenues[-1] * np.random.uniform(2, 10)
            }
        }
        
        return mock_data

if __name__ == "__main__":
    # 示例使用
    print("财务分析模块测试...")
    
    # 使用模拟数据进行测试
    mock_fetcher = MockFinancialDataFetcher()
    mock_data = mock_fetcher.generate_mock_financial_data("AAPL")
    
    print(f"模拟数据生成成功: {mock_data['symbol']}")
    print(f"最新营收: ${mock_data['revenues'][-1]/1e9:.2f}B")
    print(f"净利润率: {mock_data['ratios']['net_profit_margin']:.2f}%")
    print(f"ROE: {mock_data['ratios']['roe']:.2f}%")