#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署最佳神经网络模型

将最佳模型部署为选股系统的预测引擎
"""

import pickle
import json
from pathlib import Path
import shutil
from datetime import datetime

MODEL_DIR = Path('/home/admin/.openclaw/workspace/stocks/models')
SKILL_DIR = Path('/home/admin/.openclaw/workspace/skills/a-stock-analyzer')

# 最佳模型
BEST_MODEL = MODEL_DIR / 'ml_nn_opt_超大网络_20260413_142659.pkl'

def deploy():
    print('='*60)
    print('部署最佳神经网络模型')
    print('='*60)
    
    # 加载模型
    print(f'\n加载模型: {BEST_MODEL.name}')
    with open(BEST_MODEL, 'rb') as f:
        data = pickle.load(f)
    
    model = data['model']
    scaler = data['scaler']
    features = data['features']
    
    print(f'  网络结构: {model.hidden_layer_sizes}')
    print(f'  特征数量: {len(features)}')
    print(f'  特征列表: {features}')
    
    # 复制为生产模型
    prod_model_path = MODEL_DIR / 'ml_nn_production.pkl'
    
    # 添加元数据
    deploy_data = {
        'model': model,
        'scaler': scaler,
        'features': features,
        'metadata': {
            'source': BEST_MODEL.name,
            'deploy_time': datetime.now().isoformat(),
            'auc': 0.6350,
            'precision_90': 0.9505,
            'hidden_layers': model.hidden_layer_sizes,
            'version': 'v1.0'
        }
    }
    
    with open(prod_model_path, 'wb') as f:
        pickle.dump(deploy_data, f)
    
    print(f'\n生产模型已保存: {prod_model_path}')
    
    # 创建预测脚本
    predict_script = '''#!/usr/bin/env python3
"""神经网络预测引擎"""

import pickle
import numpy as np
from pathlib import Path

MODEL_PATH = Path('/home/admin/.openclaw/workspace/stocks/models/ml_nn_production.pkl')

class NeuralPredictor:
    def __init__(self):
        with open(MODEL_PATH, 'rb') as f:
            self.data = pickle.load(f)
        self.model = self.data['model']
        self.scaler = self.data['scaler']
        self.features = self.data['features']
        self.metadata = self.data['metadata']
    
    def predict(self, feature_dict):
        """预测单个股票"""
        # 提取特征
        X = np.array([[feature_dict.get(f, 0) for f in self.features]])
        # 标准化
        X_scaled = self.scaler.transform(X)
        # 预测概率
        prob = self.model.predict_proba(X_scaled)[0, 1]
        return prob
    
    def predict_batch(self, feature_matrix):
        """批量预测"""
        X_scaled = self.scaler.transform(feature_matrix)
        probs = self.model.predict_proba(X_scaled)[:, 1]
        return probs
    
    def get_high_confidence(self, probs, threshold=0.85):
        """获取高置信度预测"""
        return probs > threshold

# 使用示例
if __name__ == '__main__':
    predictor = NeuralPredictor()
    print(f'模型版本: {predictor.metadata["version"]}')
    print(f'AUC: {predictor.metadata["auc"]}')
    print(f'90%阈值精确率: {predictor.metadata["precision_90"]}')
'''
    
    predict_path = MODEL_DIR / 'neural_predictor.py'
    with open(predict_path, 'w') as f:
        f.write(predict_script)
    
    print(f'预测脚本已保存: {predict_path}')
    
    # 保存配置
    config = {
        'model_type': 'mlp_neural_network',
        'model_file': 'ml_nn_production.pkl',
        'predict_script': 'neural_predictor.py',
        'features': features,
        'thresholds': {
            'high_confidence': 0.85,
            'very_high': 0.90
        },
        'performance': {
            'auc': 0.6350,
            'precision_90': 0.9505
        },
        'deploy_time': datetime.now().isoformat()
    }
    
    config_path = MODEL_DIR / 'neural_config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f'配置文件已保存: {config_path}')
    
    # 验证
    print('\n验证部署...')
    import sys
    sys.path.insert(0, str(MODEL_DIR))
    from neural_predictor import NeuralPredictor
    
    p = NeuralPredictor()
    print(f'  模型加载成功')
    print(f'  特征数: {len(p.features)}')
    print(f'  AUC: {p.metadata["auc"]}')
    
    print('\n' + '='*60)
    print('部署完成!')
    print('='*60)
    print(f'生产模型: {prod_model_path}')
    print(f'预测引擎: {predict_path}')
    print(f'配置文件: {config_path}')

if __name__ == '__main__':
    deploy()