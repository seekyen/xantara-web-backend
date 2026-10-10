"""Online product lookup (name/barcode -> suggestions with image) for the inventory editor.

Uses the Open Food Facts family of open databases, which share one API: food and
drinks, beauty and personal care, general products, and pet food. Every source is
queried independently, so one being down never blocks the others. Nothing is saved
here; the admin picks a suggestion in the browser. Image downloads are proxied and
restricted to the sources' own image hosts (no arbitrary URL fetching).
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

USER_AGENT = 'XantaraPOS/1.0 (inventory product lookup; ckcaagbay@gmail.com)'
TIMEOUT = 8
MAX_JSON_BYTES = 1_000_000
MAX_IMAGE_BYTES = 5_000_000
MAX_RESULTS = 8
FIELDS = 'code,product_name,generic_name,brands,quantity,image_front_url,image_front_small_url'
SOURCES = [('Open Food Facts', 'openfoodfacts.org'), ('Open Beauty Facts', 'openbeautyfacts.org'),
           ('Open Products Facts', 'openproductsfacts.org'), ('Open Pet Food Facts', 'openpetfoodfacts.org')]
IMAGE_HOSTS = {f'images.{domain}' for _, domain in SOURCES}
IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _open(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
    return urllib.request.build_opener(NoRedirect).open(request, timeout=TIMEOUT)


def fetch_json(url):
    """Parsed JSON, or None on any network/format failure."""
    try:
        with _open(url) as response:
            return json.loads(response.read(MAX_JSON_BYTES).decode('utf-8'))
    except urllib.error.HTTPError as error:
        if error.code != 404:
            return None
        # "Not found" is a real answer (HTTP 404 with a JSON body), not an outage.
        try:
            return json.loads(error.read(MAX_JSON_BYTES).decode('utf-8'))
        except (OSError, ValueError, UnicodeDecodeError):
            return None
    except (urllib.error.URLError, OSError, ValueError, UnicodeDecodeError):
        return None


def allowed_image_url(url):
    parts = urllib.parse.urlsplit(url or '')
    return parts.scheme == 'https' and parts.hostname in IMAGE_HOSTS and not parts.username


def fetch_image(url):
    """(bytes, content_type) for an allowlisted https image; raises ValueError otherwise."""
    if not allowed_image_url(url):
        raise ValueError('This image address is not allowed.')
    try:
        with _open(url) as response:
            content_type = response.headers.get_content_type()
            body = response.read(MAX_IMAGE_BYTES + 1)
    except (urllib.error.URLError, OSError):
        raise ValueError('The image could not be downloaded.')
    if content_type not in IMAGE_TYPES or len(body) > MAX_IMAGE_BYTES:
        raise ValueError('The image is not a supported picture or is too large.')
    return body, content_type


def _candidate(product, source, domain):
    code = str(product.get('code') or '').strip()
    name = str(product.get('product_name') or '').strip()
    if not code.isdigit() or not name:
        return None
    image = product.get('image_front_url') or ''
    thumb = product.get('image_front_small_url') or image
    return {'barcode': code, 'name': name[:120], 'description': str(product.get('generic_name') or '').strip()[:120],
            'brand': str(product.get('brands') or '')[:80],
            'quantity': str(product.get('quantity') or '')[:40], 'source': source,
            'source_url': f'https://world.{domain}/product/{code}',
            'image_url': image if allowed_image_url(image) else '',
            'thumb_url': thumb if allowed_image_url(thumb) else ''}


def _by_barcode(barcode, source):
    label, domain = source
    data = fetch_json(f'https://world.{domain}/api/v2/product/{barcode}.json?fields={FIELDS}')
    if data is None:
        return label, None
    product = data.get('product') if data.get('status') == 1 else None
    return label, [c for c in [_candidate(product, label, domain)] if c] if product else []


def _by_name(name, source):
    label, domain = source
    query = urllib.parse.urlencode({'search_terms': name, 'search_simple': 1, 'action': 'process', 'json': 1,
                                    'page_size': 5, 'fields': FIELDS})
    url = f'https://world.{domain}/cgi/search.pl?{query}'
    data = fetch_json(url)
    if data is None:
        # The search endpoints answer "temporarily unavailable" now and then; one quick retry usually clears it.
        time.sleep(1)
        data = fetch_json(url)
    if data is None or not isinstance(data.get('products'), list):
        return label, None
    return label, [c for c in (_candidate(p, label, domain) for p in data['products'] if isinstance(p, dict)) if c]


def _run(function, argument):
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        outcomes = list(pool.map(lambda source: function(argument, source), SOURCES))
    unavailable = [label for label, found in outcomes if found is None]
    merged, seen = [], set()
    for _, found in outcomes:
        for item in found or []:
            if item['barcode'] not in seen:
                seen.add(item['barcode'])
                merged.append(item)
    return merged[:MAX_RESULTS], unavailable


def lookup(barcode='', name=''):
    """Barcode matches first, then name matches (deduplicated), each tagged with how it matched.

    Open databases are user-contributed, so an exact barcode can still point at a junk or
    wrong entry; the name results are always added so the admin can compare.
    """
    barcode, name = barcode.strip(), re.sub(r'\s+', ' ', name).strip()
    results, unavailable = [], []
    if barcode:
        found, failed = _run(_by_barcode, barcode)
        results += [{**item, 'match': 'barcode'} for item in found]
        unavailable = failed
    if name:
        found, failed = _run(_by_name, name)
        known = {item['barcode'] for item in results}
        results += [{**item, 'match': 'name'} for item in found if item['barcode'] not in known]
        unavailable = failed
    return {'matched_by': 'barcode' if any(r['match'] == 'barcode' for r in results) else 'name' if results else None,
            'results': results[:MAX_RESULTS], 'unavailable': unavailable}
