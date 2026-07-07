import akshare as ak
import requests
import os
import pandas as pd  # <--- 【关键修复】必须导入 pandas
from datetime import datetime

def get_stock_data():
    """获取AIAgent概念板块数据"""
    try:
        # 获取 AIAgent 概念板块成分股
        # 注意：akshare 接口可能更新，如果报错请检查 symbol 是否有效
        df = ak.stock_board_concept_cons_em(symbol="AI智能体")
        
        # 确保列名存在且数据类型正确
        # 为了防止接口变动导致列名不同，这里做个简单的防御性编程
        if '成交额' not in df.columns or '涨跌幅' not in df.columns:
            return "Error: 返回的数据格式不符合预期，可能缺少'成交额'或'涨跌幅'列"

        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
        df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
        
        # 处理主力净流入，如果没有这一列，给个默认值0
        if '主力净流入' in df.columns:
            df['主力净流入'] = pd.to_numeric(df['主力净流入'], errors='coerce')
        else:
            df['主力净流入'] = 0
        
        # 归一化计算分数 (0-100分制)
        df['score_volume'] = df['成交额'].rank(pct=True) * 40
        df['score_change'] = df['涨跌幅'].rank(pct=True) * 30
        df['score_money'] = df['主力净流入'].rank(pct=True) * 20
        
        # 新闻分暂时固定
        df['score_news'] = 10 
        
        df['total_score'] = df['score_volume'] + df['score_change'] + df['score_money'] + df['score_news']
        
        # 取 Top 10
        top10 = df.nlargest(10, 'total_score')
        return top10
    except Exception as e:
        return str(e)

def send_message(content):
    """推送到 Webhook"""
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        print("错误：未找到 WEBHOOK_URL 环境变量")
        return

    headers = {'Content-Type': 'application/json'}
    
    # 钉钉机器人需要关键词匹配，这里强制加上【股票】前缀，确保能发出去
    # 你在钉钉后台设置的关键词如果是“股票”，这里必须包含这两个字
    safe_content = f"【股票】{content}" 
    
    payload = {"msgtype": "text", "text": {"content": safe_content}}
        
    response = requests.post(webhook_url, json=payload, headers=headers)
    print(f"发送状态码: {response.status_code}")
    print(f"发送结果: {response.text}")

if __name__ == "__main__":
    data = get_stock_data()
    
    if isinstance(data, str):
        # 如果出错，也要加上关键词前缀
        msg = f"【股票】❌ 运行出错:\n{data}"
    else:
        msg = f"🔥 AIAgent 概念热度股票 Top10\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for i, row in data.iterrows():
            # 格式化输出，保留两位小数
            msg += f"{row['代码']} {row['名称']} | 涨幅:{row['涨跌幅']}% | 热度:{int(row['total_score'])}\n"
    
    print("--- 准备发送的消息内容 ---")
    print(msg)
    send_message(msg)
