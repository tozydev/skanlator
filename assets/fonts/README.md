# Khai Báo Nguồn Gốc Font Chữ Sinh Dữ Liệu Thử Nghiệm

Tài liệu này liệt kê chi tiết danh sách các font chữ đã được sử dụng nội bộ để tạo ra tập dữ liệu tổng hợp (Synthetic
Test Data) trong dự án này.

> [!IMPORTANT]
> Do quy định nghiêm ngặt về bản quyền và phân phối từ các nhà thiết kế, **toàn bộ tệp tin font (.ttf, .otf) gốc không
> được đính kèm trong mã nguồn công khai này**.

## 📁 Cấu Trúc Thư Mục

```text
assets/fonts/
├── dialog/                 # Nhóm font sử dụng cho nội dung lời thoại (Speech Dialogs)
│   └── .gitkeep
└── sfx/                    # Nhóm font sử dụng cho hiệu ứng âm thanh (Sound Effects)
    └── .gitkeep
```

## 📜 Chi Tiết Bản Quyền & Nguồn Gốc Font

Tất cả các font sử dụng dưới đây đều tuân thủ đúng điều khoản **Sử dụng phi thương mại / Nghiên cứu / Cá nhân (
Personal / Non-Commercial Use Only)** từ các tác giả và hãng font.

### 1. Nhóm Font Lời Thoại (`dialog/`)

| Tên Font Gốc         | Nhà Thiết Kế / Studio   | Giấy Phép Bản Quyền               |
|:---------------------|:------------------------|:----------------------------------|
| Action Man           | Iconian Fonts           | Miễn phí cá nhân (Charityware)    |
| Anime Ace 2.0 BB     | Blambot                 | Miễn phí cho truyện tranh độc lập |
| Digital Strip 2.0 BB | Blambot                 | Miễn phí cho truyện tranh độc lập |
| Komika Hand          | Vigilante Typeface Corp | Miễn phí cá nhân (Freeware)       |
| LetterOMatic! BB     | Blambot                 | Miễn phí cho truyện tranh độc lập |
| Manly Man            | Chequered Ink           | Miễn phí cho mục đích cá nhân     |
| Milk Mustache BB     | Blambot                 | Miễn phí cho truyện tranh độc lập |
| Plot Hole            | Comicraft / Out Of Step | Bản thử nghiệm phi thương mại     |
| WhizBang Roman       | Studio 2F / Comicraft   | Bản thử nghiệm phi thương mại     |

### 2. Nhóm Font Hiệu Ứng (`sfx/`)

| Tên Font Gốc       | Nhà Thiết Kế / Studio     | Giấy Phép Bản Quyền               |
|:-------------------|:--------------------------|:----------------------------------|
| Action Man Shaded  | Iconian Fonts             | Miễn phí cá nhân (Charityware)    |
| Badaboom BB        | Blambot                   | Miễn phí cho truyện tranh độc lập |
| Chewed Pen BB      | Blambot                   | Miễn phí cho truyện tranh độc lập |
| Crash Landing BB   | Blambot                   | Miễn phí cho truyện tranh độc lập |
| Damn Noisy Kids BB | Blambot                   | Miễn phí cho truyện tranh độc lập |
| Firepower BB       | Blambot                   | Miễn phí cho truyện tranh độc lập |
| Humana             | Linotype / Type Directors | Bản thử nghiệm / Miễn phí cá nhân |
| Komika Axis        | Vigilante Typeface Corp   | Miễn phí cá nhân (Freeware)       |
| Komika Slim        | Vigilante Typeface Corp   | Miễn phí cá nhân (Freeware)       |
| Wishful Thinking   | Jonathan S. Harris        | Miễn phí cho mục đích cá nhân     |

## 📢 Tuyên Bố Miễn Trừ Trách Nhiệm

1. **Tính Minh Bạch**: Việc liệt kê danh sách font này chỉ nhằm mục đích ghi nhận công sức (credit) của các nhà thiết kế
   và làm rõ phương pháp luận tạo dữ liệu cho các bài kiểm thử (test cases).
2. **Trách Nhiệm Thương Mại**: Nếu bạn sử dụng lại mã nguồn này hoặc tập dữ liệu mẫu để phát triển các sản phẩm thương
   mại hoặc sinh lợi nhuận, bạn **bắt buộc phải thay thế** các font trên bằng các font có bản quyền thương mại hợp pháp
   hoặc tự mua giấy phép thương mại (Commercial License) trực tiếp từ các studio sở hữu (như Blambot, Comicraft,
   Linotype...).
