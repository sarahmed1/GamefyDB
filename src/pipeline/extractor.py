import os
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_html_file(filepath: str) -> dict | None:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.warning(f"Failed to read file {filepath}: {e}")
        return None

    if not content.strip():
        logger.warning(f"Empty or unparseable HTML in {filepath}")
        return None

    # Using lxml parser
    soup = BeautifulSoup(content, 'lxml')

    # Basic extraction logic for tests
    # We expect a <title> and an <a> tag
    title_tag = soup.find('title')
    a_tag = soup.find('a')

    title = title_tag.text.strip() if title_tag else None
    url = a_tag.get('href', '').strip() if a_tag else None

    if not title or not url:
        logger.warning(f"Missing critical fields in {filepath}")
        return None

    # Extract all other random tags into a dict for raw_data
    # Or just return a flat dict to satisfy GameRecordSchema
    data = {
        'source_file': filepath,
        'title': title,
        'url': url,
        'status': 'extracted'
    }

    return data
