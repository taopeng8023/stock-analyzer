#!/usr/bin/env python3
"""
模型训练模块
使用历史数据训练 XGBoost 模型
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from xgboost import XGBClassifier
import joblib
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from config.loader import Config


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, config: Config = None):
        """
        初始化模型训练器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.train_window = int(self.config.get('MODEL', 'train_window'))
        self.predict_horizon = int(self.config.get('MODEL', 'predict_horizon'))
        self.model = None
        self.feature_columns = None
    
    def prepare_training_data(self, stock_codes: List[str], 
                              price_data: Dict,
                              feature_data: Dict) -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备训练数据
        
        Args:
            stock_codes: 股票代码列表
            price_data: 价格数据 Dict
            feature_data: 特征数据 Dict
        
        Returns:
            (X, y) 特征矩阵和标签
        """
        X_list = []
        y_list = []
        
        for code in stock_codes:
            if code not in price_data or code not in feature_data:
                continue
            
            prices = price_data[code].copy()
            features = feature_data[code].copy()
            
            if len(prices) < self.train_window + self.predict_horizon:
                continue
            
            # 创建标签：未来 N 天收益率
            for i in range(len(prices) - self.predict_horizon):
                current_price = prices['close'].iloc[i]
                future_price = prices['close'].iloc[i + self.predict_horizon]
                return_n = (future_price - current_price) / current_price
                
                # 上涨为 1，下跌为 0
                label = 1 if return_n > 0 else 0
                
                # 获取当日特征
                if i < len(features):
                    feature_row = features.iloc[i].copy()
                    feature_row['label'] = label
                    X_list.append(feature_row)
        
        if not X_list:
            return pd.DataFrame(), pd.Series()
        
        X_df = pd.DataFrame(X_list)
        y = X_df.pop('label')
        
        return X_df, y
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
        """
        训练模型
        
        Args:
            X: 特征矩阵
            y: 标签
        
        Returns:
            训练好的模型
        """
        print(f"[模型训练] 样本数：{len(X)}, 特征数：{len(X.columns)}")
        
        # 处理缺失值
        X = X.fillna(X.median())
        
        # 时间序列交叉验证
        tscv = TimeSeriesSplit(n_splits=5)
        
        # XGBoost 模型
        model = XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False,
        )
        
        # 交叉验证
        print("[模型训练] 进行时间序列交叉验证...")
        scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy')
        print(f"[模型训练] 交叉验证准确率：{scores.mean():.2%} (+/- {scores.std()*2:.2%})")
        
        # 全量训练
        print("[模型训练] 全量训练...")
        model.fit(X, y)
        
        # 特征重要性
        importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\n[模型训练] Top 10 重要特征:")
        print(importance.head(10))
        
        self.model = model
        self.feature_columns = X.columns.tolist()
        
        return model
    
    def save_model(self, filepath: str = None) -> str:
        """
        保存模型
        
        Args:
            filepath: 文件路径
        
        Returns:
            保存的文件路径
        """
        if filepath is None:
            filepath = Path(__file__).parent.parent / 'models' / 'xgb_model.pkl'
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(self.model, filepath)
        
        # 保存特征列
        feature_file = filepath.with_suffix('.features.json')
        import json
        with open(feature_file, 'w') as f:
            json.dump(self.feature_columns, f)
        
        print(f"[模型训练] 模型已保存：{filepath}")
        
        return str(filepath)
    
    def load_model(self, filepath: str = None) -> XGBClassifier:
        """
        加载模型
        
        Args:
            filepath: 文件路径
        
        Returns:
            加载的模型
        """
        if filepath is None:
            filepath = Path(__file__).parent.parent / 'models' / 'xgb_model.pkl'
        
        self.model = joblib.load(filepath)
        
        # 加载特征列
        feature_file = filepath.with_suffix('.features.json')
        if feature_file.exists():
            import json
            with open(feature_file, 'r') as f:
                self.feature_columns = json.load(f)
        
        print(f"[模型训练] 模型已加载：{filepath}")
        
        return self.model
    
    def run(self, stock_codes: List[str], price_data: Dict, 
            feature_data: Dict, save: bool = True) -> Dict:
        """
        运行完整训练流程
        
        Args:
            stock_codes: 股票代码列表
            price_data: 价格数据 Dict
            feature_data: 特征数据 Dict
            save: 是否保存模型
        
        Returns:
            训练结果 Dict
        """
        print("="*60)
        print("🤖 模型训练")
        print("="*60)
        
        # 准备训练数据
        X, y = self.prepare_training_data(stock_codes, price_data, feature_data)
        
        if len(X) == 0:
            return {'status': 'error', 'message': '无有效训练数据'}
        
        # 训练模型
        model = self.train(X, y)
        
        # 保存模型
        if save:
            self.save_model()
        
        # 评估
        from sklearn.metrics import accuracy_score, classification_report
        
        y_pred = model.predict(X)
        accuracy = accuracy_score(y, y_pred)
        
        print(f"\n[模型训练] 训练集准确率：{accuracy:.2%}")
        
        return {
            'status': 'success',
            'n_samples': len(X),
            'n_features': len(X.columns),
            'accuracy': accuracy,
            'model': model,
            'feature_columns': self.feature_columns,
        }


# 测试
if __name__ == '__main__':
    config = Config()
    trainer = ModelTrainer(config)
    
    # 创建模拟数据
    stock_codes = ['600519', '000858', '600036']
    
    price_data = {}
    feature_data = {}
    
    for code in stock_codes:
        # 模拟价格数据
        dates = pd.date_range(end=datetime.now(), periods=300, freq='B')
        price_data[code] = pd.DataFrame({
            'close': np.random.uniform(50, 200, len(dates)),
        }, index=dates)
        
        # 模拟特征数据
        feature_data[code] = pd.DataFrame({
            'pe_ttm': np.random.uniform(10, 50, len(dates)),
            'pb': np.random.uniform(1, 10, len(dates)),
            'ma5_ma20_ratio': np.random.uniform(0.9, 1.1, len(dates)),
            'rsi_14': np.random.uniform(30, 70, len(dates)),
        }, index=dates)
    
    # 训练模型
    result = trainer.run(stock_codes, price_data, feature_data)
    
    print("\n" + "="*60)
    print("📊 训练结果")
    print("="*60)
    print(f"状态：{result['status']}")
    print(f"样本数：{result['n_samples']}")
    print(f"特征数：{result['n_features']}")
    print(f"准确率：{result['accuracy']:.2%}")
