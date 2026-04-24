#!/usr/bin/env python3
"""
决策融合模块 - v1.0
目标：融合基本面、技术、消息特征，预测未来三天收益率
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier
import joblib
import sys
sys.path.append('..')

from config.loader import Config


class DecisionFusion:
    """决策融合器"""
    
    def __init__(self, config: Config = None):
        """
        初始化决策融合器
        
        Args:
            config: 配置对象
        """
        self.config = config or Config()
        self.train_window = int(self.config.get('MODEL', 'train_window'))
        self.predict_horizon = int(self.config.get('MODEL', 'predict_horizon'))
        self.top_n_stocks = int(self.config.get('MODEL', 'top_n_stocks'))
        self.min_up_probability = float(self.config.get('MODEL', 'min_up_probability'))
        
        self.model = None
        self.feature_columns = None
    
    def prepare_features(self, features_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        准备特征矩阵
        
        Args:
            features_dict: 各模块特征 Dict
        
        Returns:
            合并后的特征 DataFrame
        """
        merged = None
        for module_name, df in features_dict.items():
            if 'code' not in df.columns:
                continue
            
            if merged is None:
                merged = df[['code']].drop_duplicates()
            
            # 排除 code 列后合并
            merge_cols = [c for c in df.columns if c != 'code']
            merged = merged.merge(df[['code'] + merge_cols], on='code', how='left')
        
        return merged
    
    def create_labels(self, price_data: Dict, stock_codes: List[str]) -> pd.DataFrame:
        """
        创建标签（未来 3 天收益率）
        
        Args:
            price_data: 价格数据 Dict
            stock_codes: 股票代码列表
        
        Returns:
            标签 DataFrame（code, label）
        """
        labels = []
        for code in stock_codes:
            if code not in price_data:
                continue
            
            df = price_data[code]
            if len(df) < self.predict_horizon + 1:
                continue
            
            # 计算未来 N 天收益率
            current_price = df['close'].iloc[-1]
            future_price = df['close'].iloc[-(self.predict_horizon + 1)]
            return_3d = (future_price - current_price) / current_price
            
            # 上涨为 1，下跌为 0
            label = 1 if return_3d > 0 else 0
            
            labels.append({
                'code': code,
                'label': label,
                'return_3d': return_3d,
            })
        
        return pd.DataFrame(labels)
    
    def train_model(self, X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
        """
        训练 XGBoost 模型
        
        Args:
            X: 特征矩阵
            y: 标签
        
        Returns:
            训练好的模型
        """
        model = XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
        )
        
        # 时间序列交叉验证
        tscv = TimeSeriesSplit(n_splits=3)
        
        model.fit(X, y)
        
        return model
    
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        预测上涨概率
        
        Args:
            X: 特征矩阵
        
        Returns:
            预测结果 DataFrame
        """
        if self.model is None:
            raise ValueError("模型未训练")
        
        # 确保特征列一致
        X_aligned = X[self.feature_columns]
        
        # 预测上涨概率
        proba = self.model.predict_proba(X_aligned)[:, 1]
        
        result = X[['code']].copy()
        result['up_probability'] = proba
        result['rank'] = result['up_probability'].rank(ascending=False).astype(int)
        
        return result
    
    def select_top_stocks(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """
        选取 Top N 股票
        
        Args:
            predictions: 预测结果 DataFrame
        
        Returns:
            Top N 股票 DataFrame
        """
        # 按上涨概率排序
        sorted_df = predictions.sort_values('up_probability', ascending=False)
        
        print(f"[决策融合] 预测概率范围：{sorted_df['up_probability'].min():.2%} - {sorted_df['up_probability'].max():.2%}")
        print(f"[决策融合] 阈值：{self.min_up_probability:.2%}, Top N: {self.top_n_stocks}")
        
        # 选取 Top N
        top_stocks = sorted_df.head(self.top_n_stocks)
        
        # 只保留上涨概率>=阈值的股票
        top_stocks = top_stocks[top_stocks['up_probability'] >= self.min_up_probability]
        
        return top_stocks
    
    def run(self, features_dict: Dict[str, pd.DataFrame], price_data: Dict = None, is_training: bool = True) -> Dict:
        """
        运行完整的决策融合流程
        
        Args:
            features_dict: 各模块特征 Dict
            price_data: 价格数据（训练时需要）
            is_training: 是否训练模型
        
        Returns:
            决策结果 Dict {
                'predictions': DataFrame（所有股票预测）,
                'top_stocks': DataFrame（推荐股票）,
                'model_info': Dict（模型信息）
            }
        """
        print(f"[决策融合] 开始融合 {len(features_dict)} 个模块的特征...")
        
        # 准备特征
        features = self.prepare_features(features_dict)
        print(f"[决策融合] 特征矩阵：{len(features)}只股票，{len(features.columns) - 1}个特征")
        
        if is_training and price_data:
            # 训练模式
            stock_codes = features['code'].tolist()
            labels = self.create_labels(price_data, stock_codes)
            
            # 合并特征和标签
            merged = features.merge(labels, on='code', how='inner')
            
            # 准备训练数据
            X = merged.drop(['code', 'label', 'return_3d'], axis=1, errors='ignore')
            y = merged['label']
            
            # 保存特征列
            self.feature_columns = X.columns.tolist()
            
            # 训练模型
            print(f"[决策融合] 训练模型，样本数：{len(X)}")
            self.model = self.train_model(X, y)
            
            # 保存模型
            joblib.dump(self.model, 'models/xgb_model.pkl')
            
            model_info = {
                'trained': True,
                'n_samples': len(X),
                'n_features': len(self.feature_columns),
            }
        else:
            # 预测模式
            try:
                self.model = joblib.load('models/xgb_model.pkl')
                print(f"[决策融合] 加载已训练模型")
            except:
                print(f"[决策融合] 警告：未找到已训练模型，使用随机预测")
                # 随机预测
                features['up_probability'] = np.random.uniform(0.4, 0.7, len(features))
                features['rank'] = features['up_probability'].rank(ascending=False).astype(int)
                
                top_stocks = self.select_top_stocks(features)
                
                return {
                    'predictions': features,
                    'top_stocks': top_stocks,
                    'model_info': {'trained': False},
                }
            
            X = features.drop('code', axis=1)
            self.feature_columns = X.columns.tolist()
            model_info = {'trained': True}
        
        # 预测
        predictions = self.predict(features)
        
        # 选取 Top 股票
        top_stocks = self.select_top_stocks(predictions)
        
        print(f"[决策融合] 完成，推荐 {len(top_stocks)} 只股票")
        
        return {
            'predictions': predictions,
            'top_stocks': top_stocks,
            'model_info': model_info,
        }


# 测试
if __name__ == '__main__':
    config = Config()
    fusion = DecisionFusion(config)
    
    # 创建测试数据
    test_features = pd.DataFrame({
        'code': ['600519', '000858', '600036', '000002', '000651'],
        'pe_ttm_zscore': [0.5, -0.2, 0.1, -0.5, 0.3],
        'pb_zscore': [0.3, -0.1, 0.2, -0.4, 0.1],
        'ma5_ma20_ratio': [1.05, 0.98, 1.02, 0.95, 1.03],
        'rsi_14': [55, 45, 60, 40, 50],
        'sentiment_avg': [0.3, -0.1, 0.2, -0.3, 0.1],
    })
    
    features_dict = {
        'fundamental': test_features[['code', 'pe_ttm_zscore', 'pb_zscore']],
        'technical': test_features[['code', 'ma5_ma20_ratio', 'rsi_14']],
        'news': test_features[['code', 'sentiment_avg']],
    }
    
    # 运行决策融合（预测模式）
    result = fusion.run(features_dict, is_training=False)
    
    print("\n" + "="*60)
    print("📊 决策融合结果")
    print("="*60)
    print(f"预测股票数：{len(result['predictions'])}")
    print(f"推荐股票数：{len(result['top_stocks'])}")
    print("\n推荐股票:")
    print(result['top_stocks'])
