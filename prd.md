# Product Requirements Specification: Configuration-based Web Content Extractor

**Version:** 1.0  
**Date:** 2025-03-27  
**Status:** Defined

## 1. Introduction

This document defines the requirements for a Python-based web crawler designed to extract specific content sections from multiple target websites, convert them into Markdown format, and store them locally. The crawler’s behavior is configured via an external CSV file, allowing the user to specify target URLs, related parameters for iteration, and markers to identify desired content blocks without modifying the core script. The primary use case is to collect updates or articles from specific web pages (e.g., notices or posts), with a particular focus on content identified by start and end markers within the HTML structure after initial cleanup and Markdown conversion.

## 2. Goals and Objectives

- **Automated Content Collection:** Automatically fetch and save specific content sections from predefined web pages.  
- **Configurability:** Allow users to easily define and manage target websites and extraction parameters via a CSV file without modifying the core script.  
- **Content Segmentation:** Extract only the relevant portion of a web page’s content using user-defined start and end text markers.  
- **Format Conversion:** Convert extracted HTML content into clean Markdown format.  
- **Structured Storage:** Store extracted content in a hierarchical directory structure based on the site name and crawling date.  
- **Basic Server Load Prevention:** Implement simple delays between requests to avoid overloading the target server.  

## 3. Scope

### 3.1. Included Scope:

- Reading the crawler configuration from the specified CSV file (`server.csv`).  
- From the CSV, read each site name and starting URL to compile a list of target sites.  
- For the first site, fetch the web page at the starting URL (pointing to the first page of the bulletin board) and retrieve its content.  
- Parse the URLs of each BBS entry on the page to create a list of entry URLs.  
- From the page’s pagination section, parse the URL for the next page and fetch the next page by incrementing the current page number by 1.  
- In the same manner as the previous step, fetch page *n+1* and parse that page’s entry URLs, adding them to the existing list.  
- Continue this process until encountering an entry index that has been read previously, or until entries up to a previously read date (based on posting date) have been processed.  
- Starting from the beginning of the list of BBS entry URLs, iterate through each URL to fetch the detailed web page.  
- Parse the key content of the detail page and download any attachments using their download links, creating a directory named after the detail page index and saving the attachments there.  
- Use a standard browser `User-Agent` header.  
- Set a timeout for HTTP requests.  
- Implement basic error handling for HTTP request failures (e.g., connection errors, timeouts, non-2xx status codes).  
- Parse the fetched HTML content using BeautifulSoup.  
- Remove `<script>` and `<style>` elements (and their contents) from the parsed HTML.  
- Convert the cleaned HTML snippet to Markdown format (using the `markdownify` library with ATX heading style).  
- From the generated Markdown content, extract the lines of text between the specified start and end marker strings (including the start marker line, excluding the end marker line).  
- Create the directory structure: `./<site_name>/<YYYY-MM-DD>/<detail_page_index>/`.  
- Save the extracted Markdown content as a file named `<detail_page_index_value>.md` within that directory.  
- Implement a random delay of 1–3 seconds after processing each URL.  
- Print status messages to standard output (including the current site being processed, the URL being crawled, confirmation of file saves, and any errors).  

### 3.2. Excluded Scope:

- Handling of complex login mechanisms or session management.  
- Advanced anti-bot bypass techniques (e.g., CAPTCHA solving, complex header manipulation, IP rotation).  
- Saving the extracted data in any format other than individual Markdown files (e.g., storing in a database or other file formats).  
- Providing a graphical user interface (GUI).  
- Incremental crawling or change detection (the content is re-fetched in full on each execution).  
- Advanced error handling and retry logic beyond basic request exception handling.  
- Sophisticated rate limiting beyond simple delays, or compliance with `robots.txt`.  
- Input validation for the CSV file contents beyond basic row-length checks.  
- Handling of iteration parameters that are not numeric.  

## 4. Functional Requirements

