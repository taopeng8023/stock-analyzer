#!/usr/bin/env python3
"""
配置加载器
"""

import configparser
from pathlib import Path


class Config:
    """配置类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'config.ini'
        
        self.config = configparser.ConfigParser()
        
        if Path(config_path).exists():
            self.config.read(config_path, encoding='utf-8')
        else:
            # 创建默认配置
            self._create_default_config()
    
    def get(self, section: str, option: str, fallback: str = None) -> str:
        """
        获取配置项
        
        Args:
            section: 配置节
            option: 配置项
            fallback: 默认值
        
        Returns:
            配置值
        """
        try:
            return self.config.get(section, option, fallback=fallback)
        except:
            return fallback
    
    def getint(self, section: str, option: str, fallback: int = None) -> int:
        """获取整数配置项"""
        try:
            return self.config.getint(section, option, fallback=fallback)
        except:
            return fallback
    
    def getfloat(self, section: str, option: str, fallback: float = None) -> float:
        """获取浮点数配置项"""
        try:
            return self.config.getfloat(section, option, fallback=fallback)
        except:
            return fallback
    
    def getboolean(self, section: str, option: str, fallback: bool = None) -> bool:
        """获取布尔配置项"""
        try:
            return self.config.getboolean(section, option, fallback=fallback)
        except:
            return fallback
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config['STOCK_FILTER'] = {
            'main_board_prefix': '60, 00',
            'exclude_prefix': '300, 688, 8, 2, 4',
            'min_listing_days': '60',
            'min_turnover': '5000',
            'volume_amplify_ratio': '1.5',
            'volume_ma_period': '5',
        }
        
        self.config['TECHNICAL_INDICATORS'] = {
            'ma_periods': '5, 20',
            'macd_fast': '12',
            'macd_slow': '26',
            'macd_signal': '9',
            'rsi_period': '14',
            'kdj_period': '9',
            'atr_period': '14',
            'bollinger_period': '20',
            'feature_correlation_threshold': '0.15',
        }
        
        self.config['MODEL'] = {
            'model_type': 'xgboost',
            'train_window': '250',
            'predict_horizon': '3',
            'top_n_stocks': '10',
            'min_up_probability': '0.5',
        }
        
        self.config['DATA_QUALITY'] = {
            'missing_rate_threshold': '0.1',
            'outlier_quantile_low': '0.01',
            'outlier_quantile_high': '0.99',
            'abnormal_rate_threshold': '0.05',
            'quality_score_threshold': '95',
        }


# 测试
if __name__ == '__main__':
    config = Config()
    
    print("配置加载测试")
    print("="*40)
    print(f"主板前缀：{config.get('STOCK_FILTER', 'main_board_prefix')}")
    print(f"成交量放大倍数：{config.getfloat('STOCK_FILTER', 'volume_amplify_ratio')}")
    print(f"推荐股票数：{config.getint('MODEL', 'top_n_stocks')}")
