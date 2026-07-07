import requests
import pandas as pd
import os
from datetime import datetime

def get_stock_data_sina():
    """
    使用新浪财经接口获取数据
    这里模拟获取“AI智能体”相关股票，由于新浪没有直接的概念API，
    我们通常只能获取特定列表或大盘数据。
    为了演示，这里改为获取 '沪深300' 中涨幅靠前的股票作为替代，
    或者你可以维护一个固定的 'AI概念股代码列表'。
    """
    
    # 方案 A: 如果你有固定的 AI 股代码列表 (最稳定)
    # symbol_list = ["sh601360", "sz002230", "sh600519"] # 示例代码
    # 这种方案最稳，不会变，但需要你自己去搜集代码。
    
    # 方案 B: 尝试通过新浪接口获取部分数据 (不稳定，仅作演示)
    # 由于新浪没有直接的"概念板块"API，我们这里用一种取巧的方式：
    # 假设你关注的是热门科技股，我们可以硬编码几个核心标的，
    # 或者使用 pytdx (通达信数据) 等本地库，但在 GitHub Actions 上 pytdx 也容易连不上。
    
    # 鉴于你在 GitHub Actions 上遇到的网络问题，
    # 【强烈建议】使用方案 A：手动维护一个你看好的 AI 股票池。
    
    # 这里为你提供一个包含常见 AI 龙头的代码池 (仅作示例，你可以修改)
    stock_pool = [
        "sh601360", "sz002230", "sz002049", "sh603019", 
        "sz002415", "sh600570", "sz000977", "sh601138",
        "sz300418", "sz002371"
    ]
    
    try:
        # 构造新浪批量查询接口
        symbols_str = ",".join(stock_pool)
        url = f"https://hq.sinajs.cn/list={symbols_str}"
        
        # 必须加 Referer，否则新浪会拒绝请求
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0"
        }
        
        resp = requests.get(url, headers=headers)
        resp.encoding = 'gbk' # 新浪接口是 GBK 编码
        
        data_list = []
        for line in resp.text.split('\n'):
            if '=' in line and 'var hq_str_' in line:
                # 解析数据
                parts = line.split('=')
                code_full = parts[0].split('_')[-1]
                values = parts[1].strip('"').split(',')
                
                if len(values) > 30:
                    name = values[0]
                    current_price = float(values[3])
                    open_price = float(values[1])
                    pre_close = float(values[2])
                    
                    # 计算涨跌幅
                    if pre_close > 0:
                        change_pct = (current_price - pre_close) / pre_close * 100
                    else:
                        change_pct = 0
                    
                    # 获取成交额 (values[9] 通常是成交额，单位元)
                    volume_money = float(values[9]) if values[9] else 0
                    
                    data_list.append({
                        '名称': name,
                        '代码': code_full,
                        '现价': current_price,
                        '涨跌幅': round(change_pct, 2),
                        '成交额': volume_money
                    })
        
        df = pd.DataFrame(data_list)
        
        if df.empty:
            return "未获取到任何股票数据，可能是接口被封或代码错误。"
            
        # 按成交额排序取前10 (模拟热度)
        df = df.nlargest(10, '成交额')
        return df
        
    except Exception as e:
        return f"抓取新浪数据失败: {str(e)}"

def send_message(content):
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        print("错误：未找到 WEBHOOK_URL")
        return

    headers = {'Content-Type': 'application/json'}
    
    # 自动识别平台
    if 'dingtalk' in webhook_url:
        payload = {"msgtype": "text", "text": {"content": content}}
    elif 'feishu' in webhook_url or 'lark' in webhook_url:
        payload = {"msg_type": "text", "content": {"text": content}}
    else:
        payload = {"msgtype": "text", "text": {"content": content}}
        
    requests.post(webhook_url, json=payload, headers=headers)

if __name__ == "__main__":
    print("开始运行...")
    data = get_stock_data_sina()
    
    if isinstance(data, str):
        msg = f"❌ 运行出错:\n{data}"
    else:
        msg = f"🔥 AI 核心股票池监控\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for i, row in data.iterrows():
            color = "🟢" if row['涨跌幅'] > 0 else "🔴"
            msg += f"{color} {row['名称']} ({row['代码']}) \n   现价:{row['现价']} | 涨幅:{row['涨跌幅']}%\n"
    
    print(msg)
    send_message(msg)
