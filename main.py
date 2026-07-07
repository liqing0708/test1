import akshare as ak
import requests
import os
from datetime import datetime

def get_stock_data():
    """获取AIAgent概念板块数据"""
    try:
        # 获取 AIAgent 概念板块成分股
        df = ak.stock_board_concept_cons_em(symbol="AI智能体")
        
        # 数据清洗与计算热度分
        # 注意：akshare返回的数据列名可能随时间微调，这里做兼容处理
        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
        df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
        df['主力净流入'] = pd.to_numeric(df.get('主力净流入', 0), errors='coerce')
        
        # 归一化计算分数 (0-100分制)
        df['score_volume'] = df['成交额'].rank(pct=True) * 40
        df['score_change'] = df['涨跌幅'].rank(pct=True) * 30
        df['score_money'] = df['主力净流入'].rank(pct=True) * 20
        
        # 新闻分暂时用随机或固定值代替(免费API难获取实时新闻权重)，设为10分满分
        df['score_news'] = 10 
        
        df['total_score'] = df['score_volume'] + df['score_change'] + df['score_money'] + df['score_news']
        
        # 取 Top 10
        top10 = df.nlargest(10, 'total_score')
        return top10
    except Exception as e:
        return str(e)

def send_message(content):
    """推送到 Webhook (支持钉钉/飞书/企微)"""
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        print("错误：未找到 WEBHOOK_URL 环境变量")
        return

    headers = {'Content-Type': 'application/json'}
    
    # 自动识别平台并格式化消息
    if 'dingtalk' in webhook_url:
        payload = {"msgtype": "text", "text": {"content": content}}
    elif 'feishu' in webhook_url or 'lark' in webhook_url:
        payload = {"msg_type": "text", "content": {"text": content}}
    else: # 默认企微格式
        payload = {"msgtype": "text", "text": {"content": content}}
        
    requests.post(webhook_url, json=payload, headers=headers)

if __name__ == "__main__":
    data = get_stock_data()
    if isinstance(data, str):
        msg = f"❌ 运行出错:\n{data}"
    else:
        msg = f"🔥 AIAgent 概念热度 Top10\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for i, row in data.iterrows():
            msg += f"{row['代码']} {row['名称']} | 涨幅:{row['涨跌幅']}% | 热度:{int(row['total_score'])}\n"
    
    print(msg)
    send_message(msg)
