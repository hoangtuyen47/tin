import os
import json
import time
import datetime
from dateutil import parser as date_parser
import feedparser

# Danh sách nguồn tin RSS chất lượng cao
RSS_FEEDS = [
    # --- CÔNG NGHỆ & AI ---
    {
        "name": "TechCrunch AI",
        "category": "AI & Công nghệ",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "lang": "en"
    },
    {
        "name": "The Verge Tech",
        "category": "AI & Công nghệ",
        "url": "https://www.theverge.com/rss/index.xml",
        "lang": "en"
    },
    {
        "name": "MIT Technology Review",
        "category": "AI & Công nghệ",
        "url": "https://www.technologyreview.com/feed/",
        "lang": "en"
    },
    # --- THỜI SỰ QUỐC TẾ ---
    {
        "name": "BBC News (World)",
        "category": "Thời sự Quốc tế",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "lang": "en"
    },
    {
        "name": "Al Jazeera English",
        "category": "Thời sự Quốc tế",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "lang": "en"
    },
    # --- GIÁO DỤC & KHOA HỌC ---
    {
        "name": "ScienceDaily",
        "category": "Giáo dục & Khoa học",
        "url": "https://www.sciencedaily.com/rss/top/science.xml",
        "lang": "en"
    },
    {
        "name": "EdSurge News",
        "category": "Giáo dục & Khoa học",
        "url": "https://www.edsurge.com/articles_rss",
        "lang": "en"
    },
    # --- BÁO VIỆT NAM UY TÍN ---
    {
        "name": "VnExpress Thế Giới",
        "category": "Thời sự Quốc tế",
        "url": "https://vnexpress.net/rss/the-gioi.rss",
        "lang": "vi"
    },
    {
        "name": "VnExpress Khoa Học / Số Hoá",
        "category": "AI & Công nghệ",
        "url": "https://vnexpress.net/rss/so-hoa.rss",
        "lang": "vi"
    },
    {
        "name": "Tuổi Trẻ Giáo Dục",
        "category": "Giáo dục & Khoa học",
        "url": "https://tuoitre.vn/rss/giao-duc.rss",
        "lang": "vi"
    }
]

def parse_date(entry):
    for key in ("published", "updated", "created"):
        if hasattr(entry, key):
            try:
                return date_parser.parse(getattr(entry, key))
            except Exception:
                pass
    return datetime.datetime.now(datetime.timezone.utc)

def fetch_all_feeds(max_per_feed=5):
    print("⏳ Đang cào tin tức từ các nguồn RSS...")
    articles = []
    seen_urls = set()

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries:
                link = entry.get("link", "").strip()
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                pub_date = parse_date(entry)
                summary_raw = entry.get("summary", "") or entry.get("description", "")
                # Bỏ tag html cơ bản nếu có
                import re
                clean_summary = re.sub(r"<[^>]+>", "", summary_raw).strip()

                articles.append({
                    "id": f"art_{len(articles)+1}",
                    "title": entry.get("title", "").strip(),
                    "link": link,
                    "source": feed_info["name"],
                    "category": feed_info["category"],
                    "lang": feed_info["lang"],
                    "published_at": pub_date.isoformat(),
                    "timestamp": int(pub_date.timestamp()),
                    "original_summary": clean_summary[:500]
                })
                count += 1
                if count >= max_per_feed:
                    break
            print(f"  ✓ {feed_info['name']}: Lấy được {count} tin.")
        except Exception as e:
            print(f"  ✗ Lỗi khi lấy {feed_info['name']}: {e}")

    # Sắp xếp tin mới nhất lên đầu
    articles.sort(key=lambda x: x["timestamp"], reverse=True)
    return articles

