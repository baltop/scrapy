import scrapy
from .. import items

class YoutubeSpider(scrapy.Spider):
    name = "youtube"
    allowed_domains = ["youtube.com"]
    start_urls = ["https://youtube.com/"]

    def parse(self, response):
        videos_element = response.css('ytd-rich-item-renderer')
        details_div = videos_element.xpath('//div[@id="details"]')
        title = details_div.xpath('//a[@id="video-title-link"]/@title').get()
        channel = details_div.xpath('//*[@id="text"]/a/text()').get()
        item = self.get_video_item(title, channel)
        self.log(item)
        yield item

    def get_video_item(self, title, channel):
        video_item = items.VideoItem()
        video_item['title'] = title
        video_item['channel'] = channel
        return video_item 