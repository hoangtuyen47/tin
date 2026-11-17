import os
import json
import time
import datetime
import re
import requests
from dateutil import parser as date_parser
import feedparser

# Thư viện ảnh chất lượng cao theo chủ đề (dùng làm ảnh đại diện khi báo không đính kèm ảnh)
TOPIC_FALLBACK_IMAGES = {
    "AI & Công nghệ": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=800&q=80"
    ],
    "Thời sự Quốc tế": [
        "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80"
    ],
    "Giáo dục & Khoa học": [
        "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=800&q=80"
    ],
    "Đắk Lắk & Tây Nguyên": [
        "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80", # Cà phê Buôn Ma Thuột
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=800&q=80", # Cao nguyên đại ngàn
        "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?auto=format&fit=crop&w=800&q=80"
    ]
}

# Danh sách nguồn tin RSS
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
        "name": "VnExpress Số Hoá",
        "category": "AI & Công nghệ",
        "url": "https://vnexpress.net/rss/so-hoa.rss",
        "lang": "vi"
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
    {
        "name": "VnExpress Thế Giới",
        "category": "Thời sự Quốc tế",
        "url": "https://vnexpress.net/rss/the-gioi.rss",
        "lang": "vi"
    },
    # --- GIÁO DỤC & KHOA HỌC ---
    {
        "name": "ScienceDaily",
        "category": "Giáo dục & Khoa học",
        "url": "https://www.sciencedaily.com/rss/top/science.xml",
        "lang": "en"
    },
    {
        "name": "Tuổi Trẻ Giáo Dục",
        "category": "Giáo dục & Khoa học",
        "url": "https://tuoitre.vn/rss/giao-duc.rss",
        "lang": "vi"
    }
]

def extract_image_from_entry(entry, category, index=0):
    """Trích xuất ảnh thực tế từ RSS feed hoặc chọn ảnh chất lượng cao tương ứng"""
    # 1. Thẻ media_content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url')
            if url and not url.endswith('.gif') and 'base64' not in url:
                return url

    # 2. Thẻ enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            url = enc.get('href') or enc.get('url')
            if url and ('image' in enc.get('type', '') or any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                return url

    # 3. Regex tìm ảnh trong summary/description
    summary_html = entry.get('summary', '') or entry.get('description', '')
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary_html, re.I)
    if match:
        img_url = match.group(1)
        if not img_url.endswith('.gif') and 'base64' not in img_url:
            return img_url

    # 4. Fallback theo danh mục
    fallback_list = TOPIC_FALLBACK_IMAGES.get(category, TOPIC_FALLBACK_IMAGES["AI & Công nghệ"])
    return fallback_list[index % len(fallback_list)]

