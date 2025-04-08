import scrapy
import logging
import os
import requests
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote
import html2text
from bs4 import BeautifulSoup


class DipSpider(scrapy.Spider):
    name = "dip"
    allowed_domains = ["dip.or.kr"]
    start_urls = ["https://www.dip.or.kr/home/notice/businessbbs/boardList.ubs?sfpsize=10&fboardcd=business&sfkind=&sfcategory=&sfstdt=&sfendt=&sfsearch=ftitle&sfkeyword=&sfpage=1"]
    
    # 실제 게시글 URL 필터링을 위한 패턴 (다운로드 URL은 크롤링하지 않음)
    download_url_patterns = [
        'download.php',
        'file_download',
        'player.php',
        'fileDown'
    ]
    
    def __init__(self, *args, **kwargs):
        super(DipSpider, self).__init__(*args, **kwargs)
        self.all_thread_urls = []  # 모든 스레드 URL을 저장할 리스트
        self.max_pages = 6  # 크롤링할 최대 페이지 수
        # 저장 디렉토리 설정
        self.output_dir = Path("dip_output")
        self.output_dir.mkdir(exist_ok=True)
        self.attachments_dir = self.output_dir / "attachments"
        self.attachments_dir.mkdir(exist_ok=True)
    
    def parse(self, response):
        """
        BBS 스타일 페이지에서 스레드 링크를 추출하고 페이지네이션을 처리
        """
        self.logger.info(f"Processing page: {response.url}")
        
        # 게시글 목록에서 게시글 번호 추출
        # tr 태그의 onclick 속성에서 javascript:read('dipadmin','게시글번호') 형식에서 게시글 번호를 추출
        rows = response.css('div.board__item tr')
        thread_urls = []
        
        for row in rows:
            # onclick 속성에서 게시글 번호 추출
            onclick = row.xpath('@onclick').get()
            if onclick and "read(" in onclick:
                # 게시글 번호 추출
                try:
                    # javascript:read('dipadmin','8482') 형식에서 8482 추출
                    board_num = onclick.split("'")[-2]
                    # 게시글 URL 생성
                    thread_url = f"https://www.dip.or.kr/home/notice/businessbbs/boardRead.ubs?fboardnum={board_num}&fboardcd=business&sfpage=1"
                    thread_urls.append(thread_url)
                except Exception as e:
                    self.logger.error(f"Error extracting board number: {str(e)}")
        
        self.logger.info(f"Found {len(thread_urls)} thread links")
        
        # 수집된 URL을 리스트에 추가
        self.all_thread_urls.extend(thread_urls)
        
        # 로깅
        self.logger.info(f"Total thread URLs so far: {len(self.all_thread_urls)}")
        
        # 현재 페이지 번호 확인
        current_page = self.get_current_page(response.url)
        self.logger.info(f"Current page: {current_page}")
        
        # 최대 페이지 수에 도달하지 않았다면 다음 페이지로 이동
        if current_page < self.max_pages:
            next_page_url = self.get_next_page_url(response, current_page)
            if next_page_url:
                self.logger.info(f"Following next page: {next_page_url}")
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse
                )
            else:
                self.logger.warning(f"Could not find next page URL for page {current_page}")
                # 다음 페이지를 찾지 못했으므로 수집된 스레드 처리
                for idx, thread_url in enumerate(self.all_thread_urls):
                    yield scrapy.Request(
                        url=thread_url,
                        callback=self.parse_thread,
                        meta={'thread_url': thread_url, 'index': idx + 1}
                    )
        else:
            # 모든 페이지를 처리했으므로 수집된 스레드 처리
            self.logger.info(f"Completed all {self.max_pages} pages")
            self.logger.info(f"Total thread URLs collected: {len(self.all_thread_urls)}")
            
            # 수집된 모든 스레드 URL로 요청 생성
            for idx, thread_url in enumerate(self.all_thread_urls):
                yield scrapy.Request(
                    url=thread_url,
                    callback=self.parse_thread,
                    meta={'thread_url': thread_url, 'index': idx + 1}
                )
    
    def get_current_page(self, url):
        """
        URL에서 현재 페이지 번호 추출
        """
        # 기본값은 1페이지
        current_page = 1
        
        # URL에서 페이지 번호 추출 시도
        if 'sfpage=' in url:
            try:
                current_page = int(url.split('sfpage=')[1].split('&')[0])
            except (ValueError, IndexError):
                pass
        
        return current_page
    
    def get_next_page_url(self, response, current_page):
        """
        다음 페이지 URL 생성
        """
        # 다음 페이지 번호
        next_page = current_page + 1
        
        # 기존 URL에서 sfpage 파라미터만 변경
        next_page_url = response.url.replace(f"sfpage={current_page}", f"sfpage={next_page}")
        
        return next_page_url
    
    def parse_thread(self, response):
        """
        스레드 페이지에서 본문 내용과 첨부 파일 추출
        """
        thread_url = response.meta.get('thread_url')
        index = response.meta.get('index', 0)
        self.logger.info(f"Processing thread: {thread_url}")
        
        # 게시글 제목 추출
        title = response.css('div.read__title h3::text').get()
        if not title:
            title = f"게시글-{index}"
            self.logger.warning(f"Could not extract title, using fallback: {title}")
        else:
            title = title.strip()
        
        # 게시글 본문 내용 추출
        content = response.css('div.read__content').get()
        
        if content:
            # HTML 문서 파싱을 위해 BeautifulSoup 사용
            soup = BeautifulSoup(content, 'html.parser')
            
            # HTML을 Markdown으로 변환
            h2t = html2text.HTML2Text()
            h2t.ignore_links = False  # 링크 유지
            h2t.ignore_images = False  # 이미지 유지
            h2t.ignore_tables = False  # 테이블 유지
            h2t.body_width = 0  # 줄바꿈 방지
            h2t.unicode_snob = True  # 유니코드 문자 유지
            h2t.mark_code = True  # 코드 블록 마킹
            
            # HTML 내용을 마크다운으로 변환
            markdown_content = h2t.handle(str(soup))
            
            # 게시판 번호 디렉토리 생성 (첨부파일 저장용)
            index_dir = self.output_dir / f"{index}"
            index_dir.mkdir(exist_ok=True)
            
            # 마크다운 파일 저장
            md_filename = self.output_dir / f"{index}.md"
            with open(md_filename, 'w', encoding='utf-8') as f:
                # 메타데이터 추가
                f.write(f"# {title}\n\n")
                f.write(f"원본 URL: {thread_url}\n\n")
                
                # 게시글 정보 추가
                # 등록일 추출
                date = response.css('div.board-read-table__column3--item:nth-child(2) div.board-read-table__content span::text').get()
                if date:
                    f.write(f"작성일: {date.strip()}\n\n")
                
                # 본문 내용
                f.write("## 내용\n\n")
                f.write(markdown_content)  # 변환된 마크다운 내용 저장
            
            self.logger.info(f"Saved content as Markdown to {md_filename}")
        else:
            self.logger.error(f"Failed to extract content from {thread_url}")
        
        # 첨부 파일 다운로드
        attachment_links = []
        attachment_texts = []
        processed_urls = set()
        
        # 첨부파일 추출
        file_area = response.css('div.board-read-table__column:nth-child(5) div.board-read-table__content dl.horizontal a')
        for file_link in file_area:
            href = file_link.xpath('@href').get()
            text = file_link.xpath('text()').get()
            
            if href and href not in processed_urls:
                # 상대 URL을 절대 URL로 변환
                absolute_url = response.urljoin(href)
                attachment_links.append(absolute_url)
                attachment_texts.append(text.strip() if text else "")
                processed_urls.add(href)
                self.logger.info(f"Found attachment: {absolute_url} - {text}")
        
        self.logger.info(f"Found {len(attachment_links)} attachments")
        
        # 첨부파일 다운로드
        for i, att_url in enumerate(attachment_links):
            try:
                # 파일 이름 결정
                attachment_text = ""
                if i < len(attachment_texts):
                    attachment_text = attachment_texts[i]
                
                if attachment_text:
                    # 링크 텍스트에서 추출한 이름 사용
                    base_filename = attachment_text
                    # 파일명에 사용할 수 없는 문자 제거
                    base_filename = ''.join(c for c in base_filename if c.isalnum() or c in ' ._-').strip()
                else:
                    # URL에서 파일명 추출 시도
                    parsed_url = urlparse(att_url)
                    path = parsed_url.path
                    base_filename = os.path.basename(path)
                    if not base_filename:
                        base_filename = f"file_{index}_{i}"
                
                # 파일명 길이 제한
                base_filename = base_filename[:100]
                
                # 첨부파일 다운로드
                self.logger.info(f"Downloading attachment: {att_url}")
                
                # 파일 다운로드 (브라우저와 같은 헤더 설정)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': response.url,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                # 쿠키 전달 (응답의 쿠키 재사용)
                cookies = {}
                for cookie in response.headers.getlist('Set-Cookie'):
                    if b'=' in cookie:
                        key, value = cookie.split(b'=', 1)
                        if b';' in value:
                            value = value.split(b';', 1)[0]
                        cookies[key.decode('utf-8')] = value.decode('utf-8')
                
                r = requests.get(att_url, headers=headers, cookies=cookies, stream=True, allow_redirects=True)
                
                if r.status_code == 200:
                    # 파일명 확인 - Content-Disposition 헤더에서 파일명 추출 시도
                    filename = base_filename
                    if 'Content-Disposition' in r.headers:
                        cd = r.headers['Content-Disposition']
                        if 'filename=' in cd:
                            try:
                                server_filename = cd.split('filename=')[1].strip('"\'')
                                if server_filename:
                                    # 서버가 제공한 파일명 사용
                                    filename = unquote(server_filename)
                            except Exception as e:
                                self.logger.error(f"Error parsing filename: {str(e)}")
                    
                    # 파일 확장자 확인
                    if "." not in filename[-5:]:
                        # Content-Type 헤더로 확장자 추측
                        if 'Content-Type' in r.headers:
                            content_type = r.headers['Content-Type'].lower()
                            if 'application/pdf' in content_type:
                                filename += '.pdf'
                            elif 'application/msword' in content_type or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                                filename += '.doc'
                            elif 'application/vnd.ms-excel' in content_type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
                                filename += '.xls'
                            elif 'image/' in content_type:
                                ext = content_type.replace('image/', '')
                                filename += f'.{ext}'
                    
                    # 파일명에 사용할 수 없는 문자 제거
                    filename = ''.join(c for c in filename if c.isalnum() or c in ' ._-').strip()
                    
                    # 파일 저장 (인덱스 디렉토리에 저장)
                    att_path = index_dir / filename
                    
                    # HTML 오류 페이지 확인
                    is_html = False
                    content_peek = r.content[:1024] if len(r.content) > 0 else b''
                    
                    if b'<!doctype html>' in content_peek.lower() or b'<html' in content_peek.lower():
                        is_html = True
                        self.logger.warning(f"Received HTML instead of file. Site may require authentication for downloads.")
                        # 오류 페이지로 판단되면 저장하지 않음
                        continue
                    
                    # 파일 저장
                    with open(att_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    self.logger.info(f"Successfully downloaded attachment to {att_path}")
                else:
                    self.logger.error(f"Failed to download attachment: HTTP {r.status_code}")
            
            except Exception as e:
                self.logger.error(f"Error downloading attachment: {str(e)}")
        
        yield {
            'url': thread_url,
            'title': title,
            'content_saved': bool(content),
            'attachments_count': len(attachment_links)
        }