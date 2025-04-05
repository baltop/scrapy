import scrapy
import logging


class SnipbottomSpider(scrapy.Spider):
    name = "snipBottom"
    allowed_domains = ["snip.or.kr"]
    start_urls = ["https://www.snip.or.kr/SNIP/contents/Business1.do"]
    
    def __init__(self, *args, **kwargs):
        super(SnipbottomSpider, self).__init__(*args, **kwargs)
        self.all_thread_urls = []  # 모든 스레드 URL을 저장할 리스트
        self.max_pages = 6  # 크롤링할 최대 페이지 수
    
    def parse(self, response):
        """
        BBS 스타일 페이지에서 스레드 링크를 추출하고 페이지네이션을 처리
        """
        self.logger.info(f"Processing page: {response.url}")
        
        # 스레드 링크 추출 - snip.or.kr의 실제 HTML 구조 사용
        # 분석 결과 HTML에서 td.subject 안의 a 태그에 스레드 링크가 있음
        thread_links = response.css('td.subject a::attr(href)').getall()
        
        if not thread_links:
            self.logger.warning("No thread links found with primary selector, trying alternatives")
            # 대체 선택자 시도
            alternative_selectors = [
                'table.board-list a::attr(href)',
                'a[href*="portlet="]::attr(href)',
                'a[target="_blank"]::attr(href)'
            ]
            
            for selector in alternative_selectors:
                thread_links = response.css(selector).getall()
                if thread_links:
                    self.logger.info(f"Found {len(thread_links)} links with selector: {selector}")
                    break
        
        self.logger.info(f"Found {len(thread_links)} thread links")
        
        # 필터링: JavaScript 코드 없는 실제 URL만 유지
        filtered_thread_urls = []
        for url in thread_links:
            if url and 'javascript:' not in url:
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
                # 모든 페이지를 처리했으므로 수집된 URL 출력
                for url in self.all_thread_urls:
                    yield {'thread_url': url}
        else:
            # 모든 페이지를 처리했으므로 수집된 URL 출력
            self.logger.info(f"Completed all {self.max_pages} pages")
            self.logger.info(f"Total thread URLs collected: {len(self.all_thread_urls)}")
            
            # 수집된 모든 스레드 URL 반환
            for url in self.all_thread_urls:
                yield {'thread_url': url}
    
    def get_current_page(self, url):
        """
        URL에서 현재 페이지 번호 추출
        """
        # 기본값은 1페이지
        current_page = 1
        
        # URL에서 페이지 번호 추출 시도
        if 'page=' in url:
            try:
                current_page = int(url.split('page=')[1].split('&')[0])
            except (ValueError, IndexError):
                pass
        
        return current_page
    
    def get_next_page_url(self, response, current_page):
        """
        다음 페이지 URL 생성 - snip.or.kr 사이트 분석 기반
        """
        # 자바스크립트 코드 분석 결과 페이지 이동은 단순히 page 파라미터만 변경
        next_page = current_page + 1
        
        # 기본 URL (쿼리 스트링 제외)
        base_url = response.url.split('?')[0]
        
        # 현재 URL의 모든 매개변수 유지하되 page만 변경
        params = {}
        if '?' in response.url:
            query_string = response.url.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        # page 파라미터 업데이트
        params['page'] = str(next_page)
        
        # viewCount 파라미터가 없으면 추가 (웹사이트 분석 결과)
        if 'viewCount' not in params:
            params['viewCount'] = '10'
        
        # 쿼리 문자열 구성
        query_parts = [f"{k}={v}" for k, v in params.items()]
        next_page_url = f"{base_url}?{'&'.join(query_parts)}"
        
        return next_page_url