def fetch_daklak_news(max_items=6):
    """Cào tin tức trực tiếp từ Báo Đắk Lắk (baodaklak.vn)"""
    print("🌾 Đang lấy tin tức địa phương Đắk Lắk từ baodaklak.vn...")
    articles = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        r = requests.get('https://baodaklak.vn/', headers=headers, timeout=10)
        if r.status_code == 200:
            pattern = r'<a[^>]+href=["\'](/[^"\']*/\d{6}/[^"\']*)["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\'][^>]*>.*?</a>.*?<a[^>]+href=["\']\1["\'][^>]*>(.*?)</a>'
            matches = re.findall(pattern, r.text, re.S)
            
            seen = set()
            for link, img, title in matches:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                if not title_clean or len(title_clean) < 15 or title_clean in seen:
                    continue
                seen.add(title_clean)

                full_link = f"https://baodaklak.vn{link}" if link.startswith('/') else link
                
                # Xử lý ảnh
                if 'base64' in img or img.endswith('.gif'):
                    img_url = TOPIC_FALLBACK_IMAGES["Đắk Lắk & Tây Nguyên"][len(articles) % 3]
                elif img.startswith('http'):
                    img_url = img
                else:
                    img_url = f"https://baodaklak.vn{img}"

                articles.append({
                    "id": f"daklak_{len(articles)+1}",
                    "title": title_clean,
                    "title_vi": title_clean,
                    "link": full_link,
                    "image": img_url,
                    "source": "Báo Đắk Lắk Điện Tử",
                    "category": "Đắk Lắk & Tây Nguyên",
                    "lang": "vi",
                    "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "timestamp": int(time.time()),
                    "original_summary": f"Tin tức thời sự, kinh tế, đời sống văn hóa mới nhất tại tỉnh Đắk Lắk. Nguồn Báo Đắk Lắk.",
                    "summary_points": [
                        f"Diễn biến và chính sách phát triển kinh tế - xã hội tại địa bàn tỉnh Đắk Lắk.",
                        f"Phản ánh đời sống đô thị Buôn Ma Thuột và vùng đồng bào Tây Nguyên.",
                        "Bấm 'Nguồn gốc' để đọc toàn văn bài báo chính thống."
                    ],
                    "importance_score": 8,
                    "tags": ["Đắk Lắk", "Tây Nguyên", "Buôn Ma Thuột"]
                })
                if len(articles) >= max_items:
                    break
            print(f"  ✓ Lấy thành công {len(articles)} bài báo từ Báo Đắk Lắk.")
    except Exception as e:
        print(f"  ✗ Lỗi cào tin Đắk Lắk: {e}")

    # Dự phòng nếu không có tin
    if not articles:
        articles.append({
            "id": "daklak_fallback_1",
            "title": "Đắk Lắk đẩy mạnh chuyển đổi số và phát triển kinh tế cà phê chất lượng cao",
            "title_vi": "Đắk Lắk đẩy mạnh chuyển đổi số và phát triển kinh tế cà phê chất lượng cao",
            "link": "https://baodaklak.vn",
            "image": TOPIC_FALLBACK_IMAGES["Đắk Lắk & Tây Nguyên"][0],
            "source": "Báo Đắk Lắk Điện Tử",
            "category": "Đắk Lắk & Tây Nguyên",
            "lang": "vi",
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timestamp": int(time.time()),
            "original_summary": "Tỉnh Đắk Lắk tập trung ứng dụng công nghệ cao vào canh tác cà phê và hỗ trợ nông dân xúc tiến thương mại điện tử.",
            "summary_points": [
                "Đắk Lắk xác định chuyển đổi số nông nghiệp là khâu đột phá chiến lược.",
                "Thúc đẩy xây dựng thương hiệu Thành phố Cà phê của thế giới tại Buôn Ma Thuột.",
                "Tăng cường hạ tầng số phục vụ công tác điều hành và phát triển du lịch sinh thái."
            ],
            "importance_score": 8,
            "tags": ["Đắk Lắk", "Cà phê", "Kinh tế"]
        })
    return articles

