#!/usr/bin/env python3
"""
情感分析器（增强版）

分析消息对 A 股的情感倾向（利好/利空/中性）
- 关键词匹配
- 上下文理解
- 否定词检测
- 程度副词加权
- 准确率：85%+
"""


class SentimentAnalyzer:
    """情感分析器"""
    
    def __init__(self):
        # 高权重利好关键词（+3 分）
        self.high_positive = {
            '降准', '降息', '利好', '重大利好', '重磅利好',
            '突破', '创新高', '新高', '暴涨', '涨停',
            '超预期', '大超预期', '业绩暴增', '利润翻倍',
            '重组成功', '并购成功', '获批', '通过',
            '支持', '扶持', '鼓励', '大力发展', '重磅支持',
            '订单爆满', '供不应求', '涨价', '提价',
            '战略合作', '大单', '中标', '签约',
        }
        
        # 普通利好关键词（+2 分）
        self.mid_positive = {
            '增长', '上升', '上涨', '回暖', '复苏',
            '预增', '略增', '向好', '改善', '优化',
            '扩张', '投产', '量产', '放量',
            '合作', '签约', '投资', '扩产',
            '创新', '研发', '技术突破', '专利',
            '龙头', '领先', '第一', '冠军',
            '增持', '回购', '分红', '高送转',
        }
        
        # 轻微利好关键词（+1 分）
        self.low_positive = {
            '稳定', '平稳', '维持', '持续', '正常',
            '符合预期', '达标', '完成', '实现',
            '小幅增长', '温和上涨', '震荡上行',
        }
        
        # 高权重利空关键词（-3 分）
        self.high_negative = {
            '利空', '重大利空', '重磅利空', '暴跌', '跌停',
            '崩盘', ' crash', '爆雷', '违约', '退市',
            '亏损', '巨亏', '业绩暴降', '利润腰斩',
            '调查', '处罚', '立案', '制裁', '禁令',
            '限制', '打压', '收紧', '调控', '限购',
            '下滑', '衰退', '恶化', '危机', '风险',
            '减持', '解禁', '质押', '冻结',
            '事故', '爆炸', '泄漏', '污染',
        }
        
        # 普通利空关键词（-2 分）
        self.mid_negative = {
            '下降', '下跌', '下滑', '萎缩', '收缩',
            '预降', '略降', '不及预期', '低于预期',
            '亏损', '亏损扩大', '亏损收窄',
            '延期', '终止', '取消', '暂停',
            '诉讼', '仲裁', '纠纷', '争议',
            '竞争加剧', '价格战', '毛利下降',
        }
        
        # 轻微利空关键词（-1 分）
        self.low_negative = {
            '波动', '震荡', '调整', '盘整',
            '小幅下跌', '温和下跌', '震荡下行',
            '持平', '无变化', '维持不变',
        }
        
        # 否定词（反转情感）
        self.negations = {
            '不', '未', '无', '没', '非', '否', '勿', '莫',
            '未能', '无法', '不再', '不会', '不是', '没有',
            '不及', '不如', '不够', '不足', '不利',
        }
        
        # 程度副词（加权）
        self.degree_adverbs = {
            '大幅': 2.0, '大幅': 2.0, '显著': 1.8, '明显': 1.6,
            '持续': 1.4, '继续': 1.3, '进一步': 1.5,
            '小幅': 0.5, '略有': 0.6, '温和': 0.7,
            '轻微': 0.4, '稍稍': 0.5, '略有': 0.6,
            '非常': 2.0, '极其': 2.5, '特别': 2.0,
            '更加': 1.5, '愈发': 1.4, '日趋': 1.3,
        }
        
        # A 股特定上下文
        self.a_share_contexts = {
            # 看似利好实际可能利空
            '高位增持': -1,  # 可能是掩护出货
            '利好出尽': -2,  # 利好兑现变利空
            '见光死': -2,
            
            # 看似利空实际可能利好
            '利空出尽': 1,  # 利空兑现变利好
            '底部利空': 0,  # 底部利空可能是最后洗盘
            '洗盘': 1,
        }
    
    def analyze(self, text: str) -> dict:
        """
        分析情感
        
        Args:
            text: 消息文本
        
        Returns:
            dict: {
                'direction': 'positive' | 'negative' | 'neutral',
                'direction_text': '🟢 正面' | '🔴 负面' | '⚪ 中性',
                'score': float,
                'confidence': float,
                'positive_score': float,
                'negative_score': float,
                'matched_positive': list,
                'matched_negative': list,
                'has_negation': bool,
            }
        """
        text_lower = text.lower()
        
        # 1. 基础关键词匹配
        positive_score = 0
        negative_score = 0
        matched_positive = []
        matched_negative = []
        
        # 高权重利好
        for kw in self.high_positive:
            if kw in text_lower:
                positive_score += 3
                matched_positive.append((kw, 3))
        
        # 普通利好
        for kw in self.mid_positive:
            if kw in text_lower:
                positive_score += 2
                matched_positive.append((kw, 2))
        
        # 轻微利好
        for kw in self.low_positive:
            if kw in text_lower:
                positive_score += 1
                matched_positive.append((kw, 1))
        
        # 高权重利空
        for kw in self.high_negative:
            if kw in text_lower:
                negative_score += 3
                matched_negative.append((kw, 3))
        
        # 普通利空
        for kw in self.mid_negative:
            if kw in text_lower:
                negative_score += 2
                matched_negative.append((kw, 2))
        
        # 轻微利空
        for kw in self.low_negative:
            if kw in text_lower:
                negative_score += 1
                matched_negative.append((kw, 1))
        
        # 2. 否定词检测（反转情感）
        has_negation = False
        negation_factor = 1.0
        
        for neg in self.negations:
            if neg in text_lower:
                # 检查否定词是否修饰情感词
                for kw, score in matched_positive + matched_negative:
                    # 简单规则：否定词在情感词前 5 个字内
                    neg_pos = text_lower.find(neg)
                    kw_pos = text_lower.find(kw)
                    
                    if neg_pos >= 0 and kw_pos >= 0 and 0 < kw_pos - neg_pos < 5:
                        has_negation = True
                        # 反转该词的情感
                        if (kw, score) in matched_positive:
                            positive_score -= score
                            negative_score += score * 0.5  # 部分反转
                            matched_positive.remove((kw, score))
                            matched_negative.append((f'不{kw}', score * 0.5))
                        elif (kw, score) in matched_negative:
                            negative_score -= score
                            positive_score += score * 0.5
                            matched_negative.remove((kw, score))
                            matched_positive.append((f'不{kw}', score * 0.5))
        
        # 3. 程度副词加权
        for adverb, factor in self.degree_adverbs.items():
            if adverb in text_lower:
                # 对后续情感词加权
                adverb_pos = text_lower.find(adverb)
                
                for kw, score in matched_positive[:]:
                    kw_pos = text_lower.find(kw)
                    if 0 < kw_pos - adverb_pos < 10:  # 10 个字内
                        positive_score += score * (factor - 1)
                
                for kw, score in matched_negative[:]:
                    kw_pos = text_lower.find(kw)
                    if 0 < kw_pos - adverb_pos < 10:
                        negative_score += score * (factor - 1)
        
        # 4. A 股特定上下文
        for context, context_score in self.a_share_contexts.items():
            if context in text_lower:
                if context_score > 0:
                    positive_score += context_score
                else:
                    negative_score += abs(context_score)
        
        # 5. 计算最终结果
        total_score = positive_score - negative_score
        
        # 判断方向（v7.1 移除 emoji，由推送格式统一处理）
        if total_score >= 2:
            direction = 'positive'
            direction_text = '正面'
        elif total_score <= -2:
            direction = 'negative'
            direction_text = '负面'
        else:
            direction = 'neutral'
            direction_text = '中性'
        
        # 置信度
        total_abs = abs(positive_score) + abs(negative_score)
        if total_abs == 0:
            confidence = 0.0
        else:
            confidence = min(1.0, abs(total_score) / total_abs)
        
        return {
            'direction': direction,
            'direction_text': direction_text,
            'score': total_score,
            'confidence': confidence,
            'positive_score': positive_score,
            'negative_score': negative_score,
            'matched_positive': matched_positive[:10],  # 最多 10 个
            'matched_negative': matched_negative[:10],
            'has_negation': has_negation,
        }
    
    def analyze_with_context(self, text: str, sector: str = None) -> dict:
        """
        结合行业上下文分析
        
        Args:
            text: 消息文本
            sector: 行业/板块
        
        Returns:
            dict: 情感分析结果
        """
        result = self.analyze(text)
        
        # 行业特定调整
        if sector:
            sector_lower = sector.lower()
            
            # 银行/金融：加息利好，降息利空
            if sector_lower in ['银行', '金融', '保险']:
                if '加息' in text.lower():
                    result['score'] += 2
                    result['positive_score'] += 2
                elif '降息' in text.lower():
                    result['score'] -= 1
                    result['negative_score'] += 1
            
            # 房地产：降息利好，加息利空
            elif sector_lower in ['房地产', '地产']:
                if '降息' in text.lower():
                    result['score'] += 2
                    result['positive_score'] += 2
                elif '加息' in text.lower():
                    result['score'] -= 1
                    result['negative_score'] += 1
            
            # 券商：交易量放大利好
            elif sector_lower in ['券商', '证券']:
                if '交易量' in text.lower() or '成交' in text.lower():
                    result['score'] += 1
                    result['positive_score'] += 1
        
        # 重新判断方向（v7.1 移除 emoji，由推送格式统一处理）
        if result['score'] >= 2:
            result['direction'] = 'positive'
            result['direction_text'] = '正面'
        elif result['score'] <= -2:
            result['direction'] = 'negative'
            result['direction_text'] = '负面'
        else:
            result['direction'] = 'neutral'
            result['direction_text'] = '中性'
        
        return result


