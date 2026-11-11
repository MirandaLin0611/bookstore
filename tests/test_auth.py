"""Browser regression tests. All auth/API traffic uses an isolated, in-memory mock."""
import functools
import json
import os
from pathlib import Path
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import unittest

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class EmailLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:%d/' % cls.server.server_port
        cls.pw = sync_playwright().start()
        executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium')
        cls.browser = cls.pw.chromium.launch(executable_path=executable, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.code_enabled = True
        self.requests = []
        self.errors = []
        self.verify_status = 200
        self.send_status = 200
        self.nickname = '原本的暱稱'
        self.held_users = []
        self.hold_user = False
        self.contexts = []
        self.context = self.new_context()
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.open_page(self.page)

    def tearDown(self):
        for context in self.contexts:
            context.close()
        self.assertEqual(self.errors, [])

    def new_context(self):
        context = self.browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        context.route('**/config.js*', lambda route: route.fulfill(
            content_type='application/javascript', body='window.APP_CONFIG = ' + json.dumps({
                'SUPABASE_URL': 'https://auth-tests.supabase.co',
                'SUPABASE_KEY': 'test-public-key',
                'EMAIL_CODE_LOGIN': self.code_enabled,
            })))
        context.route('https://**/*', lambda route: (self.errors.append('Unexpected external request'), route.abort()))
        context.route('https://auth-tests.supabase.co/**', self.backend)
        self.contexts.append(context)
        return context

    def open_page(self, page):
        page.goto(self.base, wait_until='networkidle')

    def backend(self, route):
        req = route.request
        self.assertTrue(req.url.startswith('https://auth-tests.supabase.co/'))
        path = req.url.split('.supabase.co', 1)[1].split('?', 1)[0]
        body = req.post_data_json if req.post_data else None
        self.requests.append({'path': path, 'body': body, 'method': req.method})
        status, data = 200, []
        if path == '/auth/v1/otp':
            status, data = self.send_status, {}
        elif path == '/auth/v1/verify':
            status = self.verify_status
            data = {'access_token': 'test-access', 'refresh_token': 'test-refresh', 'expires_in': 3600} if status == 200 else {'code': 'otp_expired'}
        elif path == '/auth/v1/user':
            data = {'id': 'test-parent', 'email': 'parent@example.com'}
            if self.hold_user:
                self.held_users.append(route)
                return
        elif path == '/auth/v1/token':
            data = {'access_token': 'test-renewed', 'refresh_token': 'test-renewed-refresh', 'expires_in': 3600}
        elif path == '/rest/v1/profiles':
            if req.method == 'PATCH':
                self.nickname = body['nickname']
            else:
                data = [{'nickname': self.nickname}]
        elif path == '/rest/v1/rpc/is_admin':
            data = False
        route.fulfill(status=status, content_type='application/json', body=json.dumps(data), headers={'Access-Control-Allow-Origin': '*'})

    def request_email(self, page=None):
        page = page or self.page
        page.locator('#acct').click()
        page.locator('#ac_e').fill('parent@example.com')
        page.locator('#ac_ok').click()
        expect(page.locator('#ac_wait')).to_be_visible()

    def login_with_code(self, page=None):
        page = page or self.page
        self.request_email(page)
        page.locator('#ac_code').fill('123456')
        page.locator('#ac_confirm').click()
        expect(page.locator('#acct')).to_contain_text(self.nickname)

    def test_email_only_request_and_nickname_preserved(self):
        self.assertEqual(self.page.locator('#ac_n').count(), 0)
        self.request_email()
        sent = [r for r in self.requests if r['path'] == '/auth/v1/otp']
        self.assertEqual(sent[0]['body'], {'email': 'parent@example.com', 'create_user': True})
        expect(self.page.locator('#ac_resend')).to_be_disabled()
        self.page.locator('#ac_code').fill('123456')
        self.page.locator('#ac_confirm').click()
        expect(self.page.locator('#acct')).to_contain_text('原本的暱稱')
        self.page.reload(wait_until='networkidle')
        expect(self.page.locator('#acct')).to_contain_text('原本的暱稱')
        self.page.locator('#acct').click()
        expect(self.page.locator('#ac_nn')).to_have_value('原本的暱稱')
        self.page.locator('#ac_nn').fill('一次設定的新暱稱')
        self.page.locator('#ac_sv').click()
        expect(self.page.locator('#acct')).to_contain_text('一次設定的新暱稱')
        self.page.reload(wait_until='networkidle')
        expect(self.page.locator('#acct')).to_contain_text('一次設定的新暱稱')

    def test_invalid_code_does_not_create_session_and_can_retry(self):
        self.request_email()
        self.verify_status = 403
        self.page.locator('#ac_code').fill('000000')
        self.page.locator('#ac_confirm').click()
        expect(self.page.locator('#ac_error')).to_contain_text('驗證碼錯誤、已使用或已過期')
        self.assertIsNone(self.page.evaluate('localStorage.getItem("pbsess")'))
        self.verify_status = 200
        self.page.locator('#ac_code').fill('123456')
        self.page.locator('#ac_confirm').click()
        expect(self.page.locator('#acct')).to_contain_text(self.nickname)
        stored = self.page.evaluate('JSON.parse(localStorage.getItem("pbsess"))')
        self.assertNotIn('token', stored)
        self.assertNotIn('email', stored)
        self.assertNotIn('123456', json.dumps(stored))

    def test_otp_remains_bound_to_email_that_received_the_message(self):
        self.request_email()
        self.page.locator('#ac_e').evaluate('(el)=>el.value="someone-else@example.com"')
        self.page.locator('#ac_code').fill('123456')
        self.page.locator('#ac_confirm').click()
        expect(self.page.locator('#acct')).to_contain_text(self.nickname)
        verify = next(r for r in self.requests if r['path'] == '/auth/v1/verify')
        self.assertEqual(verify['body'], {'email': 'parent@example.com', 'token': '123456', 'type': 'email'})

    def test_validation_resend_and_change_email(self):
        self.page.locator('#acct').click()
        self.page.locator('#ac_e').fill('invalid')
        self.page.locator('#ac_ok').click()
        self.assertFalse(any(r['path'] == '/auth/v1/otp' for r in self.requests))
        self.page.locator('#ac_e').fill('parent@example.com')
        self.page.locator('#ac_ok').click()
        expect(self.page.locator('#ac_wait')).to_be_visible()
        self.page.locator('#ac_code').fill('abc')
        self.page.locator('#ac_confirm').click()
        self.assertFalse(any(r['path'] == '/auth/v1/verify' for r in self.requests))
        self.page.locator('#ac_change').click()
        expect(self.page.locator('#ac_request')).to_be_visible()
        self.page.locator('#ac_e').fill('new@example.com')
        self.page.locator('#ac_ok').click()
        expect(self.page.locator('#ac_target')).to_have_text('new@example.com')
        self.page.evaluate('resendAt=0;updateResendButton()')
        self.page.locator('#ac_resend').click()
        expect(self.page.locator('#ac_resend')).to_be_disabled()
        sent = [r for r in self.requests if r['path'] == '/auth/v1/otp']
        self.assertEqual(sent[-1]['body']['email'], 'new@example.com')

    def test_email_send_error_has_no_false_success(self):
        self.send_status = 429
        self.page.locator('#acct').click()
        self.page.locator('#ac_e').fill('parent@example.com')
        self.page.locator('#ac_ok').click()
        expect(self.page.locator('#ac_error')).to_contain_text('寄送太頻繁')
        expect(self.page.locator('#ac_wait')).not_to_be_visible()
        expect(self.page.locator('#ac_ok')).to_be_enabled()

    def test_code_input_hidden_until_email_template_is_ready(self):
        self.code_enabled = False
        self.page.reload(wait_until='networkidle')
        self.request_email()
        expect(self.page.locator('#ac_verify')).not_to_be_visible()
        expect(self.page.locator('#ac_device_help')).to_contain_text('在手機點擊，只會登入手機')

    def test_magic_link_callback_cleans_url_and_updates_other_tab(self):
        self.page.locator('#acct').click()
        second = self.context.new_page()
        second.goto(self.base + '#access_token=test-link-access&refresh_token=test-link-refresh&expires_in=3600', wait_until='networkidle')
        expect(second.locator('#acct')).to_contain_text(self.nickname)
        expect(self.page.locator('#acct')).to_contain_text(self.nickname)
        self.assertNotIn('access_token', second.url)
        expect(self.page.locator('#ova')).not_to_be_visible()
        second.locator('#acct').click()
        second.locator('#ac_off').click()
        expect(self.page.locator('#acct')).to_have_text('登入／註冊')
        self.assertIsNone(self.page.evaluate('localStorage.getItem("pbsess")'))

    def test_other_device_does_not_receive_session(self):
        other_context = self.new_context()
        phone = other_context.new_page()
        self.open_page(phone)
        self.login_with_code(phone)
        expect(self.page.locator('#acct')).to_have_text('登入／註冊')
        self.assertIsNone(self.page.evaluate('localStorage.getItem("pbsess")'))

    def test_simultaneous_expired_requests_share_one_refresh(self):
        self.page.evaluate('''async()=>{
          sess={access_token:'expired-test',refresh_token:'expired-refresh',expires_at:1,uid:'test-parent'};
          saveSess();await Promise.all(Array.from({length:9},()=>api('/rest/v1/books')));
        }''')
        renewals = [r for r in self.requests if r['path'] == '/auth/v1/token']
        self.assertEqual(len(renewals), 1)
        self.assertEqual(self.page.evaluate('sess.access_token'), 'test-renewed')

    def test_cross_tab_logout_during_user_lookup_stays_logged_out(self):
        self.hold_user = True
        second = self.context.new_page()
        second.goto(self.base + '#access_token=test-link&refresh_token=test-refresh&expires_in=3600', wait_until='domcontentloaded')
        self.page.wait_for_function('sessionSyncPromise!==null')
        second.evaluate('authVersion++;sess=null;me=null;localStorage.removeItem("pbsess")')
        self.page.wait_for_function('sess===null')
        self.hold_user = False
        for route in self.held_users:
            route.fulfill(status=200, content_type='application/json', body=json.dumps({'id': 'test-parent', 'email': 'parent@example.com'}), headers={'Access-Control-Allow-Origin': '*'})
        self.page.wait_for_function('sessionSyncPromise===null')
        expect(self.page.locator('#acct')).to_have_text('登入／註冊')
        self.assertIsNone(self.page.evaluate('localStorage.getItem("pbsess")'))


if __name__ == '__main__':
    unittest.main()
