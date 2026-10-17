"""HTTP discovery compatibility and source-freshness separation."""
import json
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

import asm_select_api as api

@contextmanager
def server():
    http = ThreadingHTTPServer(('127.0.0.1', 0), api.Handler)
    worker = threading.Thread(target=http.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{http.server_port}'
    finally:
        http.shutdown(); http.server_close(); worker.join()

def test_canonical_and_predecessor_paths_preserve_identity_and_source_state():
    with server() as base:
        new = json.load(urlopen(base + '/.well-known/ard.json'))
        old = json.load(urlopen(base + '/.well-known/ai-catalog.json'))
        assert len(new['entries']) == len(old['entries']) > 0
        for current, previous in zip(new['entries'], old['entries']):
            assert current['identifier'] == previous['identifier']
            assert current['url'] == previous['url']
            assert 'extensions' in previous and '@context' not in previous
            for key, value in previous['extensions'][api._AI_CATALOG_EXTENSION].items():
                assert current[key] == value
            assert current['@context'] == [api._ARD_CONTEXT, {'asm': api._ASM_NAMESPACE}]
            assert len(current['representativeQueries']) == 2
            assert all('metadata' in q or 'source verification' in q for q in current['representativeQueries'])
            assert json.load(urlopen(current['url']))['service_id']

def test_publishing_does_not_reverify_a_stale_source():
    source = dict(api._LIBRARY[0], provenance={'last_verified_at': '2000-01-01T00:00:00Z'})
    item = api._ard_entry(source, 'https://example.test')
    assert item['asm:lastVerifiedAt'] == '2000-01-01T00:00:00Z'
    assert item['asm:sourceFreshness'] == 'expired'

def test_landing_pages_advertise_canonical_discovery():
    with server() as base:
        for path in ['/', '/showcase']:
            text = urlopen(base + path).read().decode()
            assert '<link rel="ard" href="/.well-known/ard.json">' in text
