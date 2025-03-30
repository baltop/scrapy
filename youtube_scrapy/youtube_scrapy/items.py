# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html


import scrapy


class VideoItem(scrapy.Item):
    title = scrapy.Field()          # 영상 제목
    channel = scrapy.Field()        # 채널명