def enrich_with_gemini(articles, api_key=None):
    """
    Sử dụng Gemini API để dịch sang tiếng Việt, tóm tắt 3 ý chính, 
    và trích xuất từ khoá cho mỗi bài viết.
    Nếu không có API key, áp dụng mock/fallback cơ bản để chạy thử offline.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("⚠️ Không tìm thấy GEMINI_API_KEY. Áp dụng chế độ mô phỏng (Mock mode)...")
        for a in articles:
            a["title_vi"] = a["title"] if a["lang"] == "vi" else f"[Dịch] {a['title']}"
            a["summary_points"] = [
                a["original_summary"][:150] or "Nội dung tóm tắt cập nhật từ bài báo gốc.",
                f"Nguồn tin chính thống: {a['source']}.",
                "Nhấn 'Đọc nguồn gốc' để xem chi tiết đầy đủ không quảng cáo."
            ]
            a["importance_score"] = 7
        return articles, generate_mock_recap(articles)

    print("🤖 Đang kết nối Gemini API để dịch, tóm tắt và đánh giá bài viết...")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Batch xử lý 10 bài nổi bật nhất để tối ưu token & tốc độ
        processed_articles = []
        for i, a in enumerate(articles[:25]):
            prompt = f"""
Bạn là trợ lý biên tập tin tức cao cấp. Hãy xử lý bài báo sau:
- Tiêu đề gốc: {a['title']}
- Nguồn: {a['source']}
- Tóm tắt gốc: {a['original_summary']}
- Ngôn ngữ gốc: {a['lang']}

Yêu cầu xuất ra định dạng JSON duy nhất (không bọc trong markdown hoặc text khác) gồm:
{{
  "title_vi": "Tiêu đề dịch sang tiếng Việt ngắn gọn, hấp dẫn, chuẩn mực báo chí (nếu đã là tiếng Việt thì giữ nguyên)",
  "summary_points": [
    "Ý chính 1 (quan trọng nhất)",
    "Ý chính 2 (chi tiết quan trọng)",
    "Ý chính 3 (tác động/bối cảnh)"
  ],
  "importance_score": 1-10 (mức độ ảnh hưởng toàn cầu/xã hội, số nguyên),
  "tags": ["Từ khoá 1", "Từ khoá 2"]
}}
"""
            try:
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                data = json.loads(resp.text)
                a["title_vi"] = data.get("title_vi", a["title"])
                a["summary_points"] = data.get("summary_points", [a["original_summary"][:150]])
                a["importance_score"] = data.get("importance_score", 6)
                a["tags"] = data.get("tags", [a["category"]])
            except Exception as e:
                print(f"Lỗi khi xử lý bài '{a['title']}': {e}")
                a["title_vi"] = a["title"]
                a["summary_points"] = [a["original_summary"][:150] or "Đọc thêm tại link gốc."]
                a["importance_score"] = 5
                a["tags"] = [a["category"]]
            processed_articles.append(a)

        # Lấy thêm các bài còn lại (chưa qua AI xử lý sâu thì để tiêu đề gốc)
        for a in articles[25:]:
            a["title_vi"] = a["title"]
            a["summary_points"] = [a["original_summary"][:150] or "Chi tiết xem tại nguồn."]
            a["importance_score"] = 4
            a["tags"] = [a["category"]]
            processed_articles.append(a)

        # Tạo Daily Briefing / Yesterday Recap
        recap = generate_gemini_recap(client, processed_articles)
        return processed_articles, recap

    except Exception as e:
        print(f"✗ Lỗi khi dùng Gemini API: {e}. Chuyển sang fallback.")
        return articles, generate_mock_recap(articles)

def generate_gemini_recap(client, articles):
    print("📰 Đang tạo Trợ lý tóm tắt ngày hôm qua (Daily Briefing)...")
    sample_context = "\n".join([f"- [{a['category']}] {a['title_vi']} (Nguồn: {a['source']})" for a in articles[:15]])
    
    prompt = f"""
Dựa trên các sự kiện tin tức thu thập được gần nhất sau đây:
{sample_context}

