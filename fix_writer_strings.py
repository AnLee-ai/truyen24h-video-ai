import sys
content = open(r'd:\222\src\writer.py', 'r', encoding='utf-8').read()

replacements = {
    'BÃ¡ÂºÂ®T Ã„Â\x90Ã¡ÂºÂ¦U QUY TRÃƒÅ’NH VIÃ¡ÂºÂ¾T CHÃ†Â¯Ã†Â\xa0NG MÃ¡Â»Å¡I': 'BẮT ĐẦU QUY TRÌNH VIẾT CHƯƠNG MỚI',
    'BÃ¡ÂºÂ®T Ã„â€˜Ã¡ÂºÂ¦U QUY TRÃƒÅ’NH VIÃ¡ÂºÂ¾T CHÃ†Â¯Ã†Â NG MÃ¡Â»Å¡I': 'BẮT ĐẦU QUY TRÌNH VIẾT CHƯƠNG MỚI',
    'ChÃ†Â°Ã†Â\xa0ng': 'Chương',
    'ChÃ\xa0Â°Ã\xa0Â¡ng': 'Chương',
    'Ã„Â\x90ÃƒÂ£ hoÃƒÂ\xa0n thÃƒÂ\xa0nh cÃƒÂ¡c tÃ¡ÂºÂ\xadt': 'Đã hoàn thành các tập',
    'Ã„â€˜ÃƒÂ£ hoÃƒÂ n thÃƒÂ nh cÃƒÂ¡c tÃ¡ÂºÂ­p': 'Đã hoàn thành các tập',
    'Bá»\x98 KIá»\x8cM TRA Tá»° Ä\x90á»\x9eNG Báº¢O Vá»\x86 CHÆ¯Æ\xa0NG TRUYá»\x86N': 'BỘ KIỂM TRA TỰ ĐỘNG BẢO VỆ CHƯƠNG TRUYỆN',
    'GÃ¡Â»Â§i yÃƒÂªu cÃ¡ÂºÂ§u sÃƒÂ¡ng tÃƒÂ¡c tÃ¡Â»\x9bi Inkos': 'Gửi yêu cầu sáng tác tới Inkos',
    'GÃ¡Â»Â§i yÃƒÂªu cÃ¡ÂºÂ§u sÃƒÂ¡ng tÃƒÂ¡c tÃ¡Â»â€ºi Inkos': 'Gửi yêu cầu sáng tác tới Inkos',
    'LÃ¡Â»\x97i gÃ¡Â»Â\x8di Inkos Cloud': 'Lỗi gọi Inkos Cloud',
    'LÃ¡Â»â€œi gÃ¡Â»Â\x8di Inkos Cloud': 'Lỗi gọi Inkos Cloud',
    'LÃ¡Â»â€œi gÃ¡Â»\x9di Inkos Cloud': 'Lỗi gọi Inkos Cloud',
    '[SUCCESS] Ã¢Â¡Â¡ InkOS Writer Agent': '[SUCCESS] ✨ InkOS Writer Agent',
    'TÃ¡ÂºÂ¡o kÃ¡Â»â€¹ch bÃ¡ÂºÂ£n mÃ¢Â°Ã¡Â»Â£t mÃƒÂ thÃƒÂ nh cÃƒÂ´ng!': 'Tạo kịch bản mượt mà thành công!',
    'tÃ¡Â»Â«': 'từ',
    'tÃ¡Â»\x9bi': 'tới'
}

for k, v in replacements.items():
    content = content.replace(k, v)

# Blanket catch for some common ones
content = content.replace('Ã„Â\x90', 'Đ')
content = content.replace('Ã„â€˜', 'đ')

open(r'd:\222\src\writer.py', 'w', encoding='utf-8').write(content)
print("Strings replaced!")
