#!/usr/bin/env python
# 간단한 테스트 실행기

import sys
import os
from pathlib import Path

# 스파이더 import를 위한 경로 설정
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 필요한 패키지 import
from scrapy.crawler import CrawlerProcess
from bizsup.spiders.jbba import JbbaSpider

# 설정
os.makedirs("jbba_output/attachments", exist_ok=True)

# Scrapy 크롤러 프로세스 설정
process = CrawlerProcess(settings={
    'BOT_NAME': 'bizsup',
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'LOG_LEVEL': 'INFO',
    'ROBOTSTXT_OBEY': False,
    'DOWNLOAD_DELAY': 1,
    'CONCURRENT_REQUESTS': 1,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
})

# 테스트할 URL
test_url = "https://www.jbba.kr/bbs/board.php?bo_table=sub01_09&wr_id=1529"

# 스파이더 실행
process.crawl(JbbaSpider, start_urls=[test_url])
process.start()  # 스크립트는 여기서 블록됨