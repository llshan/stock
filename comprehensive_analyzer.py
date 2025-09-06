import os
import time
from datetime import datetime
from typing import Dict, List, Optional

# 导入现有模块
from stock_analyzer import StockAnalyzer, StockDataFetcher, ChartGenerator
from financial_analyzer import FinancialAnalyzer, FinancialDataFetcher, FinancialChartGenerator, MockFinancialDataFetcher

class ComprehensiveStockAnalyzer:
    def __init__(self, use_mock_data: bool = False):
        """
        综合股票分析器
        
        Args:
            use_mock_data: 是否使用模拟数据 (True: 演示模式, False: 真实数据模式)
        """
        self.use_mock_data = use_mock_data
        
        # 初始化技术分析模块
        self.stock_data_fetcher = StockDataFetcher()
        
        self.stock_analyzer = StockAnalyzer(self.stock_data_fetcher)
        self.stock_chart_generator = ChartGenerator()
        
        # 初始化财务分析模块
        if use_mock_data:
            self.financial_data_fetcher = MockFinancialDataFetcher()
            self.financial_analyzer = None  # 模拟模式使用不同的分析方法
        else:
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
            if self.use_mock_data:
                # 使用模拟数据进行技术分析
                return self._mock_technical_analysis(symbol, period)
            else:
                # 使用真实数据进行技术分析
                return self._real_technical_analysis(symbol, period)
                
        except Exception as e:
            print(f"   ❌ 技术分析失败: {str(e)}")
            return {'error': str(e)}
    
    def _real_technical_analysis(self, symbol: str, period: str):
        """真实数据技术分析"""
        # 获取实时数据
        real_time = self.stock_data_fetcher.get_real_time_data(symbol)
        if 'error' not in real_time:
            print(f"   💰 当前价格: ${real_time['current_price']:.2f}")
            print(f"   📊 涨跌: {real_time['change']:+.2f} ({real_time['change_percent']:+.2f}%)")
        
        # 技术指标分析
        analysis = self.stock_analyzer.analyze_stock(symbol, period)
        
        if 'error' not in analysis:
            print(f"   📈 趋势: {analysis['trend']}")
            print(f"   🎯 RSI: {analysis['rsi']:.2f} ({analysis['rsi_signal']})")
            print(f"   📉 布林带位置: {analysis['bb_position']:.2f}")
            
            # 生成技术分析图表
            self.stock_chart_generator.create_candlestick_chart(
                analysis['data'], symbol, f"analytics/{symbol}_candlestick.html"
            )
            self.stock_chart_generator.create_rsi_chart(
                analysis['data'], symbol, f"analytics/{symbol}_rsi.png"
            )
            self.stock_chart_generator.create_bollinger_bands_chart(
                analysis['data'], symbol, f"analytics/{symbol}_bollinger.html"
            )
        
        return analysis
    
    def _mock_technical_analysis(self, symbol: str, period: str):
        """模拟数据技术分析"""
        import numpy as np
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 生成模拟技术分析数据
        np.random.seed(hash(symbol) % 2**32)
        
        # 模拟当前价格
        current_price = np.random.uniform(50, 300)
        change = np.random.uniform(-10, 10)
        change_percent = change / current_price * 100
        
        print(f"   💰 当前价格: ${current_price:.2f} (演示)")
        print(f"   📊 涨跌: {change:+.2f} ({change_percent:+.2f}%) (演示)")
        
        # 模拟RSI和其他指标
        rsi = np.random.uniform(20, 80)
        bb_position = np.random.uniform(0, 1)
        trend = "上升趋势" if np.random.random() > 0.5 else "下降趋势"
        
        if rsi > 70:
            rsi_signal = "超买"
        elif rsi < 30:
            rsi_signal = "超卖"
        else:
            rsi_signal = "中性"
        
        print(f"   📈 趋势: {trend} (演示)")
        print(f"   🎯 RSI: {rsi:.2f} ({rsi_signal}) (演示)")
        print(f"   📉 布林带位置: {bb_position:.2f} (演示)")
        
        # 生成模拟价格数据用于图表
        days = 180 if period == "6mo" else 365
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             end=datetime.now(), freq='D')
        
        prices = [current_price]
        for _ in range(len(dates) - 1):
            change = np.random.normal(0, 0.02)
            prices.append(prices[-1] * (1 + change))
        
        # 创建模拟OHLCV数据
        closes = np.array(prices)
        highs = closes * (1 + np.random.uniform(0, 0.03, len(closes)))
        lows = closes * (1 - np.random.uniform(0, 0.03, len(closes)))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]
        volumes = np.random.uniform(1000000, 10000000, len(closes))
        
        mock_data = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes,
            'MA_5': pd.Series(closes).rolling(5).mean(),
            'MA_20': pd.Series(closes).rolling(20).mean(),
            'MA_50': pd.Series(closes).rolling(50).mean(),
            'RSI': np.full(len(closes), rsi),
            'BB_Upper': closes * 1.1,
            'BB_Middle': closes,
            'BB_Lower': closes * 0.9
        }, index=dates)
        
        # 生成技术分析图表
        self.stock_chart_generator.create_candlestick_chart(
            mock_data, symbol, f"analytics/{symbol}_candlestick_demo.html"
        )
        self.stock_chart_generator.create_rsi_chart(
            mock_data, symbol, f"analytics/{symbol}_rsi_demo.png"
        )
        self.stock_chart_generator.create_bollinger_bands_chart(
            mock_data, symbol, f"analytics/{symbol}_bollinger_demo.html"
        )
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'trend': trend,
            'rsi': rsi,
            'rsi_signal': rsi_signal,
            'bb_position': bb_position,
            'data': mock_data
        }
    
    def _perform_financial_analysis(self, symbol: str):
        """执行财务分析"""
        try:
            if self.use_mock_data:
                # 使用模拟数据
                mock_data = self.financial_data_fetcher.generate_mock_financial_data(symbol)
                
                print(f"   💼 营收: ${mock_data['revenues'][-1]/1e9:.2f}B")
                print(f"   💹 净利润率: {mock_data['ratios']['net_profit_margin']:.2f}%")
                print(f"   🏆 ROE: {mock_data['ratios']['roe']:.2f}%")
                print(f"   💳 负债率: {mock_data['ratios']['debt_ratio']:.2f}%")
                
                # 生成财务健康评分
                health_score = self._calculate_mock_health_score(mock_data['ratios'])
                
                financial_analysis = {
                    'symbol': symbol,
                    'ratios': mock_data['ratios'],
                    'health_score': health_score,
                    'mock_data': mock_data
                }
                
                # 生成财务分析图表
                self._generate_mock_financial_charts(symbol, mock_data, health_score)
                
            else:
                # 使用真实数据
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
                    
                    # 生成财务分析图表
                    self.financial_chart_generator.create_profitability_chart(
                        financial_analysis, f"analytics/{symbol}_financial_metrics.png"
                    )
                    
                    if 'error' not in health_data:
                        self.financial_chart_generator.create_financial_health_dashboard(
                            health_data, f"analytics/{symbol}_health_dashboard.html"
                        )
            
            return financial_analysis
            
        except Exception as e:
            print(f"   ❌ 财务分析失败: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_mock_health_score(self, ratios: Dict) -> Dict:
        """计算模拟数据的健康评分"""
        health_score = 0
        
        # 净利润率评分
        net_margin = ratios.get('net_profit_margin', 0)
        if net_margin > 15:
            health_score += 30
        elif net_margin > 10:
            health_score += 20
        elif net_margin > 5:
            health_score += 10
        
        # ROE评分
        roe = ratios.get('roe', 0)
        if roe > 15:
            health_score += 25
        elif roe > 10:
            health_score += 15
        elif roe > 5:
            health_score += 10
        
        # 负债率评分
        debt_ratio = ratios.get('debt_ratio', 100)
        if debt_ratio < 30:
            health_score += 25
        elif debt_ratio < 50:
            health_score += 15
        elif debt_ratio < 70:
            health_score += 10
        
        # 流动比率评分
        current_ratio = ratios.get('current_ratio', 0)
        if current_ratio > 2:
            health_score += 10
        elif current_ratio > 1.5:
            health_score += 8
        elif current_ratio > 1:
            health_score += 5
        
        # 估值评分
        pe_ratio = ratios.get('pe_ratio', 0)
        if 0 < pe_ratio < 15:
            health_score += 10
        elif 15 <= pe_ratio < 25:
            health_score += 8
        elif 25 <= pe_ratio < 35:
            health_score += 5
        
        # 确定等级
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
            'health_score': health_score,
            'max_score': 100,
            'grade': grade
        }
    
    def _generate_mock_financial_charts(self, symbol: str, mock_data: Dict, health_score: Dict):
        """生成模拟财务图表"""
        try:
            import matplotlib.pyplot as plt
            import plotly.graph_objects as go
            
            # 1. 营收趋势图
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=mock_data['years'],
                y=[rev/1e9 for rev in mock_data['revenues']],
                mode='lines+markers',
                name='营收',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title=f'{symbol} 营收趋势 (演示数据)',
                xaxis_title='年份',
                yaxis_title='营收 (十亿美元)',
                template='plotly_white'
            )
            fig.write_html(f"analytics/{symbol}_revenue_trend_demo.html")
            
            # 2. 财务指标图表
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'{symbol} 财务指标分析 (演示数据)', fontsize=16)
            
            ratios = mock_data['ratios']
            
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
            
            # 负债结构
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
            
            # 流动性指标
            current_ratio = ratios.get('current_ratio', 0)
            ax4.bar(['流动比率'], [current_ratio], color='lightblue', width=0.5)
            ax4.axhline(y=1, color='r', linestyle='--', alpha=0.7, label='安全线')
            ax4.set_title('流动性指标')
            ax4.set_ylabel('倍数')
            ax4.legend()
            
            plt.tight_layout()
            plt.savefig(f"analytics/{symbol}_financial_metrics_demo.png", dpi=300, bbox_inches='tight')
            plt.close()
            
            # 3. 健康评分仪表盘
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="gauge+number+delta",
                value=health_score['health_score'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"{symbol} 财务健康评分 (演示数据)"},
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
                title=f'财务健康等级: {health_score["grade"]}',
                height=400
            )
            fig.write_html(f"analytics/{symbol}_health_dashboard_demo.html")
            
        except Exception as e:
            print(f"生成模拟财务图表时出错: {str(e)}")
    
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
            
            # 财务面评分
            finance_score = 0
            if 'error' not in financial_analysis:
                if self.use_mock_data:
                    health_data = financial_analysis.get('health_score', {})
                else:
                    health_data = financial_analysis.get('health_data', {})
                
                if health_data:
                    finance_score = health_data.get('health_score', 0)
                    
                    if finance_score >= 80:
                        report['key_strengths'].append('财务状况优秀')
                    elif finance_score >= 60:
                        report['key_strengths'].append('财务状况良好')
                    elif finance_score < 40:
                        report['key_concerns'].append('财务状况需要关注')
            
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
            data_type = "演示数据" if self.use_mock_data else "真实数据"
            report['summary'] = f"""
基于{data_type}的综合分析，{symbol}获得{report['overall_rating']}评级。
技术分析显示{technical_analysis.get('trend', '趋势不明')}，
财务分析显示{'良好的' if finance_score >= 60 else '一般的' if finance_score >= 40 else '较差的'}财务状况。
投资建议：{report['investment_recommendation']}。
            """.strip()
            
        except Exception as e:
            report['summary'] = f"生成报告时出错: {str(e)}"
        
        return report

if __name__ == "__main__":
    # 综合分析示例
    print("=== 综合股票分析系统 ===")
    
    # 使用演示数据进行测试
    analyzer = ComprehensiveStockAnalyzer(use_mock_data=True)
    
    symbols = ["AAPL", "GOOGL", "LULU]
    
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
