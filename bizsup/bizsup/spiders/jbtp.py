import scrapy
import logging
import os
import requests
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote
import html2text
from bs4 import BeautifulSoup


class JbtpSpider(scrapy.Spider):
    name = "jbtp"
    allowed_domains = ["jbtp.or.kr"]
    start_urls = ["https://www.jbtp.or.kr/board/list.jbtp?boardId=BBS_0000006&menuCd=DOM_000000102001000000&paging=ok&gubun=&searchType=&keyword=&pageNo=1"]
    
    # 실제 게시글 URL 필터링을 위한 패턴 (다운로드 URL은 크롤링하지 않음)
    download_url_patterns = [
        'download.php',
        'file_download',
        'player.php'
    ]
    
    def __init__(self, *args, **kwargs):
        super(JbtpSpider, self).__init__(*args, **kwargs)
        self.all_thread_urls = []  # 모든 스레드 URL을 저장할 리스트
        self.max_pages = 6  # 크롤링할 최대 페이지 수
        # 저장 디렉토리 설정
        self.output_dir = Path("jbtp_output")
        self.output_dir.mkdir(exist_ok=True)
        self.attachments_dir = self.output_dir / "attachments"
        self.attachments_dir.mkdir(exist_ok=True)
    
    def parse(self, response):
        """
        BBS 스타일 페이지에서 스레드 링크를 추출하고 페이지네이션을 처리
        """
        self.logger.info(f"Processing page: {response.url}")
        
        # 스레드 링크 추출
        thread_links = response.css('td a[href*="view.jbtp"]::attr(href)').getall()
        
        if not thread_links:
            self.logger.warning("No thread links found with primary selector, trying alternatives")
            # 대체 선택자 시도
            alternative_selectors = [
                'a[href*="view.jbtp"]::attr(href)',
                'td a::attr(href)',
                'a[href*="dataSid="]::attr(href)'
            ]
            
            for selector in alternative_selectors:
                thread_links = response.css(selector).getall()
                if thread_links:
                    self.logger.info(f"Found {len(thread_links)} links with selector: {selector}")
                    break
        
        self.logger.info(f"Found {len(thread_links)} thread links")
        
        # 필터링: JavaScript 코드 없는 실제 URL만 유지하고 다운로드 URL 제외
        filtered_thread_urls = []
        for url in thread_links:
            if url and 'javascript:' not in url and '#' not in url:
                # URL이 다운로드 URL인지 확인
                is_download_url = False
                for pattern in self.download_url_patterns:
                    if pattern in url:
                        is_download_url = True
                        break
                
                # 다운로드 URL이 아닌 경우만 추가
                if not is_download_url:
                    # URL이 절대 URL인지 확인하고 아니면 변환
                    absolute_url = response.urljoin(url)
                    filtered_thread_urls.append(absolute_url)
        
        # 수집된 URL을 리스트에 추가
        self.all_thread_urls.extend(filtered_thread_urls)
        
        # 찾은 URL 로깅
        self.logger.info(f"Added {len(filtered_thread_urls)} filtered thread URLs")
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
                for thread_url in self.all_thread_urls:
                    yield scrapy.Request(
                        url=thread_url,
                        callback=self.parse_thread,
                        meta={'thread_url': thread_url}
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
                    meta={'thread_url': thread_url, 'index': idx + 1}  # 인덱스 추가
                )
    
    def get_current_page(self, url):
        """
        URL에서 현재 페이지 번호 추출
        """
        # 기본값은 1페이지
        current_page = 1
        
        # URL에서 페이지 번호 추출 시도
        if 'pageNo=' in url:
            try:
                current_page = int(url.split('pageNo=')[1].split('&')[0])
            except (ValueError, IndexError):
                pass
        
        return current_page
    
    def get_next_page_url(self, response, current_page):
        """
        다음 페이지 URL 생성
        """
        # 다음 페이지 번호
        next_page = current_page + 1
        
        # 기본 URL (쿼리 스트링 제외)
        base_url = response.url.split('?')[0]
        
        # 현재 URL의 모든 매개변수 유지하되 pageNo만 변경
        params = {}
        if '?' in response.url:
            query_string = response.url.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        # pageNo 파라미터 업데이트
        params['pageNo'] = str(next_page)
        
        # 쿼리 문자열 구성
        query_parts = [f"{k}={v}" for k, v in params.items()]
        next_page_url = f"{base_url}?{'&'.join(query_parts)}"
        
        return next_page_url
    
    def parse_thread(self, response):
        """
        스레드 페이지에서 본문 내용과 첨부 파일 추출
        """
        thread_url = response.meta.get('thread_url')
        index = response.meta.get('index', 0)  # 인덱스 가져오기, 기본값 0
        self.logger.info(f"Processing thread: {thread_url}")
        
        # 게시글 제목 추출
        title = None
        
        # 제목 추출 시도 1: 주요 제목 선택자들
        title_selectors = [
            '.board_view .t_tit::text',
            '.subject h3::text',
            '.view-title::text',
            '.view_tit::text',
            'h4.content_head::text'
        ]
        
        for selector in title_selectors:
            title = response.css(selector).get()
            if title and title.strip():
                title = title.strip()
                self.logger.info(f"Found title using selector: {selector}")
                break
        
        # 제목 추출 시도 2: 테이블 기반 레이아웃
        if not title:
            # 테이블 내 '제목' 레이블 옆의 텍스트 찾기
            title_row = response.xpath('//th[contains(text(), "제목")]/following-sibling::td')
            if title_row:
                title = title_row.xpath('string()').get()
                if title:
                    title = title.strip()
        
        # 제목이 없으면 URL에서 ID 추출하여 대체
        if not title:
            try:
                if 'dataSid=' in thread_url:
                    seq_id = thread_url.split('dataSid=')[1].split('&')[0]
                else:
                    seq_id = thread_url.split('boardId=')[1].split('&')[0]
                title = f"게시글-{seq_id}"
            except (IndexError, ValueError):
                title = f"게시글-{hash(thread_url) % 10000}"
            
            self.logger.warning(f"Could not extract title, using fallback: {title}")
        
        # 파일명에 사용할 수 없는 문자 제거
        safe_title = ''.join(c for c in title if c.isalnum() or c in ' ._-').strip()
        safe_title = safe_title[:50]  # 파일명 길이 제한
        
        # 게시글 본문 내용 추출
        content = None
        
        # 본문 내용 추출 시도 - 다양한 선택자
        content_selectors = [
            '.board_view .cont',
            '.view_cont',
            '.content_body',
            '.board_txt',
            '.view_text',
            '.bbs_con',
            '.bbs_con iframe',
            '.bbs_view .bbs_con'
        ]
        
        for selector in content_selectors:
            content = response.css(selector).get()
            if content:
                self.logger.info(f"Found content using selector: {selector}")
                break
        
        # 본문을 찾지 못한 경우 대체 방법 시도
        if not content:
            # 테이블 기반 레이아웃에서 본문 찾기
            content_row = response.xpath('//th[contains(text(), "내용")]/following-sibling::td')
            if content_row:
                content = content_row.get()
        
        # 여전히 본문을 찾지 못한 경우 div.content 같은 일반적인 선택자 시도
        if not content:
            content = response.css('div.content, div.article, div.view_cont, div.bbs_con').get()
        
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
            
            # 인덱스 번호를 사용해 파일 저장
            # 디렉토리 생성 (첨부파일 저장용)
            index_dir = self.output_dir / f"{index}"
            index_dir.mkdir(exist_ok=True)
            
            # 파일 저장
            md_filename = self.output_dir / f"{index}.md"
            with open(md_filename, 'w', encoding='utf-8') as f:
                # 메타데이터 추가
                f.write(f"# {title}\n\n")
                f.write(f"원본 URL: {thread_url}\n\n")
                
                # 게시글 정보 추가
                author = response.css('.t_info li:first-child::text, .writer::text').get()
                if author:
                    f.write(f"작성자: {author.strip()}\n\n")
                
                date = response.css('.t_info li:last-child::text, .date::text').get()
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
        processed_urls = set()  # 중복 URL 방지
        
        # 파일 첨부 링크 찾기 (첫 번째 방법)
        file_links = response.css('.board_file a[href*="fileDown"], .file_area a[href*="download"], .bbs_filedown a.sbtn_down')
        for link in file_links:
            href = link.css('::attr(href)').get()
            if href and href not in processed_urls:
                # 다운로드 URL인지 확인
                if 'fileDown' in href or 'download' in href or 'attach' in href:
                    # JBTP는 다운로드 버튼 텍스트가 아닌 앞에 있는 파일명을 사용해야 함
                    if '.bbs_filedown' in link.root.getroottree().getpath(link.root):
                        # 파일명은 a 태그의 부모 dd 태그의 첫 번째 텍스트 노드에 있음
                        parent_dd = link.xpath('./ancestor::dd')
                        if parent_dd:
                            text = parent_dd.xpath('./text()').get() or ""
                            text = text.strip()
                            # 파일명이 비어있거나 짧은 경우(예: "다운로드"), 다른 방법 시도
                            if not text or len(text) < 5:
                                # 다른 시도: dd 내부의 모든 텍스트 노드 가져오기
                                all_text = parent_dd.xpath('string()').get() or ""
                                all_text = all_text.strip()
                                if all_text and "다운로드" not in all_text and len(all_text) > 5:
                                    text = all_text
                        else:
                            text = link.css('::text').get() or ""
                    else:
                        text = link.css('::text').get() or ""
                    
                    attachment_links.append(href)
                    attachment_texts.append(text.strip())
                    processed_urls.add(href)
                    self.logger.info(f"Found attachment link: {href} - {text.strip()}")
        
        # 별도의 첨부 파일 영역에서 추가 검색 (두 번째 방법)
        file_area = response.css('.file_list, .file_area, .add_file, .board_file, .bbs_filedown')
        if file_area:
            for row in file_area.css('li, div, a, dd'):
                link = row.css('a.sbtn_down::attr(href)').get()
                if link and link not in processed_urls:
                    # 다운로드 URL인지 확인
                    if 'fileDown' in link or 'download' in link or 'attach' in link:
                        # JBTP는 dd 태그 안에 파일명과 다운로드 링크가 함께 있음
                        if row.root.tag == 'dd':
                            text = row.xpath('./text()').get() or ""
                            text = text.strip()
                        else:
                            text = row.css('a::text').get() or ""
                        
                        # 이미 처리한 URL인지 확인
                        attachment_links.append(link)
                        attachment_texts.append(text.strip())
                        processed_urls.add(link)
                        self.logger.info(f"Found attachment in file area: {link} - {text.strip()}")
        
        # 첨부파일 다운로드 URL 필터링
        clean_attachment_links = []
        clean_attachment_texts = []
        for i, url in enumerate(attachment_links):
            # 실제 다운로드 링크만 유지
            if url.startswith('javascript:') or '#' in url:
                continue
                
            # 명확한 플레이어 URL 필터링
            if 'player' in url or 'preview' in url:
                continue
                
            # 링크 유지
            clean_attachment_links.append(url)
            clean_attachment_texts.append(attachment_texts[i])
        
        # 최종 첨부파일 목록으로 업데이트
        attachment_links = clean_attachment_links
        attachment_texts = clean_attachment_texts
        
        self.logger.info(f"Found {len(attachment_links)} unique attachments")
        
        # 첨부파일 다운로드 - 인덱스 디렉토리에 저장
        for i, att_url in enumerate(attachment_links):
            try:
                # 상대 URL을 절대 URL로 변환
                absolute_att_url = response.urljoin(att_url)
                
                # 파일 이름 결정
                attachment_text = ""
                if i < len(attachment_texts):
                    attachment_text = attachment_texts[i]
                
                # URL 매개변수에서 정보 추출
                file_id = "unknown"
                file_seq = "0"
                
                if "fileId=" in absolute_att_url:
                    try:
                        file_id = absolute_att_url.split("fileId=")[1].split("&")[0]
                    except:
                        pass
                        
                if "fileSeq=" in absolute_att_url:
                    try:
                        file_seq = absolute_att_url.split("fileSeq=")[1].split("&")[0]
                    except:
                        pass
                
                # 최종 파일명 결정 (링크 텍스트와 URL 정보 결합)
                if attachment_text:
                    # 링크 텍스트에서 추출한 이름 사용
                    base_filename = f"{attachment_text}"
                    # 파일명에 사용할 수 없는 문자 제거
                    base_filename = ''.join(c for c in base_filename if c.isalnum() or c in ' ._-').strip()
                else:
                    # URL 매개변수에서 정보 추출해 고유한 파일명 생성
                    base_filename = f"file_{file_id}_{file_seq}"
                
                # 파일명 길이 제한
                base_filename = base_filename[:100]
                
                # 첨부파일 다운로드
                self.logger.info(f"Downloading attachment: {absolute_att_url}")
                
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
                
                r = requests.get(absolute_att_url, headers=headers, cookies=cookies, stream=True, allow_redirects=True)
                
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
                                    # filename = unquote(server_filename)
                                    filename = server_filename.encode('latin1').decode('utf-8', errors='ignore')
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