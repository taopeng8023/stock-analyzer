#!/usr/bin/env python3
"""
产业链分析器

分析消息对产业链上下游的影响
- 上游原材料
- 中游制造
- 下游应用
- 产业链传导效应
"""


class ChainAnalyzer:
    """产业链分析器"""
    
    def __init__(self):
        # 产业链映射
        self.industry_chains = {
            '新能源汽车': {
                'upstream': {
                    'name': '上游原材料',
                    'sectors': ['锂矿', '钴矿', '镍矿', '稀土', '石墨'],
                    'stocks': [
                        {'code': 'sz002466', 'name': '天齐锂业'},
                        {'code': 'sz002756', 'name': '永兴材料'},
                        {'code': 'sh603799', 'name': '华友钴业'},
                    ]
                },
                'midstream': {
                    'name': '中游制造',
                    'sectors': ['锂电池', '电机', '电控', '隔膜', '正极'],
                    'stocks': [
                        {'code': 'sz300750', 'name': '宁德时代'},
                        {'code': 'sz002594', 'name': '比亚迪'},
                        {'code': 'sz300014', 'name': '亿纬锂能'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['电动车', '充电桩', '换电站', '电池回收'],
                    'stocks': [
                        {'code': 'sz002594', 'name': '比亚迪'},
                        {'code': 'sh600418', 'name': '江淮汽车'},
                        {'code': 'sh601633', 'name': '长城汽车'},
                    ]
                }
            },
            '光伏': {
                'upstream': {
                    'name': '上游原材料',
                    'sectors': ['硅料', '硅片', '银浆', '玻璃'],
                    'stocks': [
                        {'code': 'sh600438', 'name': '通威股份'},
                        {'code': 'sz002129', 'name': 'TCL 中环'},
                        {'code': 'sz002756', 'name': '永兴材料'},
                    ]
                },
                'midstream': {
                    'name': '中游制造',
                    'sectors': ['电池片', '组件', '逆变器'],
                    'stocks': [
                        {'code': 'sh601012', 'name': '隆基绿能'},
                        {'code': 'sz002459', 'name': '晶澳科技'},
                        {'code': 'sz300274', 'name': '阳光电源'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['电站', '分布式', '储能'],
                    'stocks': [
                        {'code': 'sh600900', 'name': '长江电力'},
                        {'code': 'sz300750', 'name': '宁德时代'},
                    ]
                }
            },
            '半导体': {
                'upstream': {
                    'name': '上游设备/材料',
                    'sectors': ['设备', '材料', 'EDA', 'IP'],
                    'stocks': [
                        {'code': 'sz002371', 'name': '北方华创'},
                        {'code': 'sh688012', 'name': '中微公司'},
                        {'code': 'sh603501', 'name': '韦尔股份'},
                    ]
                },
                'midstream': {
                    'name': '中游制造',
                    'sectors': ['设计', '制造', '封测'],
                    'stocks': [
                        {'code': 'sh688981', 'name': '中芯国际'},
                        {'code': 'sz002156', 'name': '通富微电'},
                        {'code': 'sz002371', 'name': '北方华创'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['消费电子', '汽车电子', 'AI', '5G'],
                    'stocks': [
                        {'code': 'sz002475', 'name': '立讯精密'},
                        {'code': 'sz000725', 'name': '京东方 A'},
                        {'code': 'sz002241', 'name': '歌尔股份'},
                    ]
                }
            },
            '医药': {
                'upstream': {
                    'name': '上游原料药',
                    'sectors': ['原料药', '中间体', '药用辅料'],
                    'stocks': [
                        {'code': 'sh600276', 'name': '恒瑞医药'},
                        {'code': 'sh603259', 'name': '药明康德'},
                    ]
                },
                'midstream': {
                    'name': '中游制药',
                    'sectors': ['化学药', '生物药', '中药'],
                    'stocks': [
                        {'code': 'sh600276', 'name': '恒瑞医药'},
                        {'code': 'sz000538', 'name': '云南白药'},
                        {'code': 'sh600436', 'name': '片仔癀'},
                    ]
                },
                'downstream': {
                    'name': '下游流通',
                    'sectors': ['医药商业', '医疗器械', '医疗服务'],
                    'stocks': [
                        {'code': 'sh601607', 'name': '上海医药'},
                        {'code': 'sz000963', 'name': '华东医药'},
                    ]
                }
            },
            '白酒': {
                'upstream': {
                    'name': '上游原材料',
                    'sectors': ['粮食', '包装', '瓶盖'],
                    'stocks': [
                        {'code': 'sz000876', 'name': '新希望'},
                        {'code': 'sz002014', 'name': '永新股份'},
                    ]
                },
                'midstream': {
                    'name': '中游酿造',
                    'sectors': ['高端白酒', '次高端', '中低端'],
                    'stocks': [
                        {'code': 'sh600519', 'name': '贵州茅台'},
                        {'code': 'sz000858', 'name': '五粮液'},
                        {'code': 'sz000568', 'name': '泸州老窖'},
                    ]
                },
                'downstream': {
                    'name': '下游流通',
                    'sectors': ['经销商', '电商', '餐饮'],
                    'stocks': [
                        {'code': 'sz002024', 'name': '苏宁易购'},
                        {'code': 'sh600827', 'name': '百联股份'},
                    ]
                }
            },
            '房地产': {
                'upstream': {
                    'name': '上游原材料',
                    'sectors': ['钢铁', '水泥', '玻璃', '建材'],
                    'stocks': [
                        {'code': 'sh600019', 'name': '宝钢股份'},
                        {'code': 'sh600585', 'name': '海螺水泥'},
                    ]
                },
                'midstream': {
                    'name': '中游开发',
                    'sectors': ['住宅开发', '商业地产', '产业园区'],
                    'stocks': [
                        {'code': 'sz000002', 'name': '万科 A'},
                        {'code': 'sh600048', 'name': '保利发展'},
                        {'code': 'sh600383', 'name': '金地集团'},
                    ]
                },
                'downstream': {
                    'name': '下游服务',
                    'sectors': ['物业', '中介', '装修'],
                    'stocks': [
                        {'code': 'sz002627', 'name': '宜昌交运'},
                        {'code': 'sz002375', 'name': '亚厦股份'},
                    ]
                }
            },
            '人工智能': {
                'upstream': {
                    'name': '上游算力/数据',
                    'sectors': ['AI 芯片', '服务器', '数据中心', '数据标注'],
                    'stocks': [
                        {'code': 'sz000977', 'name': '浪潮信息'},
                        {'code': 'sh603019', 'name': '中科曙光'},
                        {'code': 'sz002230', 'name': '科大讯飞'},
                    ]
                },
                'midstream': {
                    'name': '中游算法/模型',
                    'sectors': ['大模型', '计算机视觉', '语音识别', 'NLP'],
                    'stocks': [
                        {'code': 'sz002230', 'name': '科大讯飞'},
                        {'code': 'sz300271', 'name': '华宇软件'},
                        {'code': 'sz002153', 'name': '石基信息'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['智能驾驶', '智能家居', '智慧医疗', '工业 AI'],
                    'stocks': [
                        {'code': 'sz002594', 'name': '比亚迪'},
                        {'code': 'sz002475', 'name': '立讯精密'},
                        {'code': 'sz000651', 'name': '格力电器'},
                    ]
                }
            },
            '5G': {
                'upstream': {
                    'name': '上游芯片/器件',
                    'sectors': ['基带芯片', '射频器件', '光模块', '天线'],
                    'stocks': [
                        {'code': 'sz000063', 'name': '中兴通讯'},
                        {'code': 'sz002194', 'name': '武汉凡谷'},
                        {'code': 'sz002281', 'name': '光迅科技'},
                    ]
                },
                'midstream': {
                    'name': '中游设备',
                    'sectors': ['基站设备', '传输设备', '网络优化'],
                    'stocks': [
                        {'code': 'sz000063', 'name': '中兴通讯'},
                        {'code': 'sh600498', 'name': '烽火通信'},
                        {'code': 'sz002544', 'name': '杰赛科技'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['智能手机', '物联网', '车联网', '工业互联网'],
                    'stocks': [
                        {'code': 'sz002475', 'name': '立讯精密'},
                        {'code': 'sz000725', 'name': '京东方 A'},
                        {'code': 'sz002594', 'name': '比亚迪'},
                    ]
                }
            },
            '消费电子': {
                'upstream': {
                    'name': '上游零部件',
                    'sectors': ['芯片', '屏幕', '电池', '摄像头'],
                    'stocks': [
                        {'code': 'sz002475', 'name': '立讯精密'},
                        {'code': 'sz000725', 'name': '京东方 A'},
                        {'code': 'sz002241', 'name': '歌尔股份'},
                    ]
                },
                'midstream': {
                    'name': '中游组装',
                    'sectors': ['手机组装', 'PC 组装', '可穿戴'],
                    'stocks': [
                        {'code': 'sz002475', 'name': '立讯精密'},
                        {'code': 'sz002241', 'name': '歌尔股份'},
                        {'code': 'sz002036', 'name': '联创电子'},
                    ]
                },
                'downstream': {
                    'name': '下游品牌/渠道',
                    'sectors': ['手机品牌', '电商平台', '零售'],
                    'stocks': [
                        {'code': 'sz002024', 'name': '苏宁易购'},
                        {'code': 'sh600827', 'name': '百联股份'},
                    ]
                }
            },
            '军工': {
                'upstream': {
                    'name': '上游材料/元器件',
                    'sectors': ['钛合金', '碳纤维', '军工电子', '连接器'],
                    'stocks': [
                        {'code': 'sz002049', 'name': '紫光国微'},
                        {'code': 'sz002179', 'name': '中航光电'},
                        {'code': 'sz300775', 'name': '三角防务'},
                    ]
                },
                'midstream': {
                    'name': '中游分系统',
                    'sectors': ['航空发动机', '导弹', '雷达', '航电'],
                    'stocks': [
                        {'code': 'sz000768', 'name': '中航西飞'},
                        {'code': 'sz002013', 'name': '中航机电'},
                        {'code': 'sz002151', 'name': '北斗星通'},
                    ]
                },
                'downstream': {
                    'name': '下游整机',
                    'sectors': ['飞机', '船舶', '导弹', '卫星'],
                    'stocks': [
                        {'code': 'sh600150', 'name': '中国船舶'},
                        {'code': 'sz000768', 'name': '中航西飞'},
                        {'code': 'sz002025', 'name': '航天电器'},
                    ]
                }
            },
            '数字经济': {
                'upstream': {
                    'name': '上游基础设施',
                    'sectors': ['5G', '数据中心', '云计算', '物联网'],
                    'stocks': [
                        {'code': 'sz000063', 'name': '中兴通讯'},
                        {'code': 'sz000977', 'name': '浪潮信息'},
                        {'code': 'sh600845', 'name': '宝信软件'},
                    ]
                },
                'midstream': {
                    'name': '中游平台/技术',
                    'sectors': ['大数据', '区块链', 'AI', '安全'],
                    'stocks': [
                        {'code': 'sz002230', 'name': '科大讯飞'},
                        {'code': 'sz002153', 'name': '石基信息'},
                        {'code': 'sz300496', 'name': '中科创达'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['政务', '金融', '医疗', '教育'],
                    'stocks': [
                        {'code': 'sz002153', 'name': '石基信息'},
                        {'code': 'sz300271', 'name': '华宇软件'},
                        {'code': 'sz002065', 'name': '东华软件'},
                    ]
                }
            },
            '碳中和': {
                'upstream': {
                    'name': '上游清洁能源',
                    'sectors': ['光伏', '风电', '水电', '核电'],
                    'stocks': [
                        {'code': 'sh601012', 'name': '隆基绿能'},
                        {'code': 'sz002202', 'name': '金风科技'},
                        {'code': 'sh600900', 'name': '长江电力'},
                    ]
                },
                'midstream': {
                    'name': '中游储能/传输',
                    'sectors': ['储能', '特高压', '智能电网'],
                    'stocks': [
                        {'code': 'sz300750', 'name': '宁德时代'},
                        {'code': 'sz002594', 'name': '比亚迪'},
                        {'code': 'sz002452', 'name': '长高电新'},
                    ]
                },
                'downstream': {
                    'name': '下游应用/交易',
                    'sectors': ['电动车', '碳交易', '节能服务'],
                    'stocks': [
                        {'code': 'sz002594', 'name': '比亚迪'},
                        {'code': 'sz000969', 'name': '安泰科技'},
                    ]
                }
            },
            '元宇宙': {
                'upstream': {
                    'name': '上游硬件',
                    'sectors': ['VR/AR', '芯片', '传感器', '显示'],
                    'stocks': [
                        {'code': 'sz002241', 'name': '歌尔股份'},
                        {'code': 'sz000725', 'name': '京东方 A'},
                        {'code': 'sz002036', 'name': '联创电子'},
                    ]
                },
                'midstream': {
                    'name': '中游平台/内容',
                    'sectors': ['游戏', '视频', '社交', '引擎'],
                    'stocks': [
                        {'code': 'sz002555', 'name': '三七互娱'},
                        {'code': 'sz002624', 'name': '完美世界'},
                        {'code': 'sz300418', 'name': '昆仑万维'},
                    ]
                },
                'downstream': {
                    'name': '下游应用',
                    'sectors': ['虚拟人', '数字藏品', '虚拟地产'],
                    'stocks': [
                        {'code': 'sz002555', 'name': '三七互娱'},
                        {'code': 'sz300251', 'name': '光线传媒'},
                    ]
                }
            },
        }
    
    def analyze_chain_impact(self, text: str) -> dict:
        """
        分析消息对产业链的影响
        
        Args:
            text: 消息文本
        
        Returns:
            dict: 产业链影响分析结果
        """
        text_lower = text.lower()
        
        chain_impacts = []
        
        for chain_name, chain_data in self.industry_chains.items():
            # 检查是否涉及该产业链
            chain_keywords = [chain_name] + \
                           [s for sector in chain_data.values() for s in sector.get('sectors', [])]
            
            if any(kw in text_lower for kw in chain_keywords):
                impact = self._analyze_single_chain(text_lower, chain_name, chain_data)
                chain_impacts.append(impact)
        
        return {
            'chains': chain_impacts,
            'total_chains': len(chain_impacts),
        }
    
    def _analyze_single_chain(self, text: str, chain_name: str, chain_data: dict) -> dict:
        """分析单个产业链的影响"""
        result = {
            'chain_name': chain_name,
            'upstream': {'impact': 0, 'sentiment': 'neutral', 'stocks': []},
            'midstream': {'impact': 0, 'sentiment': 'neutral', 'stocks': []},
            'downstream': {'impact': 0, 'sentiment': 'neutral', 'stocks': []},
        }
        
        # 情感分析
        positive_words = ['利好', '增长', '支持', '上涨', '突破', '复苏']
        negative_words = ['利空', '下滑', '限制', '下跌', '风险', '衰退']
        
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        
        if pos_count > neg_count * 1.5:
            sentiment = 'positive'
        elif neg_count > pos_count * 1.5:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # 分析各环节影响
        for segment in ['upstream', 'midstream', 'downstream']:
            segment_data = chain_data.get(segment, {})
            sectors = segment_data.get('sectors', [])
            stocks = segment_data.get('stocks', [])
            
            # 计算影响程度
            sector_match = sum(1 for s in sectors if any(kw in text for kw in s))
            impact_score = sector_match * 2
            
            result[segment] = {
                'impact': impact_score,
                'sentiment': sentiment,
                'stocks': stocks[:5],  # 返回前 5 只股票
                'sectors_matched': [s for s in sectors if any(kw in text for kw in s)],
            }
        
        return result
    
    def get_chain_summary(self, chain_analysis: dict) -> str:
        """获取产业链分析摘要"""
        lines = []
        
        for chain in chain_analysis.get('chains', []):
            chain_name = chain['chain_name']
            lines.append(f"🔗 **{chain_name}产业链**")
            
            # 上游
            upstream = chain.get('upstream', {})
            if upstream.get('impact', 0) > 0:
                emoji = '🟢' if upstream['sentiment'] == 'positive' else '🔴' if upstream['sentiment'] == 'negative' else '⚪'
                lines.append(f"  {emoji} 上游：{upstream['name']} (影响度：{upstream['impact']})")
                for stock in upstream.get('stocks', [])[:3]:
                    lines.append(f"    • {stock['name']} ({stock['code']})")
            
            # 中游
            midstream = chain.get('midstream', {})
            if midstream.get('impact', 0) > 0:
                emoji = '🟢' if midstream['sentiment'] == 'positive' else '🔴' if midstream['sentiment'] == 'negative' else '⚪'
                lines.append(f"  {emoji} 中游：{midstream['name']} (影响度：{midstream['impact']})")
                for stock in midstream.get('stocks', [])[:3]:
                    lines.append(f"    • {stock['name']} ({stock['code']})")
            
            # 下游
            downstream = chain.get('downstream', {})
            if downstream.get('impact', 0) > 0:
                emoji = '🟢' if downstream['sentiment'] == 'positive' else '🔴' if downstream['sentiment'] == 'negative' else '⚪'
                lines.append(f"  {emoji} 下游：{downstream['name']} (影响度：{downstream['impact']})")
                for stock in downstream.get('stocks', [])[:3]:
                    lines.append(f"    • {stock['name']} ({stock['code']})")
            
            lines.append("")
        
        return "\n".join(lines)


# 测试
if __name__ == '__main__':
    analyzer = ChainAnalyzer()
    
    test_texts = [
        '新能源汽车销量大增，锂电池需求旺盛',
        '光伏产业链价格普涨，硅料供应紧张',
        '半导体国产替代加速，设备厂商受益',
    ]
    
    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"消息：{text}")
        print(f"{'='*60}")
        
        result = analyzer.analyze_chain_impact(text)
        print(analyzer.get_chain_summary(result))
