import scrapy
import logging


class GntpSpider(scrapy.Spider):
    name = "gntp"
    allowed_domains = ["btp.or.kr"]
    start_urls = ["https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013"]
    
    def __init__(self, *args, **kwargs):
        super(GntpSpider, self).__init__(*args, **kwargs)
        self.all_thread_urls = []  # Initialize list to store all thread URLs
        self.max_pages = 6  # Number of pages to process
    
    def parse(self, response):
        """
        Parse BBS-style page, extract thread links and follow pagination
        """
        # Extract thread links - try multiple possible CSS selectors for BBS-style sites
        # Based on sample.html structure
        self.logger.info(f"Processing page: {response.url}")
        
        # Try to find thread links - multiple selectors based on common BBS patterns
        thread_links = []
        
        # Try specific CSS patterns for this BBS style
        selectors = [
            'table.board_list tr td.subject a::attr(href)',  # Common board list pattern
            'table tr.board_list td.title a::attr(href)',     # Another common pattern
            'a[href*="CMS/Board/Board.do"][href*="seq="]::attr(href)',  # Links with seq parameter
            'td.subject a::attr(href)',                      # Simple subject links
            'div.board_list a::attr(href)',                  # Board list container
            'ul.board_list li a::attr(href)',                # List style board
            '.bbsContent a[href*="seq"]::attr(href)',        # Content links with seq
            'a.view_subject::attr(href)',                    # View subject links
            'a[onclick*="boardView"]::attr(href)'            # Links with boardView JS function
        ]
        
        # Try each selector until we find matches
        for selector in selectors:
            links = response.css(selector).getall()
            if links:
                thread_links.extend(links)
                self.logger.info(f"Found {len(links)} links with selector: {selector}")
                break
        
        # Clean and convert to absolute URLs
        thread_urls = [response.urljoin(link) for link in thread_links if link]
        
        # Filter out non-thread URLs (like pagination links)
        filtered_thread_urls = []
        for url in thread_urls:
            # Skip pagination links, but keep thread links
            if ('pageIndex=' in url and 'seq=' not in url) or 'javascript:' in url:
                continue
            filtered_thread_urls.append(url)
        
        # Add to our collection
        self.all_thread_urls.extend(filtered_thread_urls)
        
        # Log the found URLs
        self.logger.info(f"Found {len(filtered_thread_urls)} thread URLs on page")
        self.logger.info(f"Total thread URLs so far: {len(self.all_thread_urls)}")
        
        # Determine current page number
        current_page = self.get_current_page(response.url)
        
        # Proceed to next page if we haven't reached the limit
        if current_page < self.max_pages:
            next_page_url = self.get_next_page_url(response, current_page)
            if next_page_url:
                self.logger.info(f"Following next page: {next_page_url}")
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse,
                    meta={'dont_redirect': True, 'handle_httpstatus_list': [302]}
                )
        else:
            # We've processed all pages, now output the collected URLs
            self.logger.info(f"Completed all {self.max_pages} pages")
            self.logger.info(f"Total thread URLs collected: {len(self.all_thread_urls)}")
            
            # Yield all collected thread URLs
            for url in self.all_thread_urls:
                yield {'thread_url': url}
    
    def get_current_page(self, url):
        """
        Extract current page number from URL
        """
        # Default to page 1
        current_page = 1
        
        # Try to extract page number from URL
        page_params = ['pageIndex=', 'page=', 'p=']
        for param in page_params:
            if param in url:
                try:
                    current_page = int(url.split(param)[1].split('&')[0])
                    break
                except (ValueError, IndexError):
                    pass
        
        return current_page
    
    def get_next_page_url(self, response, current_page):
        """
        Generate URL for the next page
        """
        next_page = current_page + 1
        
        # First try to find next page link in pagination elements
        next_page_url = None
        
        # Try to find pagination links
        pagination_selectors = [
            f'a[href*="pageIndex={next_page}"]::attr(href)',
            f'a[href*="page={next_page}"]::attr(href)',
            f'a[href*="p={next_page}"]::attr(href)',
            '.pagination a::attr(href)',
            '.paging a::attr(href)'
        ]
        
        for selector in pagination_selectors:
            next_links = response.css(selector).getall()
            if next_links:
                # Use the first matching link
                next_page_url = response.urljoin(next_links[0])
                break
        
        # If we couldn't find the next page link, construct it manually
        if not next_page_url:
            # Get base URL without parameters
            base_url = response.url.split('?')[0] if '?' in response.url else response.url
            
            # Extract parameters from current URL
            params = {}
            if '?' in response.url:
                query_string = response.url.split('?')[1]
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
            
            # Set page parameter
            # Try common pagination parameter names
            page_param_found = False
            for param_name in ['pageIndex', 'page', 'p']:
                if param_name in params:
                    params[param_name] = str(next_page)
                    page_param_found = True
                    break
            
            # If no page parameter was found, use 'pageIndex' as default
            if not page_param_found:
                params['pageIndex'] = str(next_page)
            
            # Construct query string
            query_parts = [f"{k}={v}" for k, v in params.items()]
            next_page_url = f"{base_url}?{'&'.join(query_parts)}"
        
        return next_page_url
