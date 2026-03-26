#!/usr/bin/env python3
"""
机器学习模型训练模块
基于历史数据训练 Random Forest / XGBoost 模型

训练流程:
1. 数据准备 - 加载历史决策 + 结果数据
2. 特征工程 - 提取 27+ 特征
3. 模型训练 - Random Forest / XGBoost
4. 模型评估 - 交叉验证 + 回测
5. 模型保存 - 保存最佳模型

用法:
    python3 ml_model_trainer.py --train              # 训练模型
    python3 ml_model_trainer.py --train --model xgb  # 训练 XGBoost
    python3 ml_model_trainer.py --eval               # 评估模型
    python3 ml_model_trainer.py --backtest           # 回测验证
"""

import sys
import json
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

# 尝试导入 ML 库
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn 未安装，使用规则加权模式")

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    print("⚠️ XGBoost 未安装，使用 Random Forest")


class MLModelTrainer:
    """
    ML 模型训练器
    
    支持:
    - Random Forest
    - XGBoost
    - Gradient Boosting
    """
    
    def __init__(self, model_dir: Path = None):
        self.model_dir = model_dir or Path(__file__).parent / 'ml_models'
        self.model_dir.mkdir(exist_ok=True)
        
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.model_type = 'rf'  # rf / xgb / gbdt
    
    def prepare_training_data(self, backtest_files: List[Path]) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据
        
        Args:
            backtest_files: 回测数据文件列表
        
        Returns:
            X: 特征矩阵 (n_samples, n_features)
            y: 标签数组 (n_samples,) 1=盈利，0=亏损
        """
        all_features = []
        all_labels = []
        
        for file_path in backtest_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            decisions = data.get('decisions', [])
            
            for decision in decisions:
                # 提取特征
                features = self._extract_decision_features(decision)
                
                # 提取标签 (是否盈利)
                final_return = decision.get('final_return', 0)
                label = 1 if final_return > 0 else 0
                
                all_features.append(features)
                all_labels.append(label)
        
        X = np.array(all_features)
        y = np.array(all_labels)
        
        print(f"✅ 加载训练数据：{len(X)} 样本，{X.shape[1]} 特征")
        print(f"   正样本 (盈利): {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
        print(f"   负样本 (亏损): {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
        
        return X, y
    
    def _extract_decision_features(self, decision: dict) -> List[float]:
        """
        从决策数据提取特征
        
        特征列表 (27+):
        1-5: 量价特征
        6-12: CAN SLIM 特征
        13-18: 趋势技术特征
        19-21: 海龟交易特征
        22-23: 波浪理论特征
        24-27: 其他特征
        """
        features = []
        
        # 基础数据
        change_pct = decision.get('change_pct', 0)
        volume = decision.get('volume', 0)
        amount = decision.get('amount', 0)
        price = decision.get('price', 0)
        
        # 1. 量价特征 (5 个)
        if change_pct > 3 and volume > 3000000:
            features.append(0.85)  # vp_score
        elif change_pct > 3:
            features.append(0.50)
        elif change_pct < -3 and volume > 3000000:
            features.append(0.20)
        elif change_pct < -3:
            features.append(0.45)
        else:
            features.append(0.55)
        
        features.append(0)  # volume_trend (需要历史数据)
        features.append(0)  # vp_divergence
        features.append(0.5)  # volume_breakout (估算)
        
        if amount > 10000000000:
            features.append(0.9)  # accumulation
        elif amount > 5000000000:
            features.append(0.7)
        elif amount > 1000000000:
            features.append(0.5)
        else:
            features.append(0.3)
        
        # 2. CAN SLIM 特征 (7 个)
        if change_pct > 10 and amount > 5000000000:
            features.extend([0.9, 0.81, 0.7, 0.8, 0.5, 0.85, 0.7])  # c,a,n,s,l,i,m
        elif change_pct > 5 and amount > 2000000000:
            features.extend([0.75, 0.675, 0.7, 0.6, 0.5, 0.65, 0.7])
        else:
            features.extend([0.55, 0.495, 0.5, 0.4, 0.5, 0.4, 0.4])
        
        canslim_total = np.mean(features[-7:])
        features.append(canslim_total)
        
        # 3. 趋势技术特征 (6 个)
        features.append(0.6 if change_pct > 0 else 0.4)  # dow_trend
        features.append(0.85 if change_pct > 5 else 0.65 if change_pct > 0 else 0.4)  # ma_score
        features.append(0.5)  # candlestick (需要 K 线)
        features.append(0.6 if change_pct > 0 else 0.4)  # macd
        features.append(0.55 + change_pct/100)  # kdj
        features.append(0.5 + change_pct/200)  # rsi
        
        trend_total = np.mean(features[-6:])
        features.append(trend_total)
        
        # 4. 海龟特征 (3 个)
        features.append(0.6 if change_pct > 0 else 0.4)  # donchian
        features.append(price * 0.03)  # atr
        features.append(0.6 if change_pct > 5 else 0.5)  # turtle_signal
        
        # 5. 波浪特征 (2 个)
        features.append(0.6)  # elliott_wave
        features.append(0.5)  # wave_position (数值化)
        
        # 6. 其他特征
        features.append(decision.get('final_score', 0) / 100)  # 原始评分
        features.append(decision.get('confidence', 45) / 100)  # 置信度
        features.append(1 if decision.get('rating') in ['强烈推荐', '推荐'] else 0)  # 评级编码
        features.append(decision.get('appear_count', 1) / 5)  # 出现次数归一化
        
        return features
    
    def train_random_forest(self, X: np.ndarray, y: np.ndarray, 
                           n_estimators: int = 100, 
                           max_depth: int = 10) -> Tuple[RandomForestClassifier, StandardScaler]:
        """
        训练 Random Forest 模型
        
        Args:
            X: 特征矩阵
            y: 标签数组
            n_estimators: 树数量
            max_depth: 最大深度
        
        Returns:
            model: 训练好的模型
            scaler: 特征缩放器
        """
        if not SKLEARN_AVAILABLE:
            print("❌ scikit-learn 未安装")
            return None, None
        
        print("\n🌲 训练 Random Forest...")
        print(f"   树数量：{n_estimators}")
        print(f"   最大深度：{max_depth}")
        
        # 特征标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 交叉验证 (简化版，避免资源泄漏)
        print("\n📊 3 折交叉验证...")
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        cv_scores = cross_val_score(
            RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=1
            ),
            X_scaled, y, cv=cv, scoring='accuracy'
        )
        
        print(f"   准确率：{cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
        
        # 训练最终模型 (单线程避免资源泄漏)
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=1
        )
        model.fit(X_scaled, y)
        
        # 特征重要性
        print("\n📈 特征重要性 Top10:")
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1][:10]
        for i in indices:
            print(f"   特征 {i}: {importances[i]:.4f}")
        
        return model, scaler
    
    def train_xgboost(self, X: np.ndarray, y: np.ndarray,
                     n_estimators: int = 100,
                     max_depth: int = 6,
                     learning_rate: float = 0.1) -> Tuple['xgb.XGBClassifier', StandardScaler]:
        """
        训练 XGBoost 模型
        """
        if not XGB_AVAILABLE:
            print("❌ XGBoost 未安装")
            return self.train_random_forest(X, y)
        
        print("\n🚀 训练 XGBoost...")
        print(f"   树数量：{n_estimators}")
        print(f"   最大深度：{max_depth}")
        print(f"   学习率：{learning_rate}")
        
        # 特征标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 交叉验证
        print("\n📊 5 折交叉验证...")
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(
            xgb.XGBClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            ),
            X_scaled, y, cv=cv, scoring='accuracy'
        )
        
        print(f"   准确率：{cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
        
        # 训练最终模型
        model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        model.fit(X_scaled, y)
        
        # 特征重要性
        print("\n📈 特征重要性 Top10:")
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1][:10]
        for i in indices:
            print(f"   特征 {i}: {importances[i]:.4f}")
        
        return model, scaler
    
    def save_model(self, model, scaler, model_type: str = 'rf'):
        """保存模型"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        model_path = self.model_dir / f'model_{model_type}_{timestamp}.pkl'
        scaler_path = self.model_dir / f'scaler_{model_type}_{timestamp}.pkl'
        config_path = self.model_dir / f'config_{model_type}_{timestamp}.json'
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        config = {
            'model_type': model_type,
            'train_date': datetime.now().isoformat(),
            'n_features': len(self.feature_names) if self.feature_names else 27,
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n💾 模型已保存:")
        print(f"   模型：{model_path}")
        print(f"   缩放器：{scaler_path}")
        print(f"   配置：{config_path}")
    
    def load_latest_model(self, model_type: str = 'rf'):
        """加载最新模型"""
        model_files = list(self.model_dir.glob(f'model_{model_type}_*.pkl'))
        
        if not model_files:
            print("⚠️ 未找到已训练的模型")
            return None, None
        
        latest = max(model_files, key=lambda f: f.stat().st_mtime)
        scaler_file = latest.parent / latest.name.replace('model_', 'scaler_')
        
        with open(latest, 'rb') as f:
            model = pickle.load(f)
        
        with open(scaler_file, 'rb') as f:
            scaler = pickle.load(f)
        
        print(f"✅ 加载模型：{latest.name}")
        
        return model, scaler
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if self.model is None:
            raise ValueError("模型未加载")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率"""
        if self.model is None:
            raise ValueError("模型未加载")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ML 模型训练模块')
    parser.add_argument('--train', action='store_true', help='训练模型')
    parser.add_argument('--model', choices=['rf', 'xgb', 'gbdt'], default='rf', help='模型类型')
    parser.add_argument('--eval', action='store_true', help='评估模型')
    parser.add_argument('--backtest', action='store_true', help='回测验证')
    parser.add_argument('--data-dir', type=str, help='回测数据目录')
    
    args = parser.parse_args()
    
    trainer = MLModelTrainer()
    
    if args.train:
        # 查找回测数据
        data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent / 'backtest_cache'
        backtest_files = list(data_dir.glob('backtest_result_*.json'))
        
        if not backtest_files:
            print("❌ 未找到回测数据文件")
            return
        
        print(f"📁 找到 {len(backtest_files)} 个回测数据文件")
        
        # 准备训练数据
        X, y = trainer.prepare_training_data(backtest_files)
        
        # 训练模型
        if args.model == 'rf':
            model, scaler = trainer.train_random_forest(X, y, n_estimators=100, max_depth=10)
        elif args.model == 'xgb':
            model, scaler = trainer.train_xgboost(X, y, n_estimators=100, max_depth=6)
        else:
            model, scaler = trainer.train_random_forest(X, y)
        
        if model is not None:
            # 保存模型
            trainer.save_model(model, scaler, args.model)
    
    elif args.eval:
        # 加载模型
        model, scaler = trainer.load_latest_model(args.model)
        
        if model is None:
            return
        
        # 评估代码...
        print("📊 模型评估功能开发中...")
    
    elif args.backtest:
        # 回测验证
        print("📈 回测验证功能开发中...")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
