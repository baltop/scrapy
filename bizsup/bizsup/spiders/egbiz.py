import scrapy
import logging
import re
from scrapy_playwright.page import PageMethod


class EgbizSpider(scrapy.Spider):
    name = "egbiz"
    allowed_domains = ["egbiz.or.kr"]
    start_urls = ["https://www.egbiz.or.kr/index.do"]

    def __init__(self, *args, **kwargs):
        super(EgbizSpider, self).__init__(*args, **kwargs)
        self.all_thread_urls = []  # 모든 스레드 URL을 저장할 리스트
        self.max_more_clicks = 6  # "더보기" 버튼 최대 클릭 수

    def start_requests(self):
        """Playwright를 사용하여 시작 요청 처리"""
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,  # Playwright 활성화
                    playwright_include_page=True,  # page 객체를 응답에 포함
                    playwright_page_methods=[
                        PageMethod("wait_for_selector", "body"),  # 페이지가 로드될 때까지 대기
                    ],
                ),
                callback=self.parse
            )

    def parse(self, response):
        """
        메인 페이지에서 스레드 링크 추출 및 "더보기" 버튼 처리
        """
        page = response.meta["playwright_page"]
        self.logger.info(f"페이지 로드 완료: {response.url}")
        
        # 초기 스레드 링크 추출
        self.logger.info("초기 스레드 링크 추출 중...")
        thread_links = self.extract_thread_links(response)
        self.all_thread_urls.extend(thread_links)
        self.logger.info(f"초기 스레드 {len(thread_links)}개 발견")
        
        # "더보기" 버튼 클릭 처리
        async def process_wrapper():
            async for item in self.process_more_button(page, response, 0):
                yield item
                
        return process_wrapper()

    async def process_more_button(self, page, response, click_count):
        """'더보기' 버튼 클릭 처리 및 추가 항목 수집"""
        # 클릭 제한 확인
        if click_count >= self.max_more_clicks:
            self.logger.info(f"최대 클릭 수 {self.max_more_clicks}에 도달")
            # 모든 수집된 URL 반환
            await page.close()
            for url in self.all_thread_urls:
                yield {"thread_url": url}
            return
        
        # "더보기" 버튼 CSS 선택자
        more_button_selectors = [
            ".more-btn",
            ".btn_more",
            ".btn-more",
            ".btnMore",
            "#btnMore",
            "button.more",
            "a.more",
            ".more",
            ".list_more",
            ".list-more",
            ".load_more",
            ".load-more",
            ".viewMore",
            ".view_more",
            ".view-more",
            "button[class*='more']",
            "a[class*='more']",
            "a.goBoard",
            ".view_btn",
            ".view-btn",
            ".btn-view",
            ".btn_view",
            ".btn-list",
            ".btn_list"
        ]
        
        # 각 선택자로 버튼 찾기 시도
        button_found = False
        for selector in more_button_selectors:
            try:
                # 버튼 존재 및 가시성 확인
                is_visible = await page.evaluate("""(selector) => {
                    const btn = document.querySelector(selector);
                    if (!btn) return false;
                    const style = window.getComputedStyle(btn);
                    return btn.offsetWidth > 0 && btn.offsetHeight > 0 && 
                           style.display !== 'none' && style.visibility !== 'hidden';
                }""", selector)
                
                if is_visible:
                    self.logger.info(f"'더보기' 버튼 발견: {selector}")
                    
                    # 현재 스레드 수 확인
                    pre_count = len(self.all_thread_urls)
                    
                    # 버튼 클릭 (직접 JavaScript 사용)
                    await page.evaluate("""(selector) => {
                        const btn = document.querySelector(selector);
                        if (btn) {
                            btn.click();
                            return true;
                        }
                        return false;
                    }""", selector)
                    self.logger.info(f"'더보기' 버튼 클릭 #{click_count+1} (JavaScript 이용)")
                    
                    # 새 콘텐츠 로딩 대기
                    await page.wait_for_timeout(2000)  # 2초 대기
                    
                    # 업데이트된 HTML 추출 및 파싱
                    content = await page.content()
                    updated_response = scrapy.http.HtmlResponse(
                        url=response.url,
                        body=content.encode('utf-8'),
                        encoding='utf-8'
                    )
                    
                    # 모든 스레드 링크 추출 (이미 수집된 URL 제외)
                    current_links = self.extract_thread_links(updated_response)
                    new_links = [link for link in current_links if link not in self.all_thread_urls]
                    self.all_thread_urls.extend(new_links)
                    
                    self.logger.info(f"클릭 #{click_count+1}: {len(new_links)}개의 새 스레드 발견")
                    self.logger.info(f"총 스레드 URL: {len(self.all_thread_urls)}개")
                    
                    button_found = True
                    if len(new_links) > 0:
                        # 새 링크가 추가되었으면 다음 클릭 진행
                        # 비동기 함수에서는 yield from 대신 재귀적으로 yield
                        async for item in self.process_more_button(page, updated_response, click_count + 1):
                            yield item
                    else:
                        self.logger.info("새 스레드가 추가되지 않음. 더보기 처리 종료")
                        break
                    break
            except Exception as e:
                self.logger.error(f"버튼 클릭 중 오류 발생: {str(e)}")
        
        if not button_found:
            self.logger.info("더보기 버튼을 찾을 수 없음")
        
        # 모든 스레드 URL 반환
        await page.close()
        
        # 한 번에 모든 URL 반환
        for url in self.all_thread_urls:
            yield {"thread_url": url}

    def extract_thread_links(self, response):
        """페이지에서 스레드 링크 추출"""
        # 가능한 CSS 선택자들
        selectors = [
            '.notice-list li a::attr(href)',
            '.board-list li a::attr(href)',
            '.board_list li a::attr(href)',
            '.board-list td.subject a::attr(href)',
            '.board_list td.subject a::attr(href)',
            '.notice-board a::attr(href)',
            'table.board-list tr td.subject a::attr(href)',
            'table.board_list tr td.subject a::attr(href)',
            '.notice-block a::attr(href)',
            '.notice-item a::attr(href)',
            '.biz_list a::attr(href)',
            '.biz-list a::attr(href)',
            '.list a::attr(href)',
            '.list_body a::attr(href)',
            '.news_list a::attr(href)',
            '.news-list a::attr(href)',
            '.board_news a::attr(href)',
            '.board-news a::attr(href)',
            '.news_board a::attr(href)',
            'a[href*="board_seq"]::attr(href)',
            'a[href*="seq="]::attr(href)',
            'a[href*="idx="]::attr(href)',
            'a[href*="board/view"]::attr(href)',
            'a[href*="boardId"]::attr(href)',
            'a[href*="view.do"]::attr(href)'
        ]
        
        # onclick 이벤트가 있는 링크도 처리
        onclick_selectors = [
            'a[onclick*="fnView"]::attr(onclick)',
            'tr[onclick*="fnView"]::attr(onclick)',
            'a[onclick*="goView"]::attr(onclick)',
            'a[onclick*="View"]::attr(onclick)'
        ]
        
        # 모든 일반 링크 추출
        all_links = []
        for selector in selectors:
            links = response.css(selector).getall()
            if links:
                self.logger.info(f"{len(links)}개 링크 발견 (선택자: {selector})")
                all_links.extend(links)
        
        # onclick 이벤트에서 링크 추출
        for selector in onclick_selectors:
            onclick_events = response.css(selector).getall()
            if onclick_events:
                self.logger.info(f"{len(onclick_events)}개 onclick 이벤트 발견 (선택자: {selector})")
                for onclick in onclick_events:
                    # 게시물 ID 추출 (여러 패턴 지원)
                    # "fnView('123')", "goView(123)", "View('123', '456')" 등
                    id_match = re.search(r"(?:fnView|goView|View)\s*\(\s*'?(\d+)'?", onclick)
                    if id_match:
                        board_id = id_match.group(1)
                        # 일반적인 게시판 URL 패턴으로 조합
                        constructed_url = f"https://www.egbiz.or.kr/board/view.do?boardId={board_id}"
                        all_links.append(constructed_url)
        
        # 모든 링크를 절대 URL로 변환하고 중복 제거
        clean_links = []
        for link in all_links:
            if link and 'javascript:' not in link:
                absolute_url = response.urljoin(link)
                clean_links.append(absolute_url)
        
        # 중복 제거하여 반환
        return list(set(clean_links))
