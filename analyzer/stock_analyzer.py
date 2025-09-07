import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import time
from typing import Dict, List, Optional

class StockDataFetcher:
    def __init__(self):
        pass
    
    def get_real_time_data(self, symbol: str) -> Dict:
        try:
            time.sleep(1)  # Add delay to avoid rate limiting
            ticker = yf.Ticker(symbol)
            
            # Try to get current data without info first
            history = ticker.history(period="1d", interval="5m")
            
            if not history.empty:
                current_price = history['Close'].iloc[-1]
                prev_price = history['Close'].iloc[0] if len(history) > 1 else current_price
                change = current_price - prev_price
                change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
                
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': history['Volume'].iloc[-1],
                    'timestamp': history.index[-1]
                }
            else:
                return {'error': f'无法获取 {symbol} 的实时数据'}
        except Exception as e:
            return {'error': f'获取实时数据时出错: {str(e)}'}
    
    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        try:
            time.sleep(1)  # Add delay to avoid rate limiting
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            return data
        except Exception as e:
            print(f"获取历史数据时出错: {str(e)}")
            return pd.DataFrame()

class StockAnalyzer:
    def __init__(self, data_fetcher: StockDataFetcher):
        self.data_fetcher = data_fetcher
    
    def calculate_moving_averages(self, data: pd.DataFrame, windows: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
        for window in windows:
            data[f'MA_{window}'] = data['Close'].rolling(window=window).mean()
        return data
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        return data
    
    def calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        data['BB_Middle'] = data['Close'].rolling(window=period).mean()
        data['BB_Upper'] = data['BB_Middle'] + (data['Close'].rolling(window=period).std() * std_dev)
        data['BB_Lower'] = data['BB_Middle'] - (data['Close'].rolling(window=period).std() * std_dev)
        return data
    
    def check_price_drop(self, symbol: str, days: int = 1, threshold_percent: float = 15.0) -> Dict:
        """
        检查股票在指定天数内是否下跌超过阈值
        
        Args:
            symbol: 股票代码
            days: 检查的天数 (1 或 7)
            threshold_percent: 下跌阈值百分比 (默认15%)
            
        Returns:
            Dict: 包含检查结果的字典
        """
        try:
            # 获取足够的历史数据
            period = "1mo" if days <= 7 else "3mo"
            data = self.data_fetcher.get_historical_data(symbol, period=period, interval="1d")
            
            if data.empty:
                return {'error': f'无法获取 {symbol} 的历史数据'}
            
            if len(data) < days + 1:
                return {'error': f'数据不足，无法计算 {days} 天的价格变化'}
            
            # 获取当前价格和N天前的价格
            current_price = data['Close'].iloc[-1]
            past_price = data['Close'].iloc[-(days + 1)]
            
            # 计算价格变化
            price_change = current_price - past_price
            percent_change = (price_change / past_price) * 100
            
            # 判断是否触发下跌警告
            is_drop_alert = percent_change <= -threshold_percent
            
            # 获取期间的最高价和最低价
            period_high = data['Close'].iloc[-days-1:].max()
            period_low = data['Close'].iloc[-days-1:].min()
            max_drop_from_high = ((current_price - period_high) / period_high) * 100
            
            return {
                'symbol': symbol,
                'days_checked': days,
                'threshold_percent': threshold_percent,
                'current_price': current_price,
                'past_price': past_price,
                'price_change': price_change,
                'percent_change': percent_change,
                'is_drop_alert': is_drop_alert,
                'period_high': period_high,
                'period_low': period_low,
                'max_drop_from_high': max_drop_from_high,
                'alert_message': self._generate_drop_alert_message(
                    symbol, days, percent_change, threshold_percent, is_drop_alert
                )
            }
            
        except Exception as e:
            return {'error': f'检查价格下跌时出错: {str(e)}'}
    
    def _generate_drop_alert_message(self, symbol: str, days: int, percent_change: float, 
                                   threshold: float, is_alert: bool) -> str:
        """生成下跌警告消息"""
        if is_alert:
            return f"⚠️ 警告: {symbol} 在过去 {days} 天下跌了 {abs(percent_change):.2f}%，超过了 {threshold}% 的警告阈值！"
        else:
            if percent_change < 0:
                return f"📊 {symbol} 在过去 {days} 天下跌了 {abs(percent_change):.2f}%，未达到 {threshold}% 的警告阈值"
            else:
                return f"📈 {symbol} 在过去 {days} 天上涨了 {percent_change:.2f}%"
    
    def batch_check_price_drops(self, symbols: List[str], days: int = 1, 
                               threshold_percent: float = 15.0) -> Dict[str, Dict]:
        """
        批量检查多只股票的价格下跌情况
        
        Args:
            symbols: 股票代码列表
            days: 检查的天数
            threshold_percent: 下跌阈值百分比
            
        Returns:
            Dict: 每只股票的检查结果
        """
        results = {}
        alerts = []
        
        print(f"🔍 开始检查 {len(symbols)} 只股票在过去 {days} 天的价格变化...")
        print(f"📉 警告阈值: 下跌超过 {threshold_percent}%")
        print("-" * 60)
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] 检查 {symbol}...")
            
            result = self.check_price_drop(symbol, days, threshold_percent)
            results[symbol] = result
            
            if 'error' not in result:
                print(f"  {result['alert_message']}")
                
                if result['is_drop_alert']:
                    alerts.append({
                        'symbol': symbol,
                        'percent_change': result['percent_change'],
                        'current_price': result['current_price'],
                        'max_drop_from_high': result['max_drop_from_high']
                    })
            else:
                print(f"  ❌ {result['error']}")
            
            # 避免API限制
            if i < len(symbols):
                time.sleep(1)
        
        # 打印汇总
        print("\n" + "=" * 60)
        print("📊 检查结果汇总")
        print("=" * 60)
        
        if alerts:
            print(f"⚠️  发现 {len(alerts)} 只股票触发下跌警告:")
            for alert in alerts:
                print(f"  🔴 {alert['symbol']}: {alert['percent_change']:.2f}% "
                      f"(当前价格: ${alert['current_price']:.2f})")
        else:
            print("✅ 没有股票触发下跌警告")
        
        return {
            'results': results,
            'alerts': alerts,
            'summary': {
                'total_checked': len(symbols),
                'alerts_count': len(alerts),
                'threshold_used': threshold_percent,
                'days_checked': days
            }
        }
    
    def analyze_stock(self, symbol: str, period: str = "1y") -> Dict:
        data = self.data_fetcher.get_historical_data(symbol, period)
        if data.empty:
            return {'error': f'无法获取 {symbol} 的数据'}
        
        data = self.calculate_moving_averages(data)
        data = self.calculate_rsi(data)
        data = self.calculate_bollinger_bands(data)
        
        latest_data = data.iloc[-1]
        
        analysis_result = {
            'symbol': symbol,
            'current_price': latest_data['Close'],
            'ma_5': latest_data['MA_5'],
            'ma_20': latest_data['MA_20'],
            'ma_50': latest_data['MA_50'],
            'rsi': latest_data['RSI'],
            'bb_position': (latest_data['Close'] - latest_data['BB_Lower']) / (latest_data['BB_Upper'] - latest_data['BB_Lower']),
            'data': data
        }
        
        if latest_data['Close'] > latest_data['MA_20']:
            analysis_result['trend'] = '上升趋势'
        else:
            analysis_result['trend'] = '下降趋势'
        
        if latest_data['RSI'] > 70:
            analysis_result['rsi_signal'] = '超买'
        elif latest_data['RSI'] < 30:
            analysis_result['rsi_signal'] = '超卖'
        else:
            analysis_result['rsi_signal'] = '中性'
        
        return analysis_result

