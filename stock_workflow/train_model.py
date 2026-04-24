#!/usr/bin/env python3
"""
模型训练脚本 - 使用真实历史数据训练 XGBoost 模型
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import joblib

# 添加模块路径
sys.path.append(str(Path(__file__).parent))

from config.loader import Config
from modules.real_data_fetcher import RealDataFetcher
from modules.fundamental import FundamentalAnalyzer
from modules.technical import TechnicalAnalyzer
from modules.news_sentiment import NewsSentimentAnalyzer
from modules.decision_fusion import DecisionFusion


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, config: Config = None):
        """
        初始化训练器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.data_fetcher = RealDataFetcher(config)
        self.fundamental = FundamentalAnalyzer(config)
        self.technical = TechnicalAnalyzer(config)
        self.news = NewsSentimentAnalyzer(config)
        self.decision = DecisionFusion(config)
        
        self.train_window = int(self.config.get('MODEL', 'train_window'))
        self.predict_horizon = int(self.config.get('MODEL', 'predict_horizon'))
    
    def prepare_training_data(self, stock_codes: list, price_data: dict) -> tuple:
        """
        准备训练数据
        
        Args:
            stock_codes: 股票代码列表
            price_data: 价格数据 Dict
        
        Returns:
            (X, y) 特征矩阵和标签
        """
        # 获取各模块特征
        fundamental_result = self.fundamental.run(stock_codes)
        technical_result = self.technical.run(stock_codes)
        news_result = self.news.run(stock_codes)
        
        features_dict = {
            'fundamental': fundamental_result['features'],
            'technical': technical_result['features'],
            'news': news_result['features'],
        }
        
        # 准备特征矩阵
        features = self.decision.prepare_features(features_dict)
        
        # 创建标签
        labels = self.decision.create_labels(price_data, stock_codes)
        
        # 合并特征和标签
        merged = features.merge(labels, on='code', how='inner')
        
        # 准备训练数据
        X = merged.drop(['code', 'label', 'return_3d'], axis=1, errors='ignore')
        y = merged['label']
        
        return X, y, features.columns.tolist()
    
    def train(self, sample_stocks: list = None, days: int = 300):
        """
        训练模型
        
        Args:
            sample_stocks: 样本股票列表（用于训练）
            days: 历史数据天数
        
        Returns:
            训练结果 Dict
        """
        print("="*60)
        print("🤖 模型训练")
        print("="*60)
        
        # 样本股票（主板代表性股票）
        if sample_stocks is None:
            sample_stocks = [
                '600519', '000858', '600036', '000002', '000651',  # 茅台、五粮液、招行、万科、格力
                '601318', '600276', '601398', '601288', '600030',  # 平安、恒瑞、工行、农行、中信
                '000001', '000063', '000100', '000333', '000538',  # 平安、中兴、TCL、美的、云南白药
                '600585', '600887', '601888', '600031', '601166',  # 海螺、伊利、中免、三一、兴业
            ]
        
        print(f"\n[训练] 样本股票数：{len(sample_stocks)}")
        print(f"[训练] 历史数据天数：{days}")
        
        # 获取历史价格数据
        print("\n[数据] 获取历史价格数据...")
        price_data = {}
        for code in sample_stocks:
            try:
                df = self.data_fetcher.fetch_price_history(code, days=days)
                if df is not None and len(df) > self.train_window:
                    price_data[code] = df
                    print(f"  ✓ {code}: {len(df)} 天")
            except Exception as e:
                print(f"  ✗ {code}: {e}")
        
        if not price_data:
            print("\n❌ 无法获取历史数据，使用模拟数据训练")
            # 使用模拟数据
            for code in sample_stocks[:10]:
                dates = pd.date_range(end=datetime.now(), periods=days)
                price_data[code] = pd.DataFrame({
                    'date': dates,
                    'close': np.random.uniform(10, 100, days),
                    'volume': np.random.randint(1000, 10000, days),
                })
        
        print(f"\n[数据] 有效数据：{len(price_data)} 只股票")
        
        # 准备训练数据
        print("\n[特征] 准备训练数据...")
        X, y, feature_columns = self.prepare_training_data(sample_stocks, price_data)
        
        print(f"[特征] 特征矩阵：{X.shape}")
        print(f"[特征] 特征列：{len(feature_columns)}")
        
        # 训练模型
        print("\n[训练] 训练 XGBoost 模型...")
        self.decision.feature_columns = feature_columns
        model = self.decision.train_model(X, y)
        
        # 保存模型
        model_dir = Path(__file__).parent / 'models'
        model_dir.mkdir(exist_ok=True)
        model_path = model_dir / 'xgb_model.pkl'
        
        joblib.dump(model, model_path)
        print(f"\n✅ 模型已保存：{model_path}")
        
        # 模型评估
        print("\n" + "="*60)
        print("📊 模型评估")
        print("="*60)
        
        # 训练集准确率
        train_pred = model.predict(X)
        train_acc = (train_pred == y).mean()
        print(f"训练集准确率：{train_acc:.2%}")
        
        # 特征重要性
        print("\nTop 10 重要特征:")
        importances = model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': X.columns.tolist(),
            'importance': importances,
        }).sort_values('importance', ascending=False)
        
        for i, row in feature_importance.head(10).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
        
        return {
            'model_path': str(model_path),
            'n_samples': len(X),
            'n_features': len(feature_columns),
            'train_accuracy': train_acc,
            'feature_importance': feature_importance.head(10).to_dict('records'),
        }


# 主程序
if __name__ == '__main__':
    config = Config()
    trainer = ModelTrainer(config)
    
    result = trainer.train()
    
    print("\n" + "="*60)
    print("✅ 训练完成")
    print("="*60)
    print(f"模型路径：{result['model_path']}")
    print(f"样本数：{result['n_samples']}")
    print(f"特征数：{result['n_features']}")
    print(f"训练准确率：{result['train_accuracy']:.2%}")
