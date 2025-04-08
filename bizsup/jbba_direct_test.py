#!/usr/bin/env python
# 직접 URL 처리 테스트

import requests
import html2text
import os
from pathlib import Path
from bs4 import BeautifulSoup
import re

# HTML을 Markdown으로 변환
def convert_html_to_markdown(html_content):
    h2t = html2text.HTML2Text()
    h2t.ignore_links = False
    h2t.ignore_images = False
    h2t.ignore_tables = False
    h2t.body_width = 0
    h2t.unicode_snob = True
    return h2t.handle(html_content)

# 메인 실행 함수
def main():
    # 설정
    url = "https://www.jbba.kr/bbs/board.php?bo_table=sub01_09&wr_id=1529"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    output_dir = Path("jbba_output")
    output_dir.mkdir(exist_ok=True)
    
    # URL 요청
    print(f"가져오는 URL: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"오류: HTTP 상태 코드 {response.status_code}")
        return
    
    # HTML 파싱
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 제목 추출
    title = soup.select_one('#bo_v_title')
    if title:
        title = title.get_text().strip()
    else:
        title = "제목 없음"
    
    print(f"추출된 제목: {title}")
    
    # 본문 내용 추출
    content = soup.select_one('#bo_v_con')
    if not content:
        print("본문을 찾을 수 없습니다.")
        return
    
    # HTML을 Markdown으로 변환
    content_html = str(content)
    content_markdown = convert_html_to_markdown(content_html)
    
    # 파일명에 사용할 수 없는 문자 제거
    safe_title = ''.join(c for c in title if c.isalnum() or c in ' ._-').strip()
    safe_title = safe_title[:50]
    
    # 마크다운 파일로 저장
    md_filename = output_dir / f"{safe_title}.md"
    with open(md_filename, 'w', encoding='utf-8') as f:
        # 메타데이터 추가
        f.write(f"# {title}\n\n")
        f.write(f"원본 URL: {url}\n\n")
        
        # 게시글 정보 추가
        author = soup.select_one('.bo_v_info strong, .sv_member')
        if author:
            f.write(f"작성자: {author.get_text().strip()}\n\n")
        
        date = soup.select_one('.bo_v_info .if_date, .bo_date')
        if date:
            f.write(f"작성일: {date.get_text().strip()}\n\n")
        
        # 본문 내용
        f.write("## 내용\n\n")
        f.write(content_markdown)
    
    print(f"마크다운 파일 저장 완료: {md_filename}")
    
    # 원본 HTML 파일 저장 (디버깅용)
    with open(output_dir / "original.html", 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print("완료")

if __name__ == "__main__":
    main()