import scrapy


class GntpSpider(scrapy.Spider):
    name = "gntp"
    allowed_domains = ["gntp.or.kr"]
    start_urls = ["https://www.gntp.or.kr/biz/agency"]

    def parse(self, response):
        pass
