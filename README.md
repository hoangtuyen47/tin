# 📰 FocusNews AI — Trang Tin Tức Cá Nhân Hoá & Không Quảng Cáo

> Hệ thống đọc tin tức cá nhân hoá, tự động tổng hợp từ các báo lớn trong nước & quốc tế, loại bỏ 100% quảng cáo, có trợ lý AI tóm tắt diễn biến 24h qua và tự động cập nhật miễn phí qua GitHub Actions + GitHub Pages.

---

## 🌟 Tính Năng Nổi Bật

1. **100% Không Quảng Cáo:** Giao diện tối giản (Clean Reader View), chỉ tập trung vào thông tin cốt lõi.
2. **Nguồn Báo Chí Uy Tín & Đa Chiều:**
   - **AI & Công nghệ:** TechCrunch, The Verge, MIT Technology Review, VnExpress Số hoá.
   - **Thời sự Quốc tế:** BBC World, Al Jazeera, Reuters, VnExpress Thế giới.
   - **Giáo dục & Khoa học:** ScienceDaily, EdSurge, Tuổi Trẻ Giáo dục.
3. **Trợ Lý AI Tóm Tắt Ngày Hôm Qua (Daily Briefing):**
   - Đúc kết ngắn gọn các sự kiện nóng nhất trong 24 giờ qua.
   - Chia rõ 3 mục: Quốc tế, Đột phá AI, Giáo dục & Khoa học.
4. **Tóm Tắt 3 Ý Chính & Tự Động Dịch Song Ngữ:**
   - Tin quốc tế tự động dịch sang tiếng Việt chuẩn mực báo chí.
   - AI tóm tắt 3 gạch đầu dòng mấu chốt, tiết kiệm 90% thời gian đọc.
   - Luôn kèm nút dẫn nguồn gốc minh bạch.
5. **Học Thói Quen Cá Nhân Hoá (Local-first):**
   - Thuật toán ghi nhận các chủ đề bạn đọc nhiều và tự động ưu tiên đưa lên đầu feed.
   - Hỗ trợ Lưu tin (Bookmarks), Ẩn tin không quan tâm.
   - Dữ liệu lưu trong trình duyệt (`localStorage`), bảo mật riêng tư tuyệt đối.

---

## 📁 Cấu Trúc Dự Án

```
ai-news-hub/
│
├── index.html                   # Giao diện Web (chạy trên GitHub Pages hoặc mở trực tiếp)
├── fetcher.py                   # Script cào RSS + Gọi Gemini API dịch & tóm tắt
├── requirements.txt             # Thư viện Python cần thiết
│
├── data/                        # Dữ liệu tin tức được cập nhật tự động
│   ├── news.json                # Danh sách bài báo mới nhất
│   └── recap.json               # Bản tóm tắt "Hôm qua có gì hot?"
│
└── .github/workflows/
    └── update-news.yml          # GitHub Actions tự động chạy mỗi 4 tiếng
```

---

## 🚀 Hướng Dẫn Đưa Lên GitHub & Kích Hoạt Miễn Phí (Trong 3 Phút)

### Bước 1: Tạo Repository trên GitHub
1. Đăng nhập [GitHub](https://github.com/) và bấm **New repository** (đặt tên ví dụ: `my-news-hub`).
2. Chọn chế độ **Public**.

### Bước 2: Đẩy Code lên Repository
Mở Terminal / PowerShell tại thư mục `ai-news-hub` và gõ:
```bash
git init
git add .
git commit -m "feat: initial commit for FocusNews AI"
git branch -M main
git remote add origin https://github.com/<tai-khoan-cua-ban>/my-news-hub.git
git push -u origin main
```

### Bước 3: Thêm Gemini API Key (Miễn Phí)
1. Lấy API key miễn phí tại [Google AI Studio](https://aistudio.google.com/).
2. Vào Repo GitHub của bạn > **Settings** > **Secrets and variables** > **Actions**.
3. Bấm **New repository secret**:
   - **Name:** `GEMINI_API_KEY`
   - **Secret:** Dán mã API Key của bạn vào > Bấm **Add secret**.

### Bước 4: Bật GitHub Pages & Cấp Quyền Tự Động Chạy
1. Vào **Settings** > **Pages** > Tại mục **Build and deployment / Branch**, chọn branch `main` và thư mục `/ (root)` > Bấm **Save**.
2. Vào **Settings** > **Actions** > **General** > Kéo xuống mục **Workflow permissions** > Chọn **Read and write permissions** > Bấm **Save** (để GitHub Actions tự commit dữ liệu tin mới vào repo).

Sau 1-2 phút, bạn có thể truy cập trang tin tức cá nhân tại:
`https://<tai-khoan-cua-ban>.github.io/my-news-hub/`

---

## 💻 Xem Thử Ngay Trên Máy Tính (Local Preview)
Chỉ cần nhấp đúp chuột vào file `index.html` trong thư mục này để mở trực tiếp trên trình duyệt Chrome / Edge!
