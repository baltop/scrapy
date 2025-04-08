#!/usr/bin/env python
"""
파일명 인코딩 테스트 스크립트
- Content-Disposition 헤더에서 파일명 추출 및 인코딩 처리
"""

import requests
import os
from pathlib import Path

# 테스트할 URL
url = "https://www.jbba.kr/bbs/download.php?bo_table=sub01_09&wr_id=1529&no=0"

# 요청 헤더
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.jbba.kr/bbs/board.php?bo_table=sub01_09&wr_id=1529',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# 출력 디렉토리
output_dir = Path("encoding_test")
output_dir.mkdir(exist_ok=True)

# 세션 생성
session = requests.Session()

# 먼저 Referer 페이지 방문
session.get('https://www.jbba.kr/bbs/board.php?bo_table=sub01_09&wr_id=1529', headers=headers)

# 파일 다운로드
response = session.get(url, headers=headers)

if response.status_code == 200:
    # Content-Disposition 헤더 확인
    cd = response.headers.get('Content-Disposition', '')
    print(f"Content-Disposition: {cd}")
    
    # 파일명 추출 시도
    if 'filename=' in cd:
        raw_filename = cd.split('filename=')[1].strip('"\'')
        print(f"Raw filename: {raw_filename}")
        
        # 다양한 인코딩 시도
        encodings = [
            ('latin1', 'cp949'),
            ('latin1', 'euc-kr'),
            ('latin1', 'utf-8'),
            ('euc-kr', 'euc-kr'),
            ('utf-8', 'utf-8')
        ]
        
        for src_enc, dest_enc in encodings:
            try:
                decoded = raw_filename.encode(src_enc).decode(dest_enc, errors='ignore')
                print(f"{src_enc} -> {dest_enc}: {decoded}")
                
                # 파일 저장 (인코딩별로 다른 이름 사용)
                safe_name = ''.join(c for c in decoded if c.isalnum() or c in ' ._-').strip()
                if not safe_name:
                    safe_name = f"unknown_{src_enc}_{dest_enc}"
                
                filename = f"{safe_name}.bin"
                with open(output_dir / filename, 'wb') as f:
                    f.write(response.content)
                print(f"Saved as: {filename}")
            except Exception as e:
                print(f"Error with {src_enc} -> {dest_enc}: {str(e)}")
    else:
        print("No filename in Content-Disposition")
        
        # URL에서 파일명 추출
        filename = url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        print(f"Falling back to URL filename: {filename}")
        
        with open(output_dir / f"{filename}.bin", 'wb') as f:
            f.write(response.content)
else:
    print(f"Error: HTTP status {response.status_code}")