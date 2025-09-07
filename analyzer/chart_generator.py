#!/usr/bin/env python3
"""
独立图表生成模块
统一管理所有可视化逻辑，支持技术分析和财务分析图表
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
from .config import get_config
import os


class BaseChartGenerator(ABC):
    """图表生成器抽象基类"""
    
    def __init__(self):
        self.config = get_config()
        self._setup_matplotlib_style()
    
    def _setup_matplotlib_style(self):
        """设置matplotlib样式"""
        try:
            plt.style.use(self.config.chart.plt_style)
        except:
            try:
                plt.style.use(self.config.chart.plt_fallback_style)
            except:
                pass
    
    def _ensure_output_dir(self, save_path: str):
        """确保输出目录存在"""
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    @abstractmethod
    def create_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建图表的抽象方法"""
        pass


class CandlestickChartGenerator(BaseChartGenerator):
    """K线图生成器"""
    
    def create_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建K线图"""
        fig = go.Figure(data=go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name=symbol
        ))
        
        # 添加移动平均线
        for window in self.config.technical.ma_windows:
            ma_col = f'MA_{window}'
            if ma_col in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data[ma_col],
                    mode='lines',
                    name=f'MA{window}',
                    line=dict(width=1)
                ))
        
        fig.update_layout(
            title=f'{symbol} K线图',
            yaxis_title='价格',
            xaxis_title='日期',
            template='plotly_white'
        )
        
        if save_path:
            self._ensure_output_dir(save_path)
            fig.write_html(save_path)
        else:
            fig.show()


class RSIChartGenerator(BaseChartGenerator):
    """RSI指标图生成器"""
    
    def create_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建RSI指标图"""
        fig, (ax1, ax2) = plt.subplots(2, 1, 
                                      figsize=self.config.chart.rsi_figsize, 
                                      height_ratios=self.config.chart.candlestick_height_ratios)
        
        # 价格图
        ax1.plot(data.index, data['Close'], label='收盘价', linewidth=1)
        ax1.set_title(f'{symbol} 股价和RSI指标')
        ax1.set_ylabel('价格')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # RSI图
        ax2.plot(data.index, data['RSI'], 
                label='RSI', 
                color=self.config.chart.colors['secondary'], 
                linewidth=1)
        
        # 超买超卖线
        ax2.axhline(y=self.config.technical.rsi_overbought, 
                   color=self.config.chart.rsi_overbought_color, 
                   linestyle='--', 
                   alpha=self.config.chart.rsi_line_alpha, 
                   label=f'超买线({self.config.technical.rsi_overbought})')
        ax2.axhline(y=self.config.technical.rsi_oversold, 
                   color=self.config.chart.rsi_oversold_color, 
                   linestyle='--', 
                   alpha=self.config.chart.rsi_line_alpha, 
                   label=f'超卖线({self.config.technical.rsi_oversold})')
        
        # 填充中性区域
        ax2.fill_between(data.index, 
                        self.config.technical.rsi_oversold, 
                        self.config.technical.rsi_overbought, 
                        alpha=self.config.chart.rsi_neutral_alpha, 
                        color=self.config.chart.colors['neutral_color'])
        
        ax2.set_ylabel('RSI')
        ax2.set_xlabel('日期')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            self._ensure_output_dir(save_path)
            plt.savefig(save_path, dpi=self.config.chart.save_dpi, bbox_inches='tight')
            plt.close()
        else:
            plt.show()