class ChartGenerator:
    def __init__(self):
        try:
            plt.style.use('seaborn-v0_8')
        except:
            try:
                plt.style.use('seaborn')
            except:
                pass
    
    def create_candlestick_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        fig = go.Figure(data=go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name=symbol
        ))
        
        if 'MA_5' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA_5'],
                mode='lines',
                name='MA5',
                line=dict(color='orange', width=1)
            ))
        
        if 'MA_20' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA_20'],
                mode='lines',
                name='MA20',
                line=dict(color='blue', width=1)
            ))
        
        fig.update_layout(
            title=f'{symbol} 股价走势图',
            yaxis_title='价格',
            xaxis_title='日期',
            template='plotly_white'
        )
        
        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()
    
    def create_rsi_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
        
        ax1.plot(data.index, data['Close'], label='收盘价', linewidth=1)
        ax1.set_title(f'{symbol} 股价和RSI指标')
        ax1.set_ylabel('价格')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(data.index, data['RSI'], label='RSI', color='orange', linewidth=1)
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超买线(70)')
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超卖线(30)')
        ax2.fill_between(data.index, 30, 70, alpha=0.1, color='gray')
        ax2.set_ylabel('RSI')
        ax2.set_xlabel('日期')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    
    def create_bollinger_bands_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Upper'],
            mode='lines',
            name='布林带上轨',
            line=dict(color='red', width=1),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Lower'],
            mode='lines',
            name='布林带下轨',
            line=dict(color='red', width=1),
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.1)',
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Middle'],
            mode='lines',
            name='布林带中轨(MA20)',
            line=dict(color='blue', width=1)
        ))
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Close'],
            mode='lines',
            name='收盘价',
            line=dict(color='black', width=2)
        ))
        
        fig.update_layout(
            title=f'{symbol} 布林带指标',
            yaxis_title='价格',
            xaxis_title='日期',
            template='plotly_white'
        )
        
        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()

