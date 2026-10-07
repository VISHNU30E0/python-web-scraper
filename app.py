from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_valid_url(url):
    """Validate URL format."""
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except Exception:
        return False


def scrape_website(url):
    """Scrape website and extract key data from the page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        data = {
            'url': url,
            'title': soup.title.string if soup.title else 'No title found',
            'headings': [],
            'links': [],
            'paragraphs': [],
            'images': []
        }

        for heading in soup.find_all(['h1', 'h2', 'h3']):
            text = heading.get_text(strip=True)
            if text:
                data['headings'].append(text)

        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            if text and href:
                full_url = urljoin(url, href)
                data['links'].append({'text': text, 'href': full_url})

        for para in soup.find_all('p'):
            text = para.get_text(strip=True)
            if text:
                data['paragraphs'].append(text)

        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', 'No alt text')
            if src:
                full_url = urljoin(url, src)
                data['images'].append({'src': full_url, 'alt': alt})

        return {
            'success': True,
            'data': data,
            'message': 'Scraping successful'
        }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'message': 'Request timeout. The website took too long to respond.'
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'message': 'Connection error. Please check the URL and try again.'
        }
    except requests.exceptions.HTTPError as e:
        return {
            'success': False,
            'message': f'HTTP error: {e.response.status_code}'
        }
    except Exception as e:
        logger.error(f'Scraping error: {str(e)}')
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    data = request.get_json()
    url = (data or {}).get('url', '').strip()

    if not url:
        return jsonify({'success': False, 'message': 'URL is required'}), 400

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not is_valid_url(url):
        return jsonify({'success': False, 'message': 'Invalid URL format'}), 400

    result = scrape_website(url)
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Page not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'message': 'Server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
