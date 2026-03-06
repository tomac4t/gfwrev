import json
import os
import requests
from datetime import datetime

def download_image(url, save_path):
    """下载图片并保存到本地"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"下载图片失败: {url}, 错误: {e}")
    return False

def json_to_markdown_with_images(input_json, output_md, image_folder="tweet_images"):
    # 创建存放图片的文件夹
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)

    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
        
        with open(output_md, 'w', encoding='utf-8') as md:
            md.write(f"# 推文存档\n")
            md.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            md.write("---\n\n")

            for tweet in tweets:
                author_info = tweet.get('author', {})
                author_name = author_info.get('name', 'unknown_user')
                username = author_info.get('username', 'unknown_username')
                tweet_id = tweet.get('id', 'unknown_id')
                text = tweet.get('text', '（无内容）').replace('\n', '  \n> ')
                created_at = tweet.get('createdAt', '')
                conv_id = tweet.get('id', '')
                
                # 时间格式化
                if created_at:
                    dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                    display_time = dt.strftime("%Y年%m月%d日 %H:%M:%S")
                else:
                    display_time = "未知时间"

                # 拼接 URL
                tweet_url = f"https://x.com/{username}/status/{conv_id}"
                
                # 写入基本信息
                
                md.write(f"> {text}\n\n")

                # 处理图片
                media_list = tweet.get('media', [])
                if media_list:
                    md.write("\n")
                    for index, media in enumerate(media_list):
                        # 通常图片链接在 'url' 或 'mediaUrl' 字段中
                        img_url = media.get('url') or media.get('mediaUrl')
                        if img_url:
                            # 提取后缀名 (如 .jpg, .png)
                            ext = os.path.splitext(img_url)[1].split('?')[0] or ".jpg"
                            img_name = f"{tweet_id}_{index}{ext}"
                            img_path = os.path.join(image_folder, img_name)
                            
                            print(f"正在下载图片: {img_url} ...")
                            if download_image(img_url, img_path):
                                # 在 Markdown 中插入相对路径
                                md.write(f"![图片]({image_folder}/{img_name})\n\n")

                md.write(f"-- [{author_name}]({tweet_url}), {display_time}\n\n")
                md.write("---\n\n")

        print(f"\n✅ 处理完成！")
        print(f"Markdown 文件: {output_md}")
        print(f"图片保存目录: {image_folder}")

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_json}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

if __name__ == "__main__":
    json_to_markdown_with_images("tweets.json", "twitter_full_archive.md")