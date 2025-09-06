import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional

class MockStockDataFetcher:
    def __init__(self):
        pass
    
    def generate_mock_data(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """Generate mock stock data for demonstration"""
        np.random.seed(hash(symbol) % 2**32)  # Consistent data for same symbol
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             end=datetime.now(), freq='D')
        
        # Generate realistic price movement
        initial_price = np.random.uniform(50, 300)
        returns = np.random.normal(0.001, 0.02, len(dates))  # Daily returns
        prices = [initial_price]
        
        for r in returns[1:]:
            prices.append(prices[-1] * (1 + r))
        
        # Generate OHLCV data
        closes = np.array(prices)
        highs = closes * (1 + np.random.uniform(0, 0.03, len(closes)))
        lows = closes * (1 - np.random.uniform(0, 0.03, len(closes)))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]
        volumes = np.random.uniform(1000000, 10000000, len(closes))
        
        data = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=dates)
        
        return data
    
    def get_real_time_data(self, symbol: str) -> Dict:
        try:
            data = self.generate_mock_data(symbol, days=2)
            if not data.empty:
                current_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
                change = current_price - prev_price
                change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
                
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': data['Volume'].iloc[-1],
                    'timestamp': data.index[-1]
                }
            else:
                return {'error': f'无法获取 {symbol} 的实时数据'}
        except Exception as e:
            return {'error': f'获取实时数据时出错: {str(e)}'}
    
    def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        try:
            # Map period to days
            period_days = {
                "1d": 1,
                "5d": 5,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730
            }
            days = period_days.get(period, 365)
            
            return self.generate_mock_data(symbol, days)
        except Exception as e:
            print(f"获取历史数据时出错: {str(e)}")
            return pd.DataFrame()

class StockAnalyzer:
    def __init__(self, data_fetcher):
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
    
    def analyze_stock(self, symbol: str, period: str = "1y") -> Dict:
        data = self.data_fetcher.get_historical_data(symbol, period)
        if data.empty:
            return {'error': f'无法获取 {symbol} 的数据'}
        
        data = self.calculate_moving_averages(data)
        data = self.calculate_rsi(data)
        data = self.calculate_bollinger_bands(data)
        
        latest_data = data.iloc[-1]
        
        analysis = {
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
            analysis['trend'] = '上升趋势'
        else:
            analysis['trend'] = '下降趋势'
        
        if latest_data['RSI'] > 70:
            analysis['rsi_signal'] = '超买'
        elif latest_data['RSI'] < 30:
            analysis['rsi_signal'] = '超卖'
        else:
            analysis['rsi_signal'] = '中性'
        
        return analysis

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
            title=f'{symbol} 股价走势图 (演示数据)',
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
        ax1.set_title(f'{symbol} 股价和RSI指标 (演示数据)')
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
            title=f'{symbol} 布林带指标 (演示数据)',
            yaxis_title='价格',
            xaxis_title='日期',
            template='plotly_white'
        )
        
        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()

class MockStockAnalysisApp:
    def __init__(self):
        self.data_fetcher = MockStockDataFetcher()
        self.analyzer = StockAnalyzer(self.data_fetcher)
        self.chart_generator = ChartGenerator()
    
    def run_analysis(self, symbols: List[str], period: str = "1y"):
        results = {}
        
        for i, symbol in enumerate(symbols):
            print(f"\n分析股票: {symbol} ({i+1}/{len(symbols)}) - 使用演示数据")
            
            real_time = self.data_fetcher.get_real_time_data(symbol)
            if 'error' not in real_time:
                print(f"模拟实时价格: ${real_time['current_price']:.2f}")
                print(f"模拟涨跌: {real_time['change']:+.2f} ({real_time['change_percent']:+.2f}%)")
            else:
                print(f"实时数据获取失败: {real_time['error']}")
            
            analysis = self.analyzer.analyze_stock(symbol, period)
            if 'error' not in analysis:
                print(f"趋势: {analysis['trend']}")
                print(f"RSI: {analysis['rsi']:.2f} ({analysis['rsi_signal']})")
                print(f"布林带位置: {analysis['bb_position']:.2f}")
                
                try:
                    import os
                    os.makedirs('analytics', exist_ok=True)
                    
                    self.chart_generator.create_candlestick_chart(
                        analysis['data'], symbol, f"analytics/{symbol}_candlestick_demo.html"
                    )
                    self.chart_generator.create_rsi_chart(
                        analysis['data'], symbol, f"analytics/{symbol}_rsi_demo.png"
                    )
                    self.chart_generator.create_bollinger_bands_chart(
                        analysis['data'], symbol, f"analytics/{symbol}_bollinger_demo.html"
                    )
                    print(f"演示图表已生成: analytics/{symbol}_candlestick_demo.html, analytics/{symbol}_rsi_demo.png, analytics/{symbol}_bollinger_demo.html")
                except Exception as e:
                    print(f"图表生成失败: {str(e)}")
                
                results[symbol] = analysis
            else:
                print(f"分析失败: {analysis['error']}")
                results[symbol] = analysis
        
        return results

if __name__ == "__main__":
    print("股票分析程序启动... (使用演示数据)")
    print("注意: 由于网络连接问题，程序使用模拟数据进行演示")
    
    app = MockStockAnalysisApp()
    
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    
    print(f"分析股票: {', '.join(symbols)}")
    
    results = app.run_analysis(symbols, period="6mo")
    
    print("\n演示分析完成！图表已保存到当前目录。")
    print("实际使用时，请确保网络连接正常以获取真实数据。")