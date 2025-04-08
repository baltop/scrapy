#!/usr/bin/env python
# 첨부파일 다운로드 테스트
import requests
import os
from pathlib import Path
import sys

def download_attachment(url, output_dir, filename_prefix):
    """첨부 파일 다운로드 테스트"""
    print(f"다운로드 URL: {url}")
    
    # 디렉토리 생성
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 요청 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.jbba.kr/bbs/board.php?bo_table=sub01_09',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # 세션 사용 (쿠키 유지)
        session = requests.Session()
        
        # 먼저 원본 페이지 방문 (세션 쿠키 얻기)
        referer_url = 'https://www.jbba.kr/bbs/board.php?bo_table=sub01_09&wr_id=1529'
        print(f"Referer URL 방문: {referer_url}")
        session.get(referer_url, headers=headers)
        
        # 파일 다운로드
        print(f"파일 다운로드 시도...")
        response = session.get(url, headers=headers, stream=True, allow_redirects=True)
        
        if response.status_code == 200:
            # 콘텐츠 타입 확인
            content_type = response.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            
            # Content-Disposition 확인
            content_disposition = response.headers.get('Content-Disposition', '')
            print(f"Content-Disposition: {content_disposition}")
            
            # URL에서 파일명 추출
            filename = url.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
            
            # Content-Disposition에서 파일명 추출 시도
            if 'filename=' in content_disposition:
                try:
                    cd_filename = content_disposition.split('filename=')[1].strip('"\'')
                    if cd_filename:
                        filename = cd_filename
                except:
                    pass
            
            # 파일명이 없으면 기본 이름 사용
            if not filename or len(filename) < 3:
                filename = f"{filename_prefix}_file.bin"
            
            # 파일 확장자 확인
            if '.' not in filename[-5:]:
                if 'application/pdf' in content_type:
                    filename += '.pdf'
                elif 'application/msword' in content_type or 'application/vnd.openxmlformats' in content_type:
                    filename += '.docx'
                else:
                    filename += '.bin'
            
            # 파일 저장 경로
            output_path = output_dir / filename
            
            # HTML 페이지 확인
            content_peek = response.content[:1024].lower()
            if b'<!doctype html>' in content_peek or b'<html' in content_peek:
                print("오류: HTML 페이지가 반환되었습니다. 첨부파일이 아닙니다.")
                
                # 디버깅용으로 HTML 저장
                with open(output_dir / "error_page.html", "wb") as f:
                    f.write(response.content)
                print(f"오류 페이지 저장됨: {output_dir / 'error_page.html'}")
                return False
            
            # 파일 저장
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"파일 저장 완료: {output_path}")
            return True
        else:
            print(f"오류: 상태 코드 {response.status_code}")
            return False
    
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    # 출력 디렉토리
    output_dir = "jbba_output/attachments"
    
    # 테스트할 URL (커맨드 라인에서 제공되거나 기본값 사용)
    urls = []
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        # 기본 테스트 URL
        urls = [
            "https://www.jbba.kr/bbs/download.php?bo_table=sub01_09&wr_id=1529&no=0",
            "https://www.jbba.kr/bbs/download.php?bo_table=sub01_09&wr_id=1528&no=0"
        ]
    
    # 각 URL 테스트
    for i, url in enumerate(urls):
        prefix = f"test_{i+1}"
        download_attachment(url, output_dir, prefix)