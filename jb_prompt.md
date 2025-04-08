
** 개요 

이 사이트의  코드명은 'dip'이고,  최초 접근 url은 "https://www.dip.or.kr/home/notice/businessbbs/boardList.ubs?sfpsize=10&fboardcd=business&sfkind=&sfcategory=&sfstdt=&sfendt=&sfsearch=ftitle&sfkeyword=&sfpage=1" 이다.
프로그램의 궁극적인  목적은 최초 url에서 가져온 html파일을 파싱하여 bbs형태의 파일에서 쓰레드 혹은 아이템에 해당하는 url들을 수집하고 저장한 뒤에,
bbs에서 다음 페이지에 행당하는 링크를 찾아서 다음 페이지의 html을 가져와서 위와 같이 쓰레드 혹은 아이템에 해당하는 url들을 수집하여 기존에 저장된 곳에 추가
저장한다. 전체 6페이지까지 반복하고, 쓰레드 혹은 아이템의 url을 수집 저장을 한 후 그 저장 리스트를 가져와서 루프를 돌면서 url의 html 페이지를 가져와서 
본문인 공고에 해당하는 부분만 markdown 파일로 저장하고 만약 첨부 문서가 있으면 첨부 문서를 다운로드 받아 저장한다.


** 단계별 상세 처리 방안

- scrapy 프레임워크를 이용하여 코딩한다.  btp.py만 참고해서 코딩한다. 

- 새로 작성하는 snip 스파이더의 소스인 dip.py 이외에는 수정하거나 변경하지 말것.

- 최초 접근 url을 fetch mcp server를 이용하여 fetch시  raw=true, max_length=500000 옵션으로 다운 받은 후에 html을 구조적으로 parsing해서 쓰레드의 url 들을 추출할 selector(element, id, class)를 특정한다.

- 위와 더불어 다음 페이지의 링크도 추출할 수 있도록 selector나 url 패턴을 조사한다.

- 사이트의 코드명에 해당하는 spider 를 만든다. (dip.py)

- 최초 접근 url에서 html을 가져와서 쓰레드의 url을 추출하여 리스트에 저장하고 다음 페이지를 가져와서 반복하는 소스를 작성한다.

- 페이지가 6페이지가 넘으면 반복을 중단한다.

- 추출한 url을 하나씩 꺼내서 해당 페이지를 가져와서 공고 본문을 추출하여 markdown파일 변환하여 저장하고 첨부파일이 있으면 다운로드 받아 저장하는 소스를 추가한다.

- 공고 본문을 변환한 markdown파일은 dip_output 아래에 '게시판번호'.md로 저장하고 첨부파일은 '게시판번호'로 directory를  만들고 그 아래에 저장 해줘.

- `scrapy crawl dip` 으로 테스트 하여 에러가 발생할 경우에 소스를 수정해줘. 별도의 테스트용 소스코드는 만들지 말 것.

- scrapy shell 명령으로 debug해 볼  것.

** 주의 지항

- 첨부파일 저장시에  # Content-Type 헤더로 확장자 추측 할 때 조건이 맞는 것이 없으면 그냥 파일명을 반환할 것. 뒤에  '.bin' 을 붙이지 말것.


- 첨부 파일 다운로드시에  # 한글 파일명 처리를 해야 할 경우 
  
  ```
  filename = filename.encode('latin1').decode('utf-8', errors='ignore')
  ```
  대신에 
  ```
  filename = unquote(server_filename)
  ```
  을 사용할 것.
  
  
  