class BollingerBandsChartGenerator(BaseChartGenerator):
    """布林带图生成器"""
    
    def create_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建布林带图"""
        fig = go.Figure()
        
        # 布林带上轨
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Upper'],
            name='布林带上轨',
            line=dict(color='red', width=1)
        ))
        
        # 布林带下轨
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Lower'],
            name='布林带下轨',
            line=dict(color='red', width=1),
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.1)'
        ))
        
        # 中轨（移动平均线）
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['BB_Middle'],
            name='中轨(MA)',
            line=dict(color='blue', width=1)
        ))
        
        # 收盘价
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Close'],
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
            self._ensure_output_dir(save_path)
            fig.write_html(save_path)
        else:
            fig.show()


class FinancialMetricsChartGenerator(BaseChartGenerator):
    """财务指标图生成器"""
    
    def create_profitability_chart(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建盈利能力分析图"""
        try:
            ratios = analysis_data.get('ratios', {})
            if not ratios:
                return
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, 
                                                        figsize=self.config.chart.financial_figsize)
            
            # ROE趋势
            if 'roe_history' in ratios:
                ax1.bar(range(len(ratios['roe_history'])), ratios['roe_history'])
                ax1.set_title('ROE趋势')
                ax1.set_ylabel('ROE (%)')
                ax1.grid(True, alpha=0.3)
            
            # 毛利率趋势
            if 'gross_margin_history' in ratios:
                ax2.bar(range(len(ratios['gross_margin_history'])), ratios['gross_margin_history'])
                ax2.set_title('毛利率趋势')
                ax2.set_ylabel('毛利率 (%)')
                ax2.grid(True, alpha=0.3)
            
            # 净利率趋势
            if 'net_margin_history' in ratios:
                ax3.bar(range(len(ratios['net_margin_history'])), ratios['net_margin_history'])
                ax3.set_title('净利率趋势')
                ax3.set_ylabel('净利率 (%)')
                ax3.grid(True, alpha=0.3)
            
            # ROA趋势
            if 'roa_history' in ratios:
                ax4.bar(range(len(ratios['roa_history'])), ratios['roa_history'])
                ax4.set_title('ROA趋势')
                ax4.set_ylabel('ROA (%)')
                ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                self._ensure_output_dir(save_path)
                plt.savefig(save_path, dpi=self.config.chart.save_dpi, bbox_inches='tight')
                plt.close()
            else:
                plt.show()
                
        except Exception as e:
            print(f"创建盈利能力图表时出错: {str(e)}")
    
    def create_revenue_trend_chart(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建营收趋势图"""
        try:
            income_stmt = analysis_data.get('income_statement')
            if income_stmt is None or income_stmt.empty:
                print("无营收数据可显示")
                return
            
            # 提取营收数据
            revenue_row = None
            for idx in income_stmt.index:
                if any(keyword in str(idx).lower() for keyword in ['revenue', 'total revenue', '营业收入', '总收入']):
                    revenue_row = income_stmt.loc[idx]
                    break
            
            if revenue_row is None:
                print("未找到营收数据")
                return
            
            # 创建图表
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=revenue_row.index,
                y=revenue_row.values / 1e9,  # 转换为十亿单位
                mode='lines+markers',
                name='营收',
                line=dict(color=self.config.chart.colors['primary'], width=3),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title='营收趋势分析',
                xaxis_title='年度',
                yaxis_title='营收 (十亿)',
                template='plotly_white'
            )
            
            if save_path:
                self._ensure_output_dir(save_path)
                fig.write_html(save_path)
            else:
                fig.show()
                
        except Exception as e:
            print(f"创建营收趋势图时出错: {str(e)}")
    
    def create_health_dashboard(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建财务健康度仪表盘"""
        try:
            health_score = analysis_data.get('health_score', 0)
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=health_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "财务健康度"},
                delta={'reference': self.config.financial.excellent_score},
                gauge={'axis': {'range': [None, 100]},
                      'bar': {'color': "darkblue"},
                      'steps': [
                          {'range': [0, self.config.financial.good_score], 'color': "lightgray"},
                          {'range': [self.config.financial.good_score, self.config.financial.excellent_score], 'color': "lightgreen"},
                          {'range': [self.config.financial.excellent_score, 100], 'color': "green"}
                      ],
                      'threshold': {'line': {'color': "red", 'width': 4},
                                   'thickness': 0.75, 'value': 90}}))
            
            if save_path:
                self._ensure_output_dir(save_path)
                fig.write_html(save_path)
            else:
                fig.show()
                
        except Exception as e:
            print(f"创建财务健康度仪表盘时出错: {str(e)}")


class UnifiedChartGenerator:
    """统一图表生成器 - 整合所有图表类型"""
    
    def __init__(self):
        self.candlestick_generator = CandlestickChartGenerator()
        self.rsi_generator = RSIChartGenerator()
        self.bollinger_generator = BollingerBandsChartGenerator()
        self.financial_generator = FinancialMetricsChartGenerator()
    
    # 技术分析图表
    def create_candlestick_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建K线图"""
        return self.candlestick_generator.create_chart(data, symbol, save_path)
    
    def create_rsi_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建RSI指标图"""
        return self.rsi_generator.create_chart(data, symbol, save_path)
    
    def create_bollinger_bands_chart(self, data: pd.DataFrame, symbol: str, save_path: Optional[str] = None):
        """创建布林带图"""
        return self.bollinger_generator.create_chart(data, symbol, save_path)
    
    # 财务分析图表
    def create_revenue_trend_chart(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建营收趋势图"""
        return self.financial_generator.create_revenue_trend_chart(analysis_data, save_path)
    
    def create_profitability_chart(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建盈利能力分析图"""
        return self.financial_generator.create_profitability_chart(analysis_data, save_path)
    
    def create_health_dashboard(self, analysis_data: Dict, save_path: Optional[str] = None):
        """创建财务健康度仪表盘"""
        return self.financial_generator.create_health_dashboard(analysis_data, save_path)


# 创建全局图表生成器实例
default_chart_generator = UnifiedChartGenerator()


def get_chart_generator() -> UnifiedChartGenerator:
    """获取默认的图表生成器实例"""
    return default_chart_generator