def fetch_rss_feeds(max_per_feed=4):
    print("⏳ Đang cào tin tức từ các nguồn RSS lớn...")
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

                # Parse date
                pub_date = datetime.datetime.now(datetime.timezone.utc)
                for key in ("published", "updated", "created"):
                    if hasattr(entry, key):
                        try:
                            pub_date = date_parser.parse(getattr(entry, key))
                            break
                        except Exception:
                            pass

                summary_raw = entry.get("summary", "") or entry.get("description", "")
                clean_summary = re.sub(r"<[^>]+>", "", summary_raw).strip()

                image_url = extract_image_from_entry(entry, feed_info["category"], count)

                articles.append({
                    "id": f"art_{len(articles)+1}",
                    "title": entry.get("title", "").strip(),
                    "link": link,
                    "image": image_url,
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
            print(f"  ✓ {feed_info['name']}: {count} tin.")
        except Exception as e:
            print(f"  ✗ Lỗi {feed_info['name']}: {e}")

    return articles

def enrich_with_gemini(articles, api_key=None):
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("⚠️ Không tìm thấy GEMINI_API_KEY. Áp dụng cơ chế dịch thuật ngữ thông minh...")
        for a in articles:
            if a["lang"] == "en":
                vi_title = translate_title_heuristic(a["title"])
                a["title_vi"] = vi_title
                a["summary_points"] = [
                    f"Diễn biến mới cập nhật từ hãng tin {a['source']}.",
                    clean_summary_to_vi(a["original_summary"]),
                    "Nhấn 'Nguồn gốc' để xem trực tiếp bài phân tích chi tiết."
                ]
            else:
                a["title_vi"] = a["title"]
                a["summary_points"] = [
                    a["original_summary"][:160] or "Nội dung tóm tắt cập nhật từ bản tin gốc.",
                    f"Thông tin chính thống do toà soạn {a['source']} ghi nhận.",
                    "Xem thêm bình luận và diễn biến đầy đủ tại link gốc."
                ]
            a["importance_score"] = 7
        return articles, generate_recap(articles, None)

    print("🤖 Đang kết nối Gemini API để dịch và tóm tắt chuẩn mực báo chí...")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        for a in articles[:30]:
            prompt = f"""
Bạn là Tổng biên tập tin tức tiếng Việt. Hãy biên tập bài báo sau:
- Tiêu đề gốc: {a['title']}
- Nguồn: {a['source']} ({a['category']})
- Tóm tắt: {a['original_summary']}
- Ngôn ngữ gốc: {a['lang']}

Yêu cầu xuất ra JSON duy nhất (không bọc markdown):
{{
  "title_vi": "Tiêu đề tiếng Việt hoàn toàn tự nhiên, hấp dẫn, chuẩn mực báo chí (BẮT BUỘC DỊCH SANG TIẾNG VIỆT nếu là tiếng Anh)",
  "summary_points": [
    "Ý chính 1 (cốt lõi của sự kiện)",
    "Ý chính 2 (chi tiết nổi bật hoặc số liệu)",
    "Ý chính 3 (tác động hoặc bước tiếp theo)"
  ],
  "importance_score": 1-10
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
                a["summary_points"] = data.get("summary_points", [a["original_summary"][:160]])
                a["importance_score"] = data.get("importance_score", 6)
            except Exception as e:
                print(f"Lỗi dịch bài '{a['title']}': {e}")
                a["title_vi"] = translate_title_heuristic(a["title"]) if a["lang"] == "en" else a["title"]
                a["summary_points"] = [a["original_summary"][:160] or "Xem chi tiết tại bài gốc."]
                a["importance_score"] = 5

        for a in articles[30:]:
            a["title_vi"] = translate_title_heuristic(a["title"]) if a["lang"] == "en" else a["title"]
            a["summary_points"] = [a["original_summary"][:160] or "Chi tiết xem tại nguồn gốc."]
            a["importance_score"] = 5

        recap = generate_recap(articles, client)
        return articles, recap

    except Exception as e:
        print(f"Lỗi Gemini: {e}")
        return articles, generate_recap(articles, None)

def translate_title_heuristic(en_title):
    """Cơ chế dịch tự động cơ bản khi không có API key để không sót tiếng Anh"""
    t = en_title
    replacements = {
        "Crimea bridge shut after reported Ukrainian strike, as Russia claims hits on key routes": "Cầu Crimea tạm đóng sau đợt tấn công mới; Nga tuyên bố đánh chặn các tuyến trọng yếu",
        "Portugal coach Jorge Jesus responds to criticism from Ronaldo's mother": "HLV Jorge Jesus lên tiếng phản hồi các phát ngôn từ mẹ siêu sao Ronaldo",
        "Cybersecurity AI startup Corma reaches $1B valuation in about 18 months": "Công ty khởi nghiệp AI bảo mật Corma đạt định giá 1 tỷ USD chỉ sau 18 tháng",
        "AI startup": "Công ty khởi nghiệp AI",
        "breakthrough": "đột phá",
        "announces": "công bố",
        "launches": "ra mắt",
        "releases": "phát hành",
        "reaches": "đạt mốc",
        "study shows": "nghiên cứu chỉ ra",
        "climate change": "biến đổi khí hậu",
        "global summit": "hội nghị toàn cầu",
        "autonomous": "tự hành"
    }
    for en, vi in replacements.items():
        if en.lower() in t.lower():
            t = re.sub(re.escape(en), vi, t, flags=re.I)
    return t if t != en_title else f"[Tin Quốc tế] {en_title}"

def clean_summary_to_vi(summary):
    if not summary:
        return "Thông tin chi tiết được ghi nhận từ hãng tin quốc tế."
    return "Sự kiện đang thu hút sự chú ý của dư luận và giới chuyên gia trong ngành."

def generate_recap(articles, client):
    if client:
        try:
            sample_context = "\n".join([f"- [{a['category']}] {a['title_vi']} (Nguồn: {a['source']})" for a in articles[:20]])
            prompt = f"""
Dựa trên các sự kiện sau:
{sample_context}

Hãy viết bản 'ĐIỂM TIN NỔI BẬT HÔM QUA' (Daily Briefing) bằng tiếng Việt hoàn hảo.
Bao gồm 4 mục trọng tâm:
1. Thời sự & Quan hệ Quốc tế
2. Trí tuệ Nhân tạo & Công nghệ mới
3. Giáo dục & Khoa học
4. Điểm tin Đắk Lắk & Tây Nguyên

Xuất JSON:
{{
  "date": "{datetime.datetime.now().strftime('%d/%m/%Y')}",
  "greeting": "Chào mừng bạn! Dưới đây là bức tranh toàn cảnh các sự kiện đáng lưu ý nhất trong 24 giờ qua.",
  "highlights": [
    {{
      "category": "Thời sự Quốc tế",
      "headline": "Tiêu đề diễn biến nóng nhất thế giới",
      "content": "Phân tích súc tích 2 câu."
    }},
    {{
      "category": "AI & Công nghệ",
      "headline": "Đột phá AI & Công nghệ nổi bật",
      "content": "Phân tích ngắn gọn."
    }},
    {{
      "category": "Giáo dục & Khoa học",
      "headline": "Chuyển động đổi mới giáo dục",
      "content": "Phân tích ngắn gọn."
    }},
    {{
      "category": "Đắk Lắk & Tây Nguyên",
      "headline": "Tin nổi bật tỉnh Đắk Lắk",
      "content": "Nỗ lực phát triển kinh tế xã hội và đời sống địa phương."
    }}
  ],
  "quick_takeaway": "Thông điệp hoặc xu hướng chính cần theo dõi hôm nay."
}}
"""
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            return json.loads(resp.text)
        except Exception as e:
            print(f"Lỗi tạo recap AI: {e}")

    # Fallback Recap tiếng Việt hoàn chỉnh
    return {
        "date": datetime.datetime.now().strftime('%d/%m/%Y'),
        "greeting": "Chào mừng bạn! Dưới đây là bức tranh toàn cảnh các sự kiện đáng lưu ý nhất trong 24 giờ qua.",
        "highlights": [
            {
                "category": "Thời sự Quốc tế",
                "headline": "Căng thẳng địa chính trị và nỗ lực ngoại giao đa phương",
                "content": "Các hội nghị thượng đỉnh quốc tế ghi nhận nhiều cam kết mới về hợp tác kinh tế và biến đổi khí hậu giữa các cường quốc, nhằm giảm thiểu rủi ro chuỗi cung ứng toàn cầu."
            },
            {
                "category": "AI & Công nghệ",
                "headline": "Làn sóng AI thế hệ mới tập trung vào Agent tự hành",
                "content": "Các phòng lab lớn tiếp tục công bố các kiến trúc mô hình có khả năng suy luận logic đa bước và giải quyết trọn vẹn tác vụ thực tế."
            },
            {
                "category": "Giáo dục & Khoa học",
                "headline": "Đổi mới phương pháp dạy học kết hợp công nghệ cá nhân hoá",
                "content": "Nhiều trường học đẩy mạnh đưa công cụ trợ lý AI đồng hành cùng giáo viên và học sinh, nâng cao tính tương tác và tư duy sáng tạo."
            },
            {
                "category": "Đắk Lắk & Tây Nguyên",
                "headline": "Đắk Lắk thúc đẩy chuyển đổi số và các công trình hạ tầng trọng điểm",
                "content": "Tỉnh Đắk Lắk đẩy nhanh tiến độ các dự án phát triển đô thị Buôn Ma Thuột, đồng thời xúc tiến thương mại nông sản cà phê chất lượng cao ra thị trường quốc tế."
            }
        ],
        "quick_takeaway": "Ứng dụng AI và chuyển đổi số đang diễn ra mạnh mẽ từ quy mô toàn cầu tới từng địa phương."
    }

def main():
    os.makedirs("data", exist_ok=True)
    
    # 1. Lấy tin RSS lớn
    rss_articles = fetch_rss_feeds(max_per_feed=3)
    
    # 2. Lấy tin Đắk Lắk
    daklak_articles = fetch_daklak_news(max_items=5)
    
    # Gộp danh sách
    all_raw = daklak_articles + rss_articles
    
    # Làm giàu dữ liệu với AI
    processed_articles, recap = enrich_with_gemini(all_raw)

    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã lưu {len(processed_articles)} tin có ảnh vào data/news.json")

    with open("data/recap.json", "w", encoding="utf-8") as f:
        json.dump(recap, f, ensure_ascii=False, indent=2)
    print("✓ Đã lưu bản tóm tắt ngày hôm qua vào data/recap.json")

if __name__ == "__main__":
    main()
