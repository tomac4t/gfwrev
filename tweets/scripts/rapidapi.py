import requests
import json
import time

def fetch_twitter_history(user_id, api_key):
    url = "https://twitter-api47.p.rapidapi.com/v3/user/tweets-and-replies"
    headers = {
        "x-rapidapi-host": "twitter-api47.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    all_tweets = []
    cursor = None
    page = 1

    print(f"开始抓取用户 {user_id} 的推文...")

    while True:
        # 构造请求参数
        params = {"userId": user_id}
        if cursor:
            params["cursor"] = cursor

        try:
            response = requests.get(url, headers=headers, params=params)
            
            # 检查状态码
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                print(response.text)
                break

            res_data = response.json()
            tweets = res_data.get("data", [])
            
            if not tweets:
                print("未发现更多推文，抓取结束。")
                break

            # 存储推文
            all_tweets.extend(tweets)
            print(f"已抓取第 {page} 页，当前累计推文数: {len(all_tweets)}")

            # 获取下一页的 cursor
            pagination = res_data.get("pagination", {})
            cursor = pagination.get("nextCursor")

            # 如果没有 nextCursor，说明已经到头了
            if not cursor:
                print("到达最后一页。")
                break

            # 翻页计数
            page += 1
            
            # 建议加上短时间休眠，避免触发 API 频率限制（Rate Limit）
            time.sleep(1)

        except Exception as e:
            print(f"发生错误: {e}")
            break

    return all_tweets

if __name__ == "__main__":
    # 配置信息
    USER_ID = "80831118"
    API_KEY = "RAPIDAPI_KEY"
    
    # 执行抓取
    results = fetch_twitter_history(USER_ID, API_KEY)

    # 将结果保存为 JSON 文件
    file_name = f"tweets_user_{USER_ID}.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\n抓取完成！总计推文: {len(results)}")
    print(f"数据已保存至: {file_name}")