| ID   | Requirement Description                                                 | Details and Constraints                                                                                                                                                                            | Priority  |
| :--- | :---------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------- |
| FR1  | **Configuration Loading:** The system must read the crawler configuration from a CSV file named `server.csv` in the same directory as the script. | - CSV format: Each row is `url, param_name, site_name, category, start_marker, end_marker`.<br>- Encoding: UTF-8.<br>- Any row with fewer than 6 columns should be skipped or handled appropriately (currently such rows are implicitly skipped). | Required |
| FR2  | **Initial Parameter Extraction:** For each configuration entry, the system must extract the initial *integer* value associated with `param_name` from the provided `url`.                    | - It is assumed that the URL contains `param_name=`.<br>- Extract the consecutive digits immediately following `param_name=`.<br>- If extraction fails or the result is not numeric, skip processing for that URL.                             | Required |
| FR3  | **URL Generation:** The system must decrement the initial parameter value by 0, 1, 2, ..., 9 and reconstruct the URL to generate 10 target URLs for each configuration entry.                | - Replace the original numeric value associated with `param_name` in the URL with the new decremented value.<br>- Handle any non-parameter portion of the URL that follows the numeric value appropriately.                                   | Required |
| FR4  | **Web Page Fetching:** The system must fetch the HTML content of each generated URL via an HTTP GET request.                                          | - Include a `User-Agent` header (e.g., "Mozilla/5.0...").<br>- Set a request timeout of 10 seconds.<br>- If an unsuccessful HTTP status code is encountered (e.g., 4xx or 5xx), an error should be raised.                                      | Required |
| FR5  | **HTML Parsing and Cleanup:** The system must parse the fetched HTML content and remove `<script>` and `<style>` tags and their contents.           | - Use BeautifulSoup with a standard parser (e.g., `html.parser`).                                                                                                                                   | Required |
| FR6  | **Markdown Conversion:** The system must convert the cleaned HTML structure into Markdown format.                                                   | - Use the `markdownify` library.<br>- Preserve links in the content.<br>- Use ATX style for headers (e.g., `# Header`).                                                                                 | Required |
| FR7  | **Content Section Extraction:** The system must process the generated Markdown text line by line and extract only the lines between the specified `start_marker` and `end_marker`.         | - Begin extraction from the line immediately after the one containing `start_marker`.<br>- Stop extraction at the line immediately before the one containing `end_marker`.<br>- Markers are identified by simple substring matching.<br>- If the start marker is not found, no content is extracted.<br>- If no end marker is found after the start marker, extract content until the end of the text. | Required |
| FR8  | **Output File Saving:** The system must save the extracted Markdown content to a local file.                                                        | - Directory structure: `./<site_name>/<YYYY-MM-DD>/`. If the directory does not exist, it must be created.<br>- File name: `<current_parameter_value>.md`.<br>- File encoding: UTF-8.                                                        | Required |
| FR9  | **Request Throttling:** The system must pause execution for a random duration between 1 and 3 seconds after processing each URL.                   | - Use `time.sleep()` in combination with `random.uniform(1, 3)` to implement the delay.                                                                                                              | Required |
| FR10 | **Basic Logging:** The system must output status information to the console during execution.                                                     | - Display the site/category being processed.<br>- Print the URL currently being crawled.<br>- Confirm successful saves and display the output file path.<br>- Print error messages for any errors encountered during crawling or processing. | Required |
| FR11 | **Error Handling (Network):** The system must catch exceptions during web page fetching and print an error message.                                | - Catch `requests.RequestException` exceptions.<br>- Print the failed URL and the error message.<br>- Continue with the next URL or the next configuration entry.                                     | Required |
| FR12 | **Error Handling (Content Processing):** The system should catch general exceptions during content processing (parsing, Markdown conversion, marker logic) and print an error message.    | - Catch a generic `Exception`.<br>- Print an error message indicating the processing failure.<br>- Log the error and return an empty string for the content so that an empty `.md` file is saved (or if saving empty content should be prevented, do not create a file for that entry). | Recommended |

## 5. Non-functional Requirements

| ID   | Requirement Description    | Details and Constraints                                                                                                        | Priority    |
| :--- | :------------------------ | :------------------------------------------------------------------------------------------------------------------------------ | :---------- |
| NFR1 | **Reliability:**          | The script should handle common network errors gracefully and continue processing other URLs/config entries. A single failure should not crash the program. | Required    |
| NFR2 | **Maintainability:**      | The code should be reasonably well-structured into functions for clarity of operation. Type hints should be used for readability and maintainability. | Recommended |
| NFR3 | **Usability (Developer):** | Configuration via the external `server.csv` file should be straightforward. Console output should provide appropriate feedback about the crawling process. | Required    |
| NFR4 | **Performance:**          | The script is not highly optimized for speed (requests are handled sequentially per site), but it should complete within a reasonable time for about 10 pages per site. | Recommended |
| NFR5 | **Resource Usage:**       | Memory and CPU consumption should remain reasonable for typical web page processing tasks.                                       | Recommended |

## 6. Input/Output Specifications

### 6.1. Input:

- **`server.csv` file:**  
  - **Location:** Same directory as the script.  
  - **Encoding:** UTF-8.  
  - **Columns:**  
    1. `site_code`: Human-readable code name of the website, used for creating output directories (e.g., `Example Notices`).  
    2. `url`: Base URL containing the parameter to decrement (e.g., `http://example.com/notice?boardId=123&page=1`).  

### 6.2. Output:

- **Markdown files:**  
  - **Location:** `./<site_name>/<YYYY-MM-DD>/<numeric_parameter_value>.md`  
  - **Content:** The extracted and cleaned content (in Markdown format).  
  - **Encoding:** UTF-8.  

- **Console output:**  
  - Status messages indicating progress and errors (as defined in FR10).  

## 7. Error Handling Strategy

- **Network Error (`requests.RequestException`):** Log the error along with the URL and proceed to the next URL. No retry is attempted.  
- **Parameter Extraction Error:** Log the error with the URL and skip processing of that entire configuration entry (site).  
- **Content Processing Error (`process_content` Exception):** Log the error and return an empty string for the content so that an empty `.md` file is saved (or if saving empty content is meant to be prevented, no file is created for that entry).  
- **File System Error (Directory/File Creation):** If permissions are incorrect, standard Python `IOError`/`OSError` exceptions could terminate the script. Basic handling includes using `os.makedirs(exist_ok=True)`. More robust handling is outside the scope of this version.  

## 8. Dependencies

The system requires the following Python libraries to be installed:

- `scrapy`  
- `playwright`  
- `scrapy-playwright`  
- `requests`  
- `beautifulsoup4`  
- `markdownify`  
- `typing` (part of the standard library, but usage implies Python 3.10+)  

## 9. Future Considerations / Potential Improvements (Outside v1.0 Scope)

- Support for pagination/iteration parameters that are non-numeric or more complex.  
- More robust error handling and retry logic, including exponential backoff.  
- Asynchronous fetching for significantly improved performance (e.g., using `asyncio` and `aiohttp`).  
- Database integration for storing results.  
- Delta checking to download only new or changed content.  
- More sophisticated content extraction methods (e.g., using CSS selectors or XPath on HTML before Markdown conversion).  
- Respecting `robots.txt` in crawling.  
- Better configuration management (e.g., using YAML or JSON for configuration files).  
- Monitoring and notification features.  

---
