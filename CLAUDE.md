# Scrapy Project Guidelines

## Commands
- Run spider: `scrapy crawl <spider_name>` (from project directory)
- Run single spider with output: `scrapy crawl <spider_name> -o output.json`
- Create new spider: `scrapy genspider <spider_name> <domain>`
- Shell for testing selectors: `scrapy shell <url>`
- Check spider: `scrapy check <spider_name>`
- List spiders: `scrapy list`

## Code Style
- **Imports**: Standard library first, then third-party, then local (alphabetical)
- **Classes**: CamelCase naming
- **Methods/Functions**: snake_case naming
- **Constants**: UPPERCASE with underscores
- **Indentation**: 4 spaces, no tabs
- **Line Length**: Max 100 characters
- **Error Handling**: Use try/except only when necessary, prefer specific exceptions
- **Spider Methods**: Follow Scrapy conventions (parse, parse_item, etc.)
- **Documentation**: Docstrings for spiders and complex methods
- **Type Hints**: Use for function parameters and return values

## Project Structure
- Keep spiders in spiders/ directory
- Define item classes in items.py
- Configure pipelines in pipelines.py and settings.py
- Custom middlewares in middlewares.py