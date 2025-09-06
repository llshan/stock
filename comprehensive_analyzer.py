import os
import time
from datetime import datetime
from typing import Dict, List, Optional

# 导入现有模块
from stock_analyzer import StockAnalyzer, StockDataFetcher, ChartGenerator
from financial_analyzer import FinancialAnalyzer, FinancialDataFetcher, FinancialChartGenerator

class ComprehensiveStockAnalyzer:
    def __init__(self):
        """综合股票分析器"""
        # 初始化技术分析模块
        self.stock_data_fetcher = StockDataFetcher()
        self.stock_analyzer = StockAnalyzer(self.stock_data_fetcher)
        self.stock_chart_generator = ChartGenerator()
        
        # 初始化财务分析模块
        self.financial_data_fetcher = FinancialDataFetcher()
        self.financial_analyzer = FinancialAnalyzer(self.financial_data_fetcher)
        self.financial_chart_generator = FinancialChartGenerator()
    
    def run_comprehensive_analysis(self, symbols: List[str], period: str = "1y"):
        """运行综合分析"""
        results = {}
        
        # 确保analytics目录存在
        os.makedirs('analytics', exist_ok=True)
        
        print("=" * 60)
        print("🚀 启动综合股票分析系统")
        print("=" * 60)
        
        for i, symbol in enumerate(symbols):
            print(f"\n📊 分析股票: {symbol} ({i+1}/{len(symbols)})")
            print("-" * 40)
            
            if i > 0:
                time.sleep(2)  # 避免API限制
            
            # 1. 技术分析
            print("🔍 进行技术分析...")
            technical_analysis = self._perform_technical_analysis(symbol, period)
            
            # 2. 财务分析
            print("📈 进行财务分析...")
            financial_analysis = self._perform_financial_analysis(symbol)
            
            # 3. 生成综合报告
            print("📋 生成综合报告...")
            comprehensive_report = self._generate_comprehensive_report(
                symbol, technical_analysis, financial_analysis
            )
            
            results[symbol] = {
                'technical_analysis': technical_analysis,
                'financial_analysis': financial_analysis,
                'comprehensive_report': comprehensive_report
            }
            
            print(f"✅ {symbol} 分析完成")
        
        print("\n" + "=" * 60)
        print("🎉 所有分析完成！报告已保存到 analytics/ 文件夹")
        print("=" * 60)
        
        return results
    
    def _perform_technical_analysis(self, symbol: str, period: str):
        """执行技术分析"""
        try:
            # 获取实时数据
            real_time = self.stock_data_fetcher.get_real_time_data(symbol)
            if 'error' not in real_time:
                print(f"   💰 当前价格: ${real_time['current_price']:.2f}")
                print(f"   📊 涨跌: {real_time['change']:+.2f} ({real_time['change_percent']:+.2f}%)")
            else:
                print(f"   ❌ 实时数据获取失败: {real_time['error']}")
            
            # 技术指标分析
            analysis = self.stock_analyzer.analyze_stock(symbol, period)
            
            if 'error' not in analysis:
                print(f"   📈 趋势: {analysis['trend']}")
                print(f"   🎯 RSI: {analysis['rsi']:.2f} ({analysis['rsi_signal']})")
                print(f"   📉 布林带位置: {analysis['bb_position']:.2f}")
                
                # 生成技术分析图表
                try:
                    self.stock_chart_generator.create_candlestick_chart(
                        analysis['data'], symbol, f"analytics/{symbol}_candlestick.html"
                    )
                    self.stock_chart_generator.create_rsi_chart(
                        analysis['data'], symbol, f"analytics/{symbol}_rsi.png"
                    )
                    self.stock_chart_generator.create_bollinger_bands_chart(
                        analysis['data'], symbol, f"analytics/{symbol}_bollinger.html"
                    )
                    print(f"   📊 技术分析图表已生成")
                except Exception as e:
                    print(f"   ⚠️ 图表生成失败: {str(e)}")
            else:
                print(f"   ❌ 技术分析失败: {analysis['error']}")
            
            return analysis
                
        except Exception as e:
            print(f"   ❌ 技术分析失败: {str(e)}")
            return {'error': str(e)}
    
    def _perform_financial_analysis(self, symbol: str):
        """执行财务分析"""
        try:
            # 使用真实数据进行财务分析
            financial_analysis = self.financial_analyzer.calculate_financial_ratios(symbol)
            
            if 'error' not in financial_analysis:
                ratios = financial_analysis['ratios']
                print(f"   💹 净利润率: {ratios.get('net_profit_margin', 0):.2f}%")
                print(f"   🏆 ROE: {ratios.get('roe', 0):.2f}%")
                print(f"   💳 负债率: {ratios.get('debt_ratio', 0):.2f}%")
                print(f"   📊 市盈率: {ratios.get('pe_ratio', 0):.2f}")
                
                # 财务健康评估
                health_data = self.financial_analyzer.analyze_financial_health(symbol)
                financial_analysis['health_data'] = health_data
                
                if 'error' not in health_data:
                    print(f"   🏥 财务健康等级: {health_data['grade']}")
                
                # 生成财务分析图表
                try:
                    self.financial_chart_generator.create_profitability_chart(
                        financial_analysis, f"analytics/{symbol}_financial_metrics.png"
                    )
                    
                    if 'error' not in health_data:
                        self.financial_chart_generator.create_financial_health_dashboard(
                            health_data, f"analytics/{symbol}_health_dashboard.html"
                        )
                        
                        # 生成营收趋势图
                        self.financial_chart_generator.create_revenue_trend_chart(
                            financial_analysis, f"analytics/{symbol}_revenue_trend.html"
                        )
                    
                    print(f"   📊 财务分析图表已生成")
                except Exception as e:
                    print(f"   ⚠️ 财务图表生成失败: {str(e)}")
            else:
                print(f"   ❌ 财务分析失败: {financial_analysis['error']}")
            
            return financial_analysis
            
        except Exception as e:
            print(f"   ❌ 财务分析失败: {str(e)}")
            return {'error': str(e)}
    
    def _generate_comprehensive_report(self, symbol: str, technical_analysis: Dict, financial_analysis: Dict) -> Dict:
        """生成综合投资报告"""
        report = {
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'overall_rating': 'N/A',
            'investment_recommendation': '需要更多数据',
            'key_strengths': [],
            'key_concerns': [],
            'summary': ''
        }
        
        try:
            # 技术面评分
            tech_score = 0
            if 'error' not in technical_analysis:
                if technical_analysis.get('trend') == '上升趋势':
                    tech_score += 30
                    report['key_strengths'].append('技术趋势向好')
                
                rsi = technical_analysis.get('rsi', 50)
                if 30 < rsi < 70:
                    tech_score += 20
                    report['key_strengths'].append('RSI指标健康')
                elif rsi > 70:
                    report['key_concerns'].append('RSI显示超买')
                elif rsi < 30:
                    report['key_strengths'].append('RSI显示超卖，可能反弹')
            else:
                report['key_concerns'].append('技术分析数据不可用')
            
            # 财务面评分
            finance_score = 0
            if 'error' not in financial_analysis:
                health_data = financial_analysis.get('health_data', {})
                
                if health_data and 'error' not in health_data:
                    finance_score = health_data.get('health_score', 0)
                    
                    if finance_score >= 80:
                        report['key_strengths'].append('财务状况优秀')
                    elif finance_score >= 60:
                        report['key_strengths'].append('财务状况良好')
                    elif finance_score < 40:
                        report['key_concerns'].append('财务状况需要关注')
                    
                    # 具体财务指标分析
                    ratios = financial_analysis.get('ratios', {})
                    pe_ratio = ratios.get('pe_ratio', 0)
                    if pe_ratio > 30:
                        report['key_concerns'].append('市盈率偏高')
                    elif 0 < pe_ratio < 15:
                        report['key_strengths'].append('估值合理')
                else:
                    report['key_concerns'].append('财务健康数据不可用')
            else:
                report['key_concerns'].append('财务分析数据不可用')
            
            # 综合评分和建议
            total_score = tech_score + finance_score * 0.7  # 财务分析权重稍低
            
            if total_score >= 80:
                report['overall_rating'] = 'A - 强烈推荐'
                report['investment_recommendation'] = '买入'
            elif total_score >= 60:
                report['overall_rating'] = 'B - 推荐'
                report['investment_recommendation'] = '买入/持有'
            elif total_score >= 40:
                report['overall_rating'] = 'C - 中性'
                report['investment_recommendation'] = '持有'
            elif total_score >= 20:
                report['overall_rating'] = 'D - 不推荐'
                report['investment_recommendation'] = '减持'
            else:
                report['overall_rating'] = 'F - 强烈不推荐'
                report['investment_recommendation'] = '卖出'
            
            # 生成总结
            tech_status = "趋势向好" if 'error' not in technical_analysis and technical_analysis.get('trend') == '上升趋势' else "趋势不明"
            finance_status = "良好" if finance_score >= 60 else "一般" if finance_score >= 40 else "较差"
            
            report['summary'] = f"""
基于真实市场数据的综合分析，{symbol}获得{report['overall_rating']}评级。
技术分析显示{tech_status}，财务分析显示{finance_status}的财务状况。
投资建议：{report['investment_recommendation']}。
            """.strip()
            
        except Exception as e:
            report['summary'] = f"生成报告时出错: {str(e)}"
        
        return report

if __name__ == "__main__":
    # 综合分析示例
    print("=== 综合股票分析系统 ===")
    
    # 创建分析器
    analyzer = ComprehensiveStockAnalyzer()
    
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    
    print(f"开始分析股票: {', '.join(symbols)}")
    results = analyzer.run_comprehensive_analysis(symbols, period="6mo")
    
    # 打印综合报告摘要
    print("\n" + "="*60)
    print("📋 综合分析报告摘要")
    print("="*60)
    
    for symbol, data in results.items():
        report = data['comprehensive_report']
        print(f"\n🏢 {symbol}:")
        print(f"   评级: {report['overall_rating']}")
        print(f"   建议: {report['investment_recommendation']}")
        print(f"   优势: {', '.join(report['key_strengths'][:2]) if report['key_strengths'] else '无'}")
        print(f"   风险: {', '.join(report['key_concerns'][:2]) if report['key_concerns'] else '无'}")
    
    print(f"\n✅ 所有图表和报告已保存到 analytics/ 文件夹")