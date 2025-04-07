# 요건 정의서

## 1. 개요

본 문서는 웹 스크래핑 시스템의 기능 및 비기능적 요구사항을 정의합니다. 시스템은 두 개의 주요 스크래핑 프로젝트(`bizsup`, `youtube_scrapy`)로 구성되며, 각각 특정 웹사이트들로부터 데이터를 수집하는 것을 목적으로 합니다.

## 2. 범위

### 2.1. 포함 범위

*   **bizsup 프로젝트:**
    *   지정된 비즈니스 지원 정보 웹사이트(egbiz, gntp, jbba, snipBottom)에서 데이터 스크래핑.
    *   동적 웹 페이지 처리 (Playwright 사용).
    *   페이지네이션 처리 (gntp, jbba, snipBottom).
    *   "더보기" 버튼과 같은 상호작용 처리 (egbiz).
    *   스크래핑된 데이터 정의 (`BizsupItem`).
*   **youtube_scrapy 프로젝트:**
    *   YouTube 및 기타 소스(quotes)에서 데이터 스크래핑.
    *   동적 웹 페이지 처리 (Playwright 사용).
    *   스크래핑된 데이터 정의 (`VideoItem`, `QuoteItem`).
*   **공통:**
    *   UTF-8 인코딩으로 데이터 출력.
    *   Scrapy 프레임워크 기반 실행.
    *   Twisted 비동기 네트워킹 사용.

### 2.2. 제외 범위

*   스크래핑된 데이터의 저장 방식 (파일 외 다른 DB 저장 등).
*   수집된 데이터를 활용하는 웹 애플리케이션(`app.py`의 구체적인 기능).
*   사용자 인터페이스.
*   인증 또는 로그인 처리.

## 3. 기능 요구사항

### 3.1. bizsup 스크래퍼

*   **FR-BIZ-001:** `egbiz` 스파이더는 대상 웹사이트의 메인 페이지에서 스레드 링크를 추출해야 한다.
*   **FR-BIZ-002:** `egbiz` 스파이더는 "더보기" 버튼을 클릭하여 추가 콘텐츠를 로드하고 처리해야 한다. (Playwright 필요)
*   **FR-BIZ-003:** `gntp`, `jbba`, `snipBottom` 스파이더는 대상 웹사이트의 목록 페이지에서 데이터를 추출해야 한다.
*   **FR-BIZ-004:** `gntp`, `jbba`, `snipBottom` 스파이더는 페이지네이션을 처리하여 모든 페이지의 데이터를 수집해야 한다.
*   **FR-BIZ-005:** 각 스파이더는 `BizsupItem` 형식에 맞춰 데이터를 수집해야 한다.

### 3.2. youtube_scrapy 스크래퍼

*   **FR-YT-001:** `youtube` 스파이더는 YouTube에서 비디오 제목과 채널 정보를 추출해야 한다.
*   **FR-YT-002:** `youtube` 스파이더는 `VideoItem` 형식에 맞춰 데이터를 수집해야 한다.
*   **FR-YT-003:** `quotes` 스파이더는 대상 웹사이트에서 인용구 데이터를 추출해야 한다. (Playwright 필요)
*   **FR-YT-004:** `quotes` 스파이더는 `QuoteItem` 형식에 맞춰 데이터를 수집해야 한다.
*   **FR-YT-005:** `quotes` 스파이더는 스크래핑 중 발생하는 오류를 처리하고 로그를 남겨야 한다 (`errback`).

## 4. 비기능 요구사항

*   **NFR-PERF-001:** 스크래핑 요청 간 지연 시간(`DOWNLOAD_DELAY`)은 3초로 설정되어야 한다. (bizsup)
*   **NFR-PERF-002:** 도메인당 동시 요청 수는 1개로 제한되어야 한다. (bizsup)
*   **NFR-ROBOTS-001:** `robots.txt` 파일 규칙을 준수하지 않아야 한다 (`ROBOTSTXT_OBEY = False`). (bizsup, youtube_scrapy)
*   **NFR-ENCODING-001:** 출력 데이터는 UTF-8 인코딩을 사용해야 한다 (`FEED_EXPORT_ENCODING = "utf-8"`). (bizsup, youtube_scrapy)
*   **NFR-TECH-001:** 비동기 처리를 위해 `twisted.internet.asyncioreactor.AsyncioSelectorReactor`를 사용해야 한다. (bizsup, youtube_scrapy)
*   **NFR-TECH-002:** 동적 웹 페이지 렌더링을 위해 Playwright 핸들러를 사용해야 한다 (`DOWNLOAD_HANDLERS`). (bizsup, youtube_scrapy)

## 5. 데이터 요구사항

*   **DR-BIZ-001:** `bizsup` 프로젝트는 `bizsup/items.py`에 정의된 `BizsupItem` 구조에 따라 데이터를 수집해야 한다.
*   **DR-YT-001:** `youtube_scrapy` 프로젝트는 `youtube_scrapy/items.py`에 정의된 `VideoItem` 구조에 따라 데이터를 수집해야 한다.
*   **DR-YT-002:** `youtube_scrapy` 프로젝트는 `youtube_scrapy/qitems.py`에 정의된 `QuoteItem` 구조에 따라 데이터를 수집해야 한다.

## 6. 기술 요구사항

*   **TR-LANG-001:** 시스템은 Python 언어로 개발되어야 한다.
*   **TR-FW-001:** 웹 스크래핑 기능은 Scrapy 프레임워크를 사용하여 구현되어야 한다.
*   **TR-LIB-001:** 동적 웹 페이지 처리를 위해 Playwright 라이브러리를 사용해야 한다.
