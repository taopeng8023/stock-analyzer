#!/usr/bin/env python3
"""
行业板块分析器

分析消息对国内行业和 A 股板块的影响
- 行业影响分析
- 板块影响分析
- 积极/消极判断
- 影响程度评分
"""


class SectorAnalyzer:
    """行业板块分析器"""
    
    def __init__(self):
        # 行业关键词映射
        self.industry_keywords = {
            # 金融行业
            '银行': {
                'keywords': ['银行', '降准', '降息', 'LPR', '信贷', '利率', '存款准备金'],
                'sensitivity': 5,  # 敏感度 1-5
            },
            '券商': {
                'keywords': ['券商', '证券', '资本市场', 'IPO', '交易', '印花税', 'T+0'],
                'sensitivity': 5,
            },
            '保险': {
                'keywords': ['保险', '保费', '理赔', '险资'],
                'sensitivity': 3,
            },
            '金融': {
                'keywords': ['金融', '央行', '人民银行', '银保监会', '证监会'],
                'sensitivity': 5,
            },
            
            # 科技行业
            '半导体': {
                'keywords': ['芯片', '半导体', '集成电路', '光刻机', '晶圆', 'EDA'],
                'sensitivity': 5,
            },
            '人工智能': {
                'keywords': ['AI', '人工智能', '大模型', '深度学习', '神经网络', 'AIGC'],
                'sensitivity': 5,
            },
            '5G 通信': {
                'keywords': ['5G', '6G', '通信', '基站', '华为', '中兴'],
                'sensitivity': 4,
            },
            '消费电子': {
                'keywords': ['手机', '消费电子', '苹果', '华为', '小米', '智能穿戴'],
                'sensitivity': 4,
            },
            '软件': {
                'keywords': ['软件', '操作系统', '数据库', '云计算', 'SaaS', '信创'],
                'sensitivity': 4,
            },
            
            # 新能源行业
            '光伏': {
                'keywords': ['光伏', '太阳能', '硅料', '电池片', '组件'],
                'sensitivity': 5,
            },
            '风电': {
                'keywords': ['风电', '风力发电', '风机', '海上风电'],
                'sensitivity': 4,
            },
            '储能': {
                'keywords': ['储能', '电池储能', '抽水蓄能'],
                'sensitivity': 4,
            },
            '电动车': {
                'keywords': ['电动车', '新能源車', '比亚迪', '特斯拉', '充电桩'],
                'sensitivity': 5,
            },
            '锂电池': {
                'keywords': ['锂电池', '宁德时代', '比亚迪', '正极', '负极', '电解液'],
                'sensitivity': 5,
            },
            
            # 医药行业
            '医药': {
                'keywords': ['医药', '药品', '制药', '集采', '医保', '创新药'],
                'sensitivity': 5,
            },
            '医疗器械': {
                'keywords': ['医疗器械', '设备', '耗材', '检测'],
                'sensitivity': 4,
            },
            '生物科技': {
                'keywords': ['生物', '疫苗', '基因', '细胞治疗', 'CXO'],
                'sensitivity': 4,
            },
            
            # 能源化工行业
            '石油': {
                'keywords': ['石油', '原油', '油气', '三桶油', '中石油', '中石化', '中海油', '布伦特', 'wti'],
                'sensitivity': 5,
            },
            '天然气': {
                'keywords': ['天然气', '液化气', 'lng', 'cng', '燃气', '燃料'],
                'sensitivity': 4,
            },
            '化工': {
                'keywords': ['化工', '石化', '炼化', '化肥', '农药', '塑料', '橡胶'],
                'sensitivity': 4,
            },
            '期货': {
                'keywords': ['期货', '涨停', '跌停', '主力合约', '大宗商品', '能源'],
                'sensitivity': 4,
            },
            
            # 消费行业
            '白酒': {
                'keywords': ['白酒', '茅台', '五粮液', '酒类'],
                'sensitivity': 4,
            },
            '食品': {
                'keywords': ['食品', '饮料', '乳业', '调味品'],
                'sensitivity': 3,
            },
            '旅游': {
                'keywords': ['旅游', '酒店', '景区', '航空'],
                'sensitivity': 3,
            },
            '零售': {
                'keywords': ['零售', '电商', '超市', '百货'],
                'sensitivity': 3,
            },
            
            # 周期行业
            '钢铁': {
                'keywords': ['钢铁', '钢材', '宝钢', '鞍钢'],
                'sensitivity': 4,
            },
            '煤炭': {
                'keywords': ['煤炭', '焦煤', '动力煤', '中国神华'],
                'sensitivity': 4,
            },
            '有色金属': {
                'keywords': ['有色', '铜', '铝', '锌', '锂', '钴', '稀土'],
                'sensitivity': 4,
            },
            '化工': {
                'keywords': ['化工', '石化', '塑料', '橡胶', '化肥'],
                'sensitivity': 3,
            },
            '建材': {
                'keywords': ['建材', '水泥', '玻璃', '陶瓷'],
                'sensitivity': 3,
            },
            
            # 地产基建
            '房地产': {
                'keywords': ['地产', '房地产', '房价', '楼市', '万科', '保利'],
                'sensitivity': 5,
            },
            '基建': {
                'keywords': ['基建', '投资', '铁路', '公路', '桥梁', '建筑'],
                'sensitivity': 4,
            },
            
            # 其他行业
            '农业': {
                'keywords': ['农业', '种业', '农机', '养猪', '牧原', '温氏'],
                'sensitivity': 3,
            },
            '军工': {
                'keywords': ['军工', '国防', '航空', '航天', '船舶'],
                'sensitivity': 3,
            },
            '传媒': {
                'keywords': ['传媒', '游戏', '影视', '广告', '出版'],
                'sensitivity': 3,
            },
            '环保': {
                'keywords': ['环保', '污水处理', '固废', '碳中和', '碳交易'],
                'sensitivity': 3,
            },
        }
        
        # 积极/消极关键词
        self.positive_keywords = {
            '高': ['支持', '扶持', '利好', '鼓励', '发展', '规划', '刺激', '补贴',
                  '增长', '突破', '创新', '升级', '放宽', '放松', '降准', '降息',
                  '订单', '签约', '合作', '中标', '投产', '量产', '获批', '通过'],
            '中': ['稳定', '平稳', '正常', '维持', '持续', '推进', '落实'],
        }
        
        self.negative_keywords = {
            '高': ['限制', '打压', '利空', '收紧', '调控', '处罚', '调查', '制裁',
                  '下滑', '衰退', '亏损', '风险', '警告', '禁令', '加征', '制裁',
                  '违约', '暴雷', '退市', '减持', '解禁', '诉讼', '事故'],
            '中': ['调整', '波动', '不确定', '关注', '监测', '提醒'],
        }
        
        # A 股板块映射
        self.stock_sectors = {
            '银行': ['银行', '股份制银行', '城商行', '农商行'],
            '券商': ['券商', '证券', '期货', '信托'],
            '半导体': ['半导体', '芯片', '集成电路', '封测'],
            '人工智能': ['人工智能', 'AI', '算力', '大模型'],
            # ... 可以继续扩展
        }
    
    def analyze_industry_impact(self, text: str) -> dict:
        """
        分析对国内行业的影响
        
        Args:
            text: 消息文本
        
        Returns:
            dict: 行业影响分析结果
        """
        text_lower = text.lower()
        
        impacted_industries = []
        
        for industry, config in self.industry_keywords.items():
            keywords = config['keywords']
            sensitivity = config['sensitivity']
            
            # 计算匹配度
            match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
            
            if match_count > 0:
                # 计算影响得分
                impact_score = match_count * sensitivity
                
                # 判断积极/消极
                sentiment = self._analyze_sentiment(text_lower)
                
                impacted_industries.append({
                    'industry': industry,
                    'match_count': match_count,
                    'sensitivity': sensitivity,
                    'impact_score': impact_score,
                    'sentiment': sentiment['direction'],
                    'sentiment_score': sentiment['score'],
                    'keywords_matched': [kw for kw in keywords if kw.lower() in text_lower],
                })
        
        # 按影响得分排序
        impacted_industries.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return {
            'industries': impacted_industries,
            'total_impacted': len(impacted_industries),
            'positive_count': sum(1 for i in impacted_industries if i['sentiment'] == 'positive'),
            'negative_count': sum(1 for i in impacted_industries if i['sentiment'] == 'negative'),
        }
    
    def analyze_sector_impact(self, text: str) -> dict:
        """
        分析对 A 股板块的影响
        
        Args:
            text: 消息文本
        
        Returns:
            dict: A 股板块影响分析结果
        """
        # 先分析行业影响
        industry_impact = self.analyze_industry_impact(text)
        
        # 映射到 A 股板块
        sector_impact = {
            'benefit_sectors': [],  # 受益板块
            'harm_sectors': [],     # 受损板块
            'neutral_sectors': [],  # 中性板块
        }
        
        for industry in industry_impact['industries']:
            sector_info = {
                'name': industry['industry'],
                'impact_score': industry['impact_score'],
                'sentiment': industry['sentiment'],
                'keywords': industry['keywords_matched'],
            }
            
            if industry['sentiment'] == 'positive':
                sector_impact['benefit_sectors'].append(sector_info)
            elif industry['sentiment'] == 'negative':
                sector_impact['harm_sectors'].append(sector_info)
            else:
                sector_impact['neutral_sectors'].append(sector_info)
        
        # 排序
        sector_impact['benefit_sectors'].sort(key=lambda x: x['impact_score'], reverse=True)
        sector_impact['harm_sectors'].sort(key=lambda x: x['impact_score'], reverse=True)
        
        return sector_impact
    
    def _analyze_sentiment(self, text: str) -> dict:
        """
        分析消息情感（积极/消极）
        
        Args:
            text: 消息文本
        
        Returns:
            dict: 情感分析结果
        """
        positive_score = 0
        negative_score = 0
        
        # 计算积极得分
        for level, keywords in self.positive_keywords.items():
            for kw in keywords:
                if kw in text:
                    positive_score += 2 if level == '高' else 1
        
        # 计算消极得分
        for level, keywords in self.negative_keywords.items():
            for kw in keywords:
                if kw in text:
                    negative_score += 2 if level == '高' else 1
        
        # 判断方向
        if positive_score > negative_score * 1.5:
            direction = 'positive'
            direction_text = '积极'
        elif negative_score > positive_score * 1.5:
            direction = 'negative'
            direction_text = '消极'
        else:
            direction = 'neutral'
            direction_text = '中性'
        
        score = positive_score - negative_score
        return {
            'direction': direction,
            'direction_text': direction_text,
            'positive_score': positive_score,
            'negative_score': negative_score,
            'score': score,
            'total_score': positive_score + negative_score,
        }
    
    def get_impact_summary(self, text: str) -> str:
        """获取影响摘要 (v6.0 修复版)"""
        try:
            industry_impact = self.analyze_industry_impact(text)
            sector_impact = self.analyze_sector_impact(text)
        except Exception:
            return "详细分析暂不可用"
        
        lines = []
        
        # 行业影响
        if industry_impact.get('total_impacted', 0) > 0:
            lines.append(f"📊 影响行业：{industry_impact['total_impacted']}个")
            for ind in industry_impact.get('industries', [])[:5]:
                sentiment_emoji = '🟢' if ind.get('sentiment') == 'positive' else '🔴' if ind.get('sentiment') == 'negative' else '⚪'
                ind_name = ind.get('industry', 'N/A')
                ind_score = ind.get('impact_score', 0)
                lines.append(f"  {sentiment_emoji} {ind_name} (影响度：{ind_score})")
        
        # A 股板块影响
        if sector_impact.get('benefit_sectors'):
            lines.append(f"\n🟢 受益板块：{len(sector_impact['benefit_sectors'])}个")
            for sec in sector_impact['benefit_sectors'][:5]:
                sec_name = sec.get('name', 'N/A')
                sec_score = sec.get('impact_score', 0)
                lines.append(f"  + {sec_name} (影响度：{sec_score})")
        
        if sector_impact.get('harm_sectors'):
            lines.append(f"\n🔴 受损板块：{len(sector_impact['harm_sectors'])}个")
            for sec in sector_impact['harm_sectors'][:5]:
                sec_name = sec.get('name', 'N/A')
                sec_score = sec.get('impact_score', 0)
                lines.append(f"  - {sec_name} (影响度：{sec_score})")
        
        return "\n".join(lines) if lines else "详细分析暂不可用"


# 测试
if __name__ == '__main__':
    analyzer = SectorAnalyzer()
    
    test_texts = [
        '央行宣布降准 0.5 个百分点，释放长期资金约 1 万亿元，支持实体经济发展',
        '工信部出台人工智能产业发展规划，推进大模型技术研发和应用落地',
        '美联储加息 25 个基点，美元指数上涨，人民币汇率承压',
    ]
    
    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"消息：{text}")
        print(f"{'='*60}")
        
        summary = analyzer.get_impact_summary(text)
        print(summary)
