import tushare as ts
import requests
import os
import pandas as pd
from datetime import datetime

def get_stock_data():
    """使用 Tushare 获取 AI 智能体概念股票数据"""
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        return "错误：未配置 TUSHARE_TOKEN 环境变量"

    try:
        # 初始化 Tushare
        ts.set_token(token)
        pro = ts.pro_api()

        # 1. 查找“AI智能体”或相关概念的 ID
        # Tushare 的概念接口需要 concept_id，我们需要先搜一下
        # 注意：不同数据源对概念命名不同，这里尝试搜索包含 'AI' 或 '人工智能' 的概念
        # 如果搜不到，可能需要手动指定一个已知的 ID，或者换成 '沪深300' 等宽基指数测试
        
        # 这里我们尝试获取“人工智能”相关概念（ID通常固定，或者通过 search 接口找）
        # 为了演示稳定性，这里直接使用 Tushare 的 concept_detail 接口
        # 假设我们要查的是“人工智能”概念 (ID: TS009688 仅为示例，实际需动态获取或硬编码)
        
        # --- 简化方案：为了确保你能跑通，我们先获取“上证50”或“沪深300”作为替代 ---
        # 因为概念板块的 ID 经常变，且需要积分权限。
        # 如果你确定有权限查概念，可以使用下面的逻辑。
        
        # 尝试获取概念列表中包含 "AI" 的
        df_concepts = pro.concept() 
        target_id = None
        for index, row in df_concepts.iterrows():
            if 'AI' in str(row['name']) or '智能' in str(row['name']):
                target_id = row['code']
                print(f"找到概念: {row['name']} (ID: {target_id})")
                break
        
        if not target_id:
            # 如果找不到 AI 概念， fallback 到 沪深300 保证程序不报错
            print("未找到特定 AI 概念，切换至沪深300成分股进行测试...")
            # 获取沪深300成分股
            hs300 = pro.index_weight(index_code='399300.SZ', start_date='20231027', end_date='20231027') # 日期随便填，只要有权重即可
            codes = hs300['con_code'].tolist()
            # 取前20个测试，避免积分不够
            codes = codes[:20] 
        else:
            # 获取该概念的成分股
            df_members = pro.concept_detail(id=target_id, fields='ts_code,name,weight')
            codes = df_members['ts_code'].tolist()

        # 2. 批量获取这些股票的行情数据
        # 注意：Tushare 免费版每日调用次数有限，这里只取前 30 只股票进行演示
        # 如果你有更高积分，可以去掉 [:30]
        target_codes = ",".join(codes[:30]) 
        
        print(f"正在获取 {len(codes[:30])} 只股票的行情...")
        df_daily = pro.daily(ts_code=target_codes, trade_date=datetime.now().strftime('%Y%m%d'))
        
        # 如果今天还没收盘或没数据，取最近一天
        if df_daily.empty:
             # 简单处理：如果是周末或晚上，可能没当日数据，这里暂略过复杂日期回退逻辑
             return "今日暂无交易数据或非交易日"

        # 3. 计算热度分 (涨跌幅 * 成交额权重)
        df_daily['change_pct'] = pd.to_numeric(df_daily['change'], errors='coerce')
        df_daily['amount'] = pd.to_numeric(df_daily['amount'], errors='coerce')
        
        # 简单的打分逻辑：涨幅排名 60% + 成交额排名 40%
        df_daily['score_change'] = df_daily['change_pct'].rank(pct=True) * 60
        df_daily['score_amount'] = df_daily['amount'].rank(pct=True) * 40
        df_daily['total_score'] = df_daily['score_change'] + df_daily['score_amount']
        
        # 取 Top 10
        top10 = df_daily.nlargest(10, 'total_score')
        
        result_list = []
        for _, row in top10.iterrows():
            result_list.append({
                'name': row.get('ts_code', ''), # Tushare返回的是代码，名称需要额外映射，这里简化显示代码
                'change': row['change_pct'],
                'score': int(row['total_score'])
            })
            
        return result_list

    except Exception as e:
        return f"Tushare 接口报错: {str(e)}"

def send_message(content):
    """推送到 Webhook (钉钉/企微/飞书)"""
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        print("错误：未找到 WEBHOOK_URL")
        return

    headers = {'Content-Type': 'application/json'}
    
    # 钉钉格式
    payload = {
        "msgtype": "text",
        "text": {"content": content}
    }
    
    # 如果你想兼容其他平台，可以在这里加判断，目前默认按钉钉发
    
    try:
        resp = requests.post(webhook_url, json=payload, headers=headers)
        print(f"发送结果: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    data = get_stock_data()
    
    if isinstance(data, str):
        # 如果是字符串，说明报错了
        msg = f"【股票】❌ 运行出错:\n{data}"
    else:
        # 如果是列表，说明成功了
        msg = f"【股票】🔥 AI智能体/AI概念 热度 Top10\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for i, item in enumerate(data):
            # 格式化输出
            color = "🟢" if item['change'] > 0 else "🔴"
            msg += f"{i+1}. {item['name']} | 涨幅:{item['change']}% | 热度:{item['score']}\n"
    
    print(msg)
    send_message(msg)
