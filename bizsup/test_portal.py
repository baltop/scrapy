import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 포털 사이트 페이지 로드
        await page.goto("https://portal.snip.or.kr:8443/portal/snip/MainMenu/businessManagement/application.page?portlet=2025-0064&portlet2=3945&homeYn=Y")
        
        # 페이지 로딩 완료까지 대기
        await page.wait_for_load_state("networkidle")
        
        # HTML 요소 검색
        title_elements = [
            ".title", 
            ".tt", 
            ".sub_detail_wrap h3", 
            ".board_view_tit",
            ".bbs_view_title",
            "h3.title",
            ".table_view th",
            ".view_tit",     # 추가 선택자
            "h3",            # 추가 선택자
            ".page_tit"      # 추가 선택자
        ]
        
        print("Title 선택자 테스트:")
        for selector in title_elements:
            elements = await page.query_selector_all(selector)
            text = ""
            if elements and len(elements) > 0:
                text = await elements[0].text_content()
            print(f"{selector}: {len(elements)} 요소 발견, 텍스트: {text.strip() if text else '없음'}")
        
        content_elements = [
            ".content",
            ".board_view_cont",
            ".sub_detail_con",
            ".bbs_view_content",
            ".table_view .content",
            "div.view_cont",
            ".page_content",   # 추가 선택자
            "#contents",       # 추가 선택자
            "article",         # 추가 선택자
            ".article"         # 추가 선택자
        ]
        
        print("\nContent 선택자 테스트:")
        for selector in content_elements:
            elements = await page.query_selector_all(selector)
            text = ""
            if elements and len(elements) > 0:
                text = await elements[0].text_content()
                text = text[:50] + "..." if len(text) > 50 else text
            print(f"{selector}: {len(elements)} 요소 발견, 텍스트: {text.strip() if text else '없음'}")
        
        attachment_elements = [
            ".file a",
            ".file_list a",
            ".attachfile a",
            "a[href*='fileDown']",
            "a[href*='download']",
            ".bbs_view_file a",
            ".file_section a"
        ]
        
        print("\nAttachment 선택자 테스트:")
        for selector in attachment_elements:
            elements = await page.query_selector_all(selector)
            print(f"{selector}: {len(elements)} 요소 발견")
            for e in elements[:3]:  # 첫 3개만 출력
                href = await e.get_attribute("href")
                text = await e.text_content()
                print(f" - href: {href}, text: {text.strip() if text else '없음'}")
        
        # HTML 소스 덤프 (디버깅용)
        html = await page.content()
        with open("portal_dump.html", "w", encoding="utf-8") as f:
            f.write(html[:20000])  # 처음 20000자만 저장
        
        await browser.close()

asyncio.run(main())