Hãy đóng vai trò Biên tập viên tin tức AI, viết bản 'ĐIỂM TIN NỔI BẬT HÔM QUA' (Daily Briefing) cho người đọc bận rộn.
Tập trung chính vào 3 trụ cột:
1. Thời sự & Quan hệ Quốc tế
2. Trí tuệ nhân tạo (AI) & Đột phá Công nghệ
3. Giáo dục & Khoa học

Trả về kết quả định dạng JSON duy nhất:
{{
  "date": "{datetime.datetime.now().strftime('%d/%m/%Y')}",
  "greeting": "Chào buổi sáng! Dưới đây là 3 phút tóm tắt tất cả những diễn biến đáng chú ý nhất trong 24 giờ qua.",
  "highlights": [
    {{
      "category": "Thời sự Quốc tế",
      "headline": "Tiêu đề diễn biến nóng nhất",
      "content": "Đoạn phân tích ngắn gọn 2-3 câu về bối cảnh và tác động."
    }},
    {{
      "category": "AI & Công nghệ",
      "headline": "Đột phá công nghệ đáng lưu ý",
      "content": "Đoạn phân tích ngắn gọn 2-3 câu về công cụ hoặc xu hướng mới."
    }},
    {{
      "category": "Giáo dục & Khoa học",
      "headline": "Chuyển động giáo dục / nghiên cứu",
      "content": "Đoạn phân tích ngắn gọn 2-3 câu."
    }}
  ],
  "quick_takeaway": "Một câu đúc kết hoặc xu hướng quan trọng cần theo dõi trong ngày hôm nay."
}}
"""
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(resp.text)
    except Exception as e:
        print(f"Lỗi khi tạo recap bằng AI: {e}")
        return generate_mock_recap(articles)

def generate_mock_recap(articles):
    return {
        "date": datetime.datetime.now().strftime('%d/%m/%Y'),
        "greeting": "Chào buổi sáng! Dưới đây là bản tóm tắt nhanh những diễn biến đáng chú ý trong 24 giờ qua dành cho bạn.",
        "highlights": [
            {
                "category": "Thời sự Quốc tế",
                "headline": "Căng thẳng địa chính trị và nỗ lực ngoại giao đa phương",
                "content": "Các hội nghị thượng đỉnh quốc tế ghi nhận nhiều cam kết mới về hợp tác kinh tế và biến đổi khí hậu giữa các cường quốc, nhằm giảm thiểu rủi ro chuỗi cung ứng toàn cầu."
            },
            {
                "category": "AI & Công nghệ",
                "headline": "Làn sóng AI thế hệ mới tập trung vào Agent tự hành",
                "content": "Các phòng lab lớn tiếp tục công bố các kiến trúc mô hình có khả năng suy luận đa bước (reasoning models) và tích hợp sâu vào quy trình làm việc tự động."
            },
            {
                "category": "Giáo dục & Khoa học",
                "headline": "Đổi mới phương pháp học tập kết hợp công nghệ cá nhân hoá",
                "content": "Nhiều trường đại học hàng đầu đang thí điểm đưa các công cụ trợ lý AI vào đồng hành cùng người học, giúp giảm áp lực và nâng cao tính tương tác."
            }
        ],
        "quick_takeaway": "Làn sóng ứng dụng AI đang chuyển dịch mạnh mẽ từ 'thử nghiệm tính năng' sang 'tối ưu hoá công việc thực tế' trên toàn cầu."
    }

def main():
    os.makedirs("data", exist_ok=True)
    raw_articles = fetch_all_feeds(max_per_feed=4)
    processed_articles, recap = enrich_with_gemini(raw_articles)

    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã lưu {len(processed_articles)} tin vào data/news.json")

    with open("data/recap.json", "w", encoding="utf-8") as f:
        json.dump(recap, f, ensure_ascii=False, indent=2)
    print("✓ Đã lưu bản tóm tắt ngày hôm qua vào data/recap.json")

if __name__ == "__main__":
    main()