class StockAnalysisApp:
    def __init__(self):
        self.data_fetcher = StockDataFetcher()
        self.analyzer = StockAnalyzer(self.data_fetcher)
        self.chart_generator = ChartGenerator()
    
    def run_analysis(self, symbols: List[str], period: str = "1y"):
        results = {}
        
        for i, symbol in enumerate(symbols):
            print(f"\n分析股票: {symbol} ({i+1}/{len(symbols)})")
            
            # Add delay between stocks to avoid rate limiting
            if i > 0:
                time.sleep(2)
            
            real_time = self.data_fetcher.get_real_time_data(symbol)
            if 'error' not in real_time:
                print(f"实时价格: ${real_time['current_price']:.2f}")
                print(f"涨跌: {real_time['change']:+.2f} ({real_time['change_percent']:+.2f}%)")
            else:
                print(f"实时数据获取失败: {real_time['error']}")
            
            analysis_result = self.analyzer.analyze_stock(symbol, period)
            if 'error' not in analysis_result:
                print(f"趋势: {analysis_result['trend']}")
                print(f"RSI: {analysis_result['rsi']:.2f} ({analysis_result['rsi_signal']})")
                print(f"布林带位置: {analysis_result['bb_position']:.2f}")
                
                try:
                    import os
                    os.makedirs('results', exist_ok=True)
                    
                    self.chart_generator.create_candlestick_chart(
                        analysis_result['data'], symbol, f"results/{symbol}_candlestick.html"
                    )
                    self.chart_generator.create_rsi_chart(
                        analysis_result['data'], symbol, f"results/{symbol}_rsi.png"
                    )
                    self.chart_generator.create_bollinger_bands_chart(
                        analysis_result['data'], symbol, f"results/{symbol}_bollinger.html"
                    )
                    print(f"图表已生成: results/{symbol}_candlestick.html, results/{symbol}_rsi.png, results/{symbol}_bollinger.html")
                except Exception as e:
                    print(f"图表生成失败: {str(e)}")
                
                results[symbol] = analysis_result
            else:
                print(f"分析失败: {analysis_result['error']}")
                results[symbol] = analysis_result
        
        return results

if __name__ == "__main__":
    print("=== 股票分析程序 ===")
    
    # 创建数据获取器和分析器
    data_fetcher = StockDataFetcher()
    analyzer = StockAnalyzer(data_fetcher)
    
    # 示例1: 技术分析
    print("\n1️⃣ 技术分析示例")
    print("-" * 30)
    
    app = StockAnalysisApp()
    symbols = ["AAPL", "GOOGL", "MSFT"]
    
    print("股票分析程序启动...")
    print(f"分析股票: {', '.join(symbols)}")
    
    results = app.run_analysis(symbols, period="6mo")
    print("技术分析完成！图表已保存到 results/ 目录。")
    
    # 示例2: 价格下跌检测
    print("\n2️⃣ 价格下跌检测示例")
    print("-" * 30)
    
    # 单只股票检测
    print("📊 单只股票检测:")
    result = analyzer.check_price_drop("AAPL", days=1, threshold_percent=15.0)
    if 'error' not in result:
        print(f"✅ {result['alert_message']}")
        print(f"   当前价格: ${result['current_price']:.2f}")
        print(f"   价格变化: {result['percent_change']:.2f}%")
    else:
        print(f"❌ {result['error']}")
    
    print("\n📊 批量检测示例 (检查1天价格变化):")
    watch_list = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    batch_results = analyzer.batch_check_price_drops(watch_list, days=1, threshold_percent=10.0)
    
    print("\n📊 批量检测示例 (检查7天价格变化):")
    batch_results_7d = analyzer.batch_check_price_drops(watch_list, days=7, threshold_percent=15.0)
    
    print("\n=== 使用方法说明 ===")
    print("💡 价格下跌检测功能使用方法:")
    print("   • check_price_drop(symbol, days=1, threshold_percent=15.0)")
    print("   • batch_check_price_drops(symbols, days=1, threshold_percent=15.0)")
    print("   • days: 检查天数 (1天或7天)")
    print("   • threshold_percent: 警告阈值 (默认15%)")
    print("\n📈 示例代码:")
    print("   from stock_analyzer import StockDataFetcher, StockAnalyzer")
    print("   data_fetcher = StockDataFetcher()")
    print("   analyzer = StockAnalyzer(data_fetcher)")
    print("   result = analyzer.check_price_drop('AAPL', days=1, threshold_percent=15.0)")
    print("   if result['is_drop_alert']:")
    print("       print(f'警告: {result['alert_message']}')")
