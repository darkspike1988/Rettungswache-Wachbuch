import functools
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('PRESENTATION_QA_DIR', '/opt/data/cache/presentation-qa'))
url = sys.argv[1] if len(sys.argv) > 1 else None
server = None
if not url:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(out / 'dist'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
exe = os.environ.get('CHROMIUM_EXECUTABLE', '/opt/hermes/.playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell')
evidence = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, headless=True, args=['--no-sandbox'])
        for label, width, height in [('desktop',1440,1000), ('mobile',390,844), ('narrow',320,740), ('tablet',768,1024)]:
            page = browser.new_page(viewport={'width':width,'height':height}, reduced_motion='reduce')
            errors, requests = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
            page.on('request', lambda r: requests.append({'url':r.url, 'method':r.method, 'type':r.resource_type}))
            page.on('response', lambda r: errors.append(f'HTTP {r.status}: {r.url}') if r.status >= 400 else None)
            assert page.goto(url, wait_until='networkidle').status == 200
            assert page.locator('h1').count() == 1
            assert page.locator('h1').inner_text() == 'Die nächste Schicht. Schon im Bild.'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
            for button in page.locator('[data-pw-demo] button').all():
                if button.is_visible():
                    assert button.bounding_box()['height'] >= 47.5, 'Touch target below 48px'
            # Real keyboard entry and visible focus, including the skip link.
            page.keyboard.press('Tab')
            assert page.locator(':focus').get_attribute('href') == '#inhalt'
            assert page.locator(':focus').evaluate('(e)=>getComputedStyle(e).outlineStyle') != 'none'
            page.locator('[data-pw-start]').first.click()
            # Regression: opening a revision must never destroy overview card text.
            expected_titles = page.locator('[data-pw-ho] strong').all_text_contents()
            for index, revision in [(0,'3'), (1,'2'), (2,'1')]:
                page.locator('[data-pw-view="overview"]').click()
                page.locator('[data-pw-ho]').nth(index).click()
                assert page.locator('[data-pw-ho-title]').inner_text() == expected_titles[index]
                assert page.locator('[data-pw-panel="handover"] [data-pw-rev]').first.inner_text() == revision
                assert page.locator('[data-pw-rev-item]:visible').count() == int(revision)
                page.locator('[data-pw-ack]').click()
                assert f'Revision {revision} bestätigt' in page.locator('[data-pw-ack-status]').inner_text()
                assert 'bleibt offen' in page.locator('[data-pw-ack-status]').inner_text()
                assert page.locator('[data-pw-ho] strong').all_text_contents() == expected_titles
            page.locator('[data-pw-view="tasks"]').click()
            tasks = page.locator('[data-pw-task]')
            tasks.first.check()
            assert page.locator('[data-pw-task-count]').inner_text() == '1 von 7 erledigt'
            page.locator('[data-pw-view="calendar"]').click()
            assert page.locator('[data-pw-panel="calendar"]').is_visible()
            page.locator('[data-pw-reset]').click()
            assert tasks.evaluate_all('(es)=>es.every(e=>!e.checked)')
            assert page.locator('[data-pw-task-count]').inner_text() == '0 von 7 erledigt'
            assert page.locator('[data-pw-panel="overview"]').is_visible()
            page.locator('[data-pw-view="handover"]').focus()
            page.keyboard.press('Enter')
            assert page.locator('[data-pw-panel="handover"]').is_visible()
            assert page.locator('[data-pw-panel="handover"] [data-pw-rev]').first.inner_text() == '3'
            page.locator('[data-pw-reset]').click()
            page.locator('summary').first.click()
            assert page.locator('details').first.get_attribute('open') == ''
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not page.evaluate('Object.keys(localStorage).length + Object.keys(sessionStorage).length')
            assert not any(r['type'] in ['fetch','xhr'] or r['method'] != 'GET' for r in requests)
            assert not errors, errors
            page.screenshot(path=str(out / f'after-{label}.png'), full_page=True)
            page.locator('#demo').screenshot(path=str(out / f'phone-{label}.png'))
            evidence.append({'viewport':{'width':width,'height':height}, 'flows':'all passed', 'console_errors':errors, 'requests':requests})
            page.close()
        page = browser.new_page(java_script_enabled=False, viewport={'width':390,'height':844})
        page.goto(url)
        assert page.locator('noscript').is_visible()
        assert page.get_by_role('link', name='Vorführung ansehen').is_visible()
        evidence.append({'javascript_disabled':'fallback visible'})
        browser.close()
finally:
    if server:
        server.shutdown()
(out / 'browser-evidence.json').write_text(json.dumps({'url':url,'checks':evidence}, indent=2))
print(f'BROWSER QA PASSED: {len(evidence)-1} viewports, three handover revisions, task/ack separation, reset, keyboard, FAQ, reduced motion, no-JS fallback, no XHR or storage')
