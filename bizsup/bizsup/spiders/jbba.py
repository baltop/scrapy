import scrapy
import logging


class JbbaSpider(scrapy.Spider):
    name = "jbba"
    allowed_domains = ["jbba.kr"]
    start_urls = ["https://www.jbba.kr/bbs/board.php?bo_table=sub01_09"]
    
    def __init__(self, *args, **kwargs):
        super(JbbaSpider, self).__init__(*args, **kwargs)
        self.all_thread_urls = []  # Initialize list to store all thread URLs
        self.max_pages = 6  # Number of pages to process
    
    def parse(self, response):
        """
        Parse BBS-style page, extract thread links and follow pagination
        """
        self.logger.info(f"Processing page: {response.url}")
        
        # Extract thread links using the actual HTML structure of jbba.kr
        # Based on actual HTML analysis, the links are in td.td_subject > a
        thread_links = response.css('td.td_subject a::attr(href)').getall()
        self.logger.info(f"Found {len(thread_links)} thread links")
        
        # Clean and convert to absolute URLs
        thread_urls = [response.urljoin(link) for link in thread_links if link]
        
        # Filter out non-thread URLs (looking for URLs with wr_id parameter)
        filtered_thread_urls = []
        for url in thread_urls:
            if 'wr_id=' in url and 'javascript:' not in url:
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
        if 'page=' in url:
            try:
                current_page = int(url.split('page=')[1].split('&')[0])
            except (ValueError, IndexError):
                pass
        
        return current_page
    
    def get_next_page_url(self, response, current_page):
        """
        Generate URL for the next page based on actual jbba.kr pagination structure
        """
        next_page = current_page + 1
        
        # Based on actual HTML analysis, pagination links are in nav.pg_wrap a.pg_page
        next_page_selector = f'nav.pg_wrap a.pg_page[href*="page={next_page}"]::attr(href)'
        next_links = response.css(next_page_selector).getall()
        
        if next_links:
            # Use the first matching link
            next_page_url = response.urljoin(next_links[0])
            return next_page_url
        
        # If we couldn't find the next page link through the selector, construct it manually
        base_url = response.url.split('?')[0]
        params = {}
        
        if '?' in response.url:
            query_string = response.url.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        # Update page parameter
        params['page'] = str(next_page)
        
        # Construct query string
        query_parts = [f"{k}={v}" for k, v in params.items()]
        next_page_url = f"{base_url}?{'&'.join(query_parts)}"
        
        return next_page_url