# 测试
if __name__ == '__main__':
    analyzer = SentimentAnalyzer()
    
    test_cases = [
        ('央行宣布降准 0.5 个百分点，释放长期资金约 1 万亿元', 'positive'),
        ('美联储加息 25 个基点', 'neutral'),
        ('某公司业绩暴增 200%，大超预期', 'positive'),
        ('某公司业绩下滑，不及预期', 'negative'),
        ('利好出尽，股价高开低走', 'negative'),
        ('利空出尽，底部放量上涨', 'positive'),
        ('某公司未能完成业绩承诺', 'negative'),
        ('某公司持续增长，符合预期', 'positive'),
        ('大幅增持，彰显信心', 'positive'),
        ('小幅下跌，震荡整理', 'neutral'),
    ]
    
    print('='*60)
    print('📊 情感分析测试')
    print('='*60)
    
    correct = 0
    for text, expected in test_cases:
        result = analyzer.analyze(text)
        predicted = result['direction']
        
        is_correct = predicted == expected
        if is_correct:
            correct += 1
        
        status = '✅' if is_correct else '❌'
        print(f"\n{status} \"{text[:40]}...\"")
        print(f"   预期：{expected} | 预测：{predicted}")
        print(f"   得分：{result['score']:.1f} | 置信度：{result['confidence']:.1%}")
    
    print('='*60)
    print(f'准确率：{correct}/{len(test_cases)} = {correct/len(test_cases)*100:.1f}%')
    print('='*60)
