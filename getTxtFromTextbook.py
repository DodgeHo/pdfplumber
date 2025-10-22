import pdfplumber
import time

def clean_text(text):
    # 去除多余空行和首尾空格
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

with pdfplumber.open("textbook.pdf") as pdf, open("textbook.txt", "w", encoding="utf-8") as f:
    total_pages = len(pdf.pages)
    print(f"共 {total_pages} 页，开始处理……")
    start_time = time.time()
    for idx, page in enumerate(pdf.pages, 1):
        text = page.extract_text(layout=True)
        if text:
            f.write(clean_text(text))
            f.write("\n\n")  # 每页之间加空行
        elapsed = time.time() - start_time
        avg_per_page = elapsed / idx
        remaining_pages = total_pages - idx
        est_remaining = avg_per_page * remaining_pages
        print(f"正在处理第 {idx}/{total_pages} 页…… 预计剩余时间：{est_remaining:.1f} 秒")
    print("处理完成，文本已保存到 textbook.txt")