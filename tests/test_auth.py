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
        self.books = []
        self.book_status = 201
        self.age_votes = []
        self.stage_votes = []
        self.votes = {}
        self.favorites = set()
        self.favorite_status = 201
        self.stale_favorites = False
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
        elif path == '/rest/v1/books':
            if req.method == 'POST':
                status = self.book_status
                if status >= 400:
                    data = {'message': 'test failed submission'}
                else:
                    book = dict(body, id='submitted-%d' % len(self.books), submitted_by='test-parent')
                    self.books.append(book)
                    data = [book]
            else:
                data = self.books
        elif path == '/rest/v1/book_age_votes':
            data = self.age_votes
        elif path == '/rest/v1/book_stage_votes':
            data = self.stage_votes
        elif path == '/rest/v1/book_votes':
            if req.method == 'POST':
                self.votes[body['book_id']] = body
                for stage in body['stages']:
                    vote = next((v for v in self.stage_votes if v['book_id'] == body['book_id'] and v['stage'] == stage), None)
                    if vote:
                        vote['votes'] += 1
                    else:
                        self.stage_votes.append({'book_id': body['book_id'], 'stage': stage, 'votes': 1})
            else:
                data = [{'book_id': bid} for bid in self.votes]
        elif path == '/rest/v1/book_voter_counts':
            data = [{'book_id': b['id'], 'voters': 1} for b in self.books]
        elif path == '/rest/v1/favorites':
            if req.method == 'POST':
                if self.favorite_status >= 400:
                    status, data = self.favorite_status, {'message': 'test failed save'}
                elif body['book_id'] in self.favorites:
                    status, data = 409, {'code': '23505', 'message': 'test duplicate'}
                else:
                    self.favorites.add(body['book_id'])
            elif req.method == 'DELETE':
                from urllib.parse import urlsplit, parse_qs
                bid = parse_qs(urlsplit(req.url).query)['book_id'][0].removeprefix('eq.')
                self.favorites.discard(bid)
            else:
                data = [] if self.stale_favorites else [{'book_id': bid} for bid in self.favorites]
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


    def load_flow_books(self):
        def book(bid, title, themes=None):
            return {'id': bid, 'title': title, 'author': '測試作者', 'lang': '中文',
                    'status': 'published', 'submitted_by': 'other-parent',
                    'themes': themes or [], 'styles': [], 'photos': [], 'review': '測試共讀心得'}
        self.books = [book('emotion-vote', '情緒書（投票）'),
                      book('emotion-theme', '情緒書（主題）', ['情緒']),
                      book('sleep-vote', '睡前書（投票）'),
                      book('sleep-theme', '睡前書（主題）', ['睡前']),
                      book('numbers-vote', '數字書')]
        self.stage_votes = [{'book_id': 'emotion-vote', 'stage': '情緒管理', 'votes': 1},
                            {'book_id': 'sleep-vote', 'stage': '睡前共讀', 'votes': 1},
                            {'book_id': 'numbers-vote', 'stage': '數字學習', 'votes': 1}]
        self.page.reload(wait_until='networkidle')

    def finish_open_login(self):
        self.page.locator('#ac_e').fill('parent@example.com')
        self.page.locator('#ac_ok').click()
        expect(self.page.locator('#ac_code')).to_be_visible()
        self.page.locator('#ac_code').fill('123456')
        self.page.locator('#ac_confirm').click()
        self.page.wait_for_function('!loginBusy')
        expect(self.page.locator('#acct')).to_contain_text(self.nickname)

    def favorite_writes(self):
        return [r for r in self.requests if r['path'] == '/rest/v1/favorites' and r['method'] != 'GET']

    def open_book_for_favorite(self):
        self.load_flow_books()
        self.page.get_by_role('button', name='情緒書（投票）', exact=True).click()
        self.page.get_by_role('button', name='加入收藏', exact=True).click()
        expect(self.page.locator('#ova')).to_be_visible()

    def test_emotion_and_sleep_scenarios_match_manual_filters(self):
        self.load_flow_books()
        for label, stage, titles in [
            ('孩子難過或生氣', '情緒管理', ['情緒書（投票）', '情緒書（主題）']),
            ('睡前放鬆', '睡前共讀', ['睡前書（投票）', '睡前書（主題）'])]:
            with self.subTest(stage=stage):
                button = self.page.get_by_role('button', name=label, exact=True)
                button.click()
                expect(self.page.locator('.book-link')).to_have_text(titles)
                self.page.get_by_role('button', name='移除條件：'+stage, exact=True).click()
                expect(self.page.locator('.card')).to_have_count(5)
                if self.page.locator('#ftog').get_attribute('aria-expanded') == 'false':
                    self.page.locator('#ftog').click()
                if self.page.locator('#stages').get_by_role('button', name=stage, exact=True).count() == 0:
                    self.page.locator('#stages .mo').click()
                self.page.locator('#stages').get_by_role('button', name=stage, exact=True).click()
                expect(self.page.locator('.book-link')).to_have_text(titles)
                expect(button).to_have_attribute('aria-pressed', 'true')
                self.page.locator('#apply-filters').click()
                button.click()
                expect(self.page.locator('.card')).to_have_count(5)

    def test_other_scenarios_still_work(self):
        self.load_flow_books()
        self.open_situation_group('好奇與探索')
        self.page.locator('#situations').get_by_role('button', name='數字學習', exact=True).click()
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.book-link')).to_have_text(['數字書'])

    def open_situation_group(self, name, posting=False):
        root = self.page.locator('#form-situations' if posting else '#situations')
        if not posting and self.page.locator('#ftog').get_attribute('aria-expanded') == 'false':
            self.page.locator('#more-situations').click()
        group = root.locator('details').filter(has=self.page.locator('summary', has_text=name))
        if group.get_attribute('open') is None:
            group.locator('summary').click()
        return group

    def load_situation_books(self):
        def book(bid, title, themes, **extra):
            return dict({'id': bid, 'title': title, 'author': '測試作者', 'lang': '中文',
                         'status': 'published', 'submitted_by': 'other-parent',
                         'themes': themes, 'styles': [], 'photos': [], 'review': '共讀心得'}, **extra)
        self.books = [
            book('apology', '道歉的故事', ['道歉']),
            book('manners', '禮貌的故事', ['禮貌']),
            book('gratitude', '感激的故事', ['感激']),
            book('sibling', '手足的故事', ['手足關係']),
            book('both', '手足一起學道歉', ['學說對不起', '手足相處']),
            book('unrelated', '其他主題的故事', ['太空'], review='這本沒有談到道歉'),
            book('unpublished', '審核中的道歉故事', ['道歉'], status='pending'),
        ]
        self.age_votes = [{'book_id': 'both', 'age': 4, 'votes': 1},
                          {'book_id': 'apology', 'age': 5, 'votes': 1}]
        self.page.reload(wait_until='networkidle')

    def test_all_situations_are_available_with_empty_catalog_and_counts(self):
        self.page.locator('#more-situations').click()
        expect(self.page.locator('#ftog')).to_have_attribute('aria-expanded', 'true')
        expect(self.page.locator('#situations details')).to_have_count(6)
        expect(self.page.locator('#situations [data-life]')).to_have_count(32)
        for name in ['學說對不起', '有禮貌', '感恩與感激']:
            button = self.page.locator('#situations').get_by_role('button', name=name, exact=True)
            expect(button).to_be_enabled()
            expect(button.locator('.situation-count')).to_have_text('0 本公開繪本')
        self.page.locator('#situations').get_by_role('button', name='學說對不起', exact=True).click()
        expect(self.page.locator('#count')).to_have_text('共 0 本繪本')
        expect(self.page.locator('#active-filters')).to_contain_text('學說對不起')
        self.page.locator('#apply-filters').click()
        self.page.get_by_role('button', name='清除條件，再找找', exact=True).click()
        expect(self.page.locator('#situations [aria-pressed=true]')).to_have_count(0)

    def test_parent_examples_match_existing_aliases_without_guessing_from_review(self):
        self.load_situation_books()
        expected = [('學說對不起', ['道歉的故事', '手足一起學道歉']),
                    ('有禮貌', ['禮貌的故事']),
                    ('手足相處', ['手足的故事', '手足一起學道歉']),
                    ('感恩與感激', ['感激的故事'])]
        for label, titles in expected:
            with self.subTest(label=label):
                shortcut = self.page.locator('#scen').get_by_role('button', name=label, exact=True)
                shortcut.click()
                expect(self.page.locator('.book-link')).to_have_text(titles)
                self.open_situation_group('人際與家庭' if label == '手足相處' else '友善與品格')
                button = self.page.locator('#situations').get_by_role('button', name=label, exact=True)
                expect(button).to_have_attribute('aria-pressed', 'true')
                expect(button.locator('.situation-count')).to_have_text(str(len(titles))+' 本公開繪本')
                button.click()
                expect(self.page.locator('.card')).to_have_count(6)
                button.click()
                expect(self.page.locator('.book-link')).to_have_text(titles)
                expect(shortcut).to_have_attribute('aria-pressed', 'true')
                self.page.locator('#apply-filters').click()
                shortcut.click()

    def test_combined_situations_age_and_language_can_be_removed_individually(self):
        self.load_situation_books()
        self.page.locator('#langs').get_by_role('button', name='中文', exact=True).click()
        self.page.locator('#scen').get_by_role('button', name='學說對不起', exact=True).click()
        group = self.open_situation_group('人際與家庭')
        group.get_by_role('button', name='手足相處', exact=True).click()
        expect(self.page.locator('.book-link')).to_have_text(['手足一起學道歉'])
        expect(group.locator('.situation-selection')).to_have_text('已選 1')
        self.page.locator('#age').fill('4')
        expect(self.page.locator('.book-link')).to_have_text(['手足一起學道歉'])
        expect(self.page.locator('#active-filters button')).to_have_count(4)
        self.page.locator('#apply-filters').click()
        self.page.get_by_role('button', name='移除條件：學說對不起', exact=True).click()
        self.page.get_by_role('button', name='移除條件：4 歲', exact=True).click()
        expect(self.page.locator('.book-link')).to_have_text(['手足的故事', '手足一起學道歉'])
        self.page.locator('#ftog').click()
        self.page.locator('#reset').click()
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.card')).to_have_count(6)
        expect(self.page.locator('#situations [aria-pressed=true]')).to_have_count(0)
        expect(self.page.locator('#active-filters button')).to_have_count(0)

    def test_keyword_search_understands_situation_aliases_and_custom_themes_remain(self):
        self.load_situation_books()
        for query in ['感恩', '感激', '感謝']:
            self.page.locator('#q').fill(query)
            expect(self.page.locator('.book-link')).to_have_text(['感激的故事'])
        self.page.locator('#clear-search').click()
        self.page.locator('#more-situations').click()
        expect(self.page.locator('#themes')).not_to_contain_text('道歉')
        self.page.locator('#themes').get_by_role('button', name='太空', exact=True).click()
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.book-link')).to_have_text(['其他主題的故事'])

    def load_search_books(self):
        def book(bid, title, **extra):
            return dict({'id': bid, 'title': title, 'author': '測試作者', 'lang': '中文',
                         'status': 'published', 'submitted_by': 'other-parent',
                         'themes': [], 'styles': [], 'photos': [], 'review': '共讀心得'}, **extra)
        self.books = [
            book('tag', '點子小宇宙', themes=['想像與創作'], styles=['水彩風格']),
            book('legacy', '小小造夢師', themes=['創造力'], styles=['拼貼']),
            book('review', '會變身的雨滴', review='故事有許多創意。', styles=['水彩']),
            book('reaction', '紙箱變成飛船', kid_reaction='孩子發揮想像力，接著編故事。', styles=['漫畫']),
            book('literal', '腦洞大開的動物', styles=['手繪']),
            book('english', 'A Sky of Ideas', author='Chris Example', lang='英文', themes=['創意'], styles=['水彩']),
            book('sleep', '安靜的晚安', themes=['睡前'], styles=['溫柔']),
            book('boundary', '天馬', author='行空'),
            book('pending', '未公開的創意', themes=['想像與創作'], status='pending'),
        ]
        self.age_votes = [{'book_id': 'tag', 'age': 4, 'votes': 1}]
        self.stage_votes = [{'book_id': 'tag', 'stage': '幼幼班', 'votes': 1}]
        self.page.reload(wait_until='networkidle')

    def test_intent_keywords_find_tags_old_aliases_reviews_and_child_reactions_without_filters(self):
        self.load_search_books()
        titles = [b['title'] for b in self.books[:6]]
        requests_before = len(self.requests)
        for query in ['天馬行空', '腦洞大開', '有創意', '創造力', '想像力']:
            with self.subTest(query=query):
                self.page.locator('#q').fill(query)
                expect(self.page.locator('.book-link')).to_have_text(titles)
                expect(self.page.locator('#search-context')).to_have_text('也會找：想像與創作')
                expect(self.page.locator('#active-filters')).to_be_empty()
                expect(self.page.locator('#ovfilters')).not_to_be_visible()
        self.assertEqual(len(self.requests), requests_before)

    def test_multiple_keyword_terms_intersect_and_still_combine_with_language_and_age(self):
        self.load_search_books()
        titles = ['點子小宇宙', '會變身的雨滴', 'A Sky of Ideas']
        for query in ['有創意 水彩', '有創意，水彩', '有創意、 水彩', '有創意\u3000水彩']:
            with self.subTest(query=query):
                self.page.locator('#q').fill(query)
                expect(self.page.locator('.book-link')).to_have_text(titles)
        self.page.locator('#langs').get_by_role('button', name='中文', exact=True).click()
        expect(self.page.locator('.book-link')).to_have_text(titles[:2])
        self.page.locator('#ftog').click()
        self.page.locator('#age').fill('4')
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.book-link')).to_have_text(['點子小宇宙'])
        self.page.locator('#all-books').click()
        self.page.locator('#q').fill('腦洞大開、有創意、天馬行空')
        expect(self.page.locator('.book-link')).to_have_text([b['title'] for b in self.books[:6]])
        expect(self.page.locator('#search-context')).to_have_text('也會找：想像與創作')
        self.page.locator('#q').fill('有創意 水彩 Chris')
        expect(self.page.locator('.book-link')).to_have_text(['A Sky of Ideas'])

    def test_search_keeps_literal_titles_author_unicode_and_stage_queries_and_does_not_join_fields(self):
        self.load_search_books()
        for query in ['ｃｈｒｉｓ', 'CHRIS', 'a sky', 'A Sky of Ideas']:
            with self.subTest(query=query):
                self.page.locator('#q').fill(query)
                expect(self.page.locator('.book-link')).to_have_text(['A Sky of Ideas'])
        self.page.locator('#q').fill('幼幼班')
        expect(self.page.locator('.book-link')).to_have_text(['點子小宇宙'])
        self.page.locator('#q').fill('天馬行空')
        expect(self.page.locator('.book-link')).not_to_contain_text(['天馬'])
        self.page.locator('#q').fill('不存在的火箭')
        expect(self.page.locator('.card')).to_have_count(0)
        expect(self.page.locator('#search-context')).not_to_be_visible()
        self.page.get_by_role('button', name='清除條件，再找找', exact=True).click()
        expect(self.page.locator('.card')).to_have_count(8)
        self.page.locator('#q').fill('有創意 不存在的火箭')
        expect(self.page.locator('.card')).to_have_count(0)

    def test_creative_intent_aliases_round_trip_through_submission_and_search(self):
        self.login_with_code()
        self.page.locator('#addb').click()
        self.page.locator('#f_t').fill('月亮也有新點子')
        self.page.locator('#f_th').fill('天馬行空、有創意、腦洞大開、創造力')
        self.page.locator('#f_ok').click()
        expect(self.page.locator('#ovf')).not_to_be_visible()
        payload = [r['body'] for r in self.requests if r['path'] == '/rest/v1/books' and r['method'] == 'POST'][-1]
        self.assertEqual(payload['themes'], ['想像與創作'])
        self.books[0]['status'] = 'published'
        self.page.reload(wait_until='networkidle')
        self.page.locator('#q').fill('腦洞大開')
        expect(self.page.locator('.book-link')).to_have_text(['月亮也有新點子'])

    def test_keyword_search_enter_ignores_ime_confirmation_and_clear_restores_overview(self):
        self.load_search_books()
        query = self.page.locator('#q')
        query.fill('有創意')
        query.dispatch_event('keydown', {'key': 'Enter', 'isComposing': True, 'bubbles': True})
        expect(query).to_be_focused()
        query.press('Enter')
        expect(self.page.locator('#results-bar')).to_be_focused()
        expect(self.page.locator('#ovfilters')).not_to_be_visible()
        self.page.locator('#clear-search').click()
        expect(query).to_be_focused()
        expect(query).to_have_value('')
        expect(self.page.locator('#search-context')).not_to_be_visible()
        expect(self.page.locator('.card')).to_have_count(8)
        for width in [320, 390, 1440]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 844})
                query.fill('腦洞大開 有創意 水彩')
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))

    def test_selected_situations_round_trip_through_submission_and_reset(self):
        self.login_with_code()
        self.page.locator('#addb').click()
        self.page.locator('#f_t').fill('手足學道歉與感謝')
        self.page.locator('#fa').get_by_role('button', name='5 歲', exact=True).click()
        for name in ['學說對不起', '感恩與感激']:
            self.page.locator('#form-situations').get_by_role('button', name=name, exact=True).click()
        self.open_situation_group('人際與家庭', posting=True).get_by_role('button', name='手足相處', exact=True).click()
        self.open_situation_group('情緒與自我', posting=True).get_by_role('button', name='孩子難過或生氣', exact=True).click()
        self.page.locator('#f_th').fill('道歉、感謝, 太空,太空')
        self.page.locator('#ovf .optional-fields summary').click()
        self.page.locator('#fs').get_by_role('button', name='情緒管理', exact=True).click()
        self.page.locator('#f_ok').click()
        expect(self.page.locator('#ovf')).not_to_be_visible()
        payload = next(r['body'] for r in self.requests if r['path'] == '/rest/v1/books' and r['method'] == 'POST')
        self.assertEqual(payload['themes'], ['學說對不起', '感恩與感激', '手足相處', '情緒管理', '太空'])
        self.assertEqual(payload['suggested_stages'], ['情緒管理'])
        self.assertEqual(payload['suggested_ages'], [5])
        self.assertEqual(payload['status'], 'pending')
        self.page.locator('#addb').click()
        expect(self.page.locator('#form-situations [aria-pressed=true]')).to_have_count(0)
        expect(self.page.locator('#fs [aria-pressed=true]')).to_have_count(0)
        expect(self.page.locator('#fa [aria-pressed=true]')).to_have_count(0)
        expect(self.page.locator('#f_th')).to_have_value('')
        self.page.locator('#ovf .x').click()
        # Simulate moderation on the isolated backend; no production data is written.
        self.books[0]['status'] = 'published'
        self.page.reload(wait_until='networkidle')
        for name in ['學說對不起', '有禮貌', '手足相處', '感恩與感激']:
            button = self.page.locator('#scen').get_by_role('button', name=name, exact=True)
            button.click()
            expect(self.page.locator('.book-link')).to_have_text([] if name == '有禮貌' else ['手足學道歉與感謝'])
            button.click()

    def test_failed_submission_preserves_situations_for_retry(self):
        self.login_with_code()
        self.page.locator('#addb').click()
        self.page.locator('#f_t').fill('保留投稿內容')
        button = self.page.locator('#form-situations').get_by_role('button', name='學說對不起', exact=True)
        button.click()
        self.book_status = 503
        self.page.locator('#f_ok').click()
        expect(self.page.locator('#toast')).to_contain_text('test failed submission')
        expect(self.page.locator('#f_ok')).to_be_enabled()
        expect(button).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#f_t')).to_have_value('保留投稿內容')
        self.book_status = 201
        self.page.locator('#f_ok').click()
        expect(self.page.locator('#ovf')).not_to_be_visible()
        writes = [r for r in self.requests if r['path'] == '/rest/v1/books' and r['method'] == 'POST']
        self.assertEqual([r['body']['themes'] for r in writes], [['學說對不起'], ['學說對不起']])

    def test_situation_groups_are_keyboard_accessible_and_fit_mobile_and_desktop(self):
        self.load_situation_books()
        self.page.locator('#more-situations').click()
        expect(self.page.locator('#situations summary').first).to_be_focused()
        self.page.keyboard.press('Tab')
        expect(self.page.locator('#situations [data-life="學說對不起"]')).to_be_focused()
        self.page.keyboard.press('Enter')
        expect(self.page.locator('#situations [data-life="學說對不起"]')).to_have_attribute('aria-pressed', 'true')
        for width in [320, 390, 1280]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 844})
                self.page.locator('#situations details').evaluate_all('(nodes)=>nodes.forEach(n=>n.open=true)')
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                self.assertTrue(self.page.locator('#situations button').evaluate_all(
                    '(nodes)=>nodes.every(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.height>=44})'))

    def load_facet_books(self):
        self.load_flow_books()
        for book, styles in zip(self.books, [['水彩風格'], ['溫柔'], ['拼貼'], ['插畫風格'], []]):
            book['styles'] = styles
        self.stage_votes.append({'book_id': 'emotion-vote', 'stage': '幼幼班', 'votes': 1})
        self.age_votes = [{'book_id': 'emotion-vote', 'age': 2, 'votes': 1}]
        self.page.reload(wait_until='networkidle')

    def test_filter_selection_keeps_page_compact_and_result_action_visible(self):
        self.load_situation_books()
        compact_height = self.page.locator('.filters').bounding_box()['height']
        self.page.locator('#more-situations').click()
        expect(self.page.locator('#ovfilters')).to_be_visible()
        expect(self.page.locator('#main')).to_have_attribute('inert', '')
        page_scroll = self.page.evaluate('scrollY')
        self.open_situation_group('人際與家庭').get_by_role('button', name='手足相處', exact=True).click()
        self.page.locator('#situations').get_by_role('button', name='學說對不起', exact=True).click()
        expect(self.page.locator('#apply-filters')).to_have_text('查看 1 本繪本')
        self.assertLessEqual(self.page.locator('.filters').bounding_box()['height'], compact_height + 64)
        token_height = self.page.locator('#active-filters').bounding_box()['height']
        self.assertLessEqual(token_height, 50)
        self.assertEqual(self.page.evaluate('scrollY'), page_scroll)
        self.page.locator('#fbody').evaluate('(el)=>el.scrollTop=el.scrollHeight')
        bounds = self.page.locator('#apply-filters').bounding_box()
        self.assertGreaterEqual(bounds['y'], 0)
        self.assertLessEqual(bounds['y'] + bounds['height'], 844)
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('#ovfilters')).not_to_be_visible()
        expect(self.page.locator('#ftog')).to_have_attribute('aria-expanded', 'false')
        expect(self.page.locator('#results-bar')).to_be_focused()
        expect(self.page.locator('.book-link')).to_have_text(['手足一起學道歉'])
        self.page.locator('#all-books').click()
        expect(self.page.locator('.card')).to_have_count(6)
        expect(self.page.locator('#active-filters')).to_be_empty()

    def test_all_books_resets_every_filter_and_shelf_without_reload(self):
        self.load_facet_books()
        self.login_with_code()
        self.page.locator('#langs').get_by_role('button', name='中文', exact=True).click()
        self.page.locator('#q').fill('情緒')
        self.page.locator('#ftog').click()
        self.page.locator('#age').fill('2')
        self.page.locator('#stages').get_by_role('button', name='幼幼班', exact=True).click()
        self.page.locator('#styles').get_by_role('button', name='水彩', exact=True).click()
        self.page.locator('#nowarn').check()
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.book-link')).to_have_text(['情緒書（投票）'])
        self.page.locator('.tab[data-t=fav]').click()
        expect(self.page.locator('.card')).to_have_count(0)
        requests_before = len(self.requests)
        self.page.locator('#all-books').click()
        expect(self.page.locator('.card')).to_have_count(5)
        expect(self.page.locator('#q')).to_have_value('')
        expect(self.page.locator('#active-filters')).to_be_empty()
        expect(self.page.locator('.tab[data-t=all]')).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#acct')).to_contain_text(self.nickname)
        self.assertEqual(len(self.requests), requests_before)
        self.page.locator('#ftog').click()
        expect(self.page.locator('#age')).to_have_value('-1')
        expect(self.page.locator('#nowarn')).not_to_be_checked()
        self.page.locator('#styles').get_by_role('button', name='水彩', exact=True).click()
        self.page.locator('#filter-all-books').click()
        expect(self.page.locator('#ovfilters')).not_to_be_visible()
        expect(self.page.locator('.card')).to_have_count(5)

    def test_explore_links_and_home_logo_return_to_unfiltered_overview(self):
        self.load_flow_books()
        self.page.set_viewport_size({'width': 1280, 'height': 900})
        for entry in ['.brand', '.header-nav [data-explore]', '.hero [data-explore]', '.tab[data-t=all]']:
            with self.subTest(entry=entry):
                self.page.locator('#scen').get_by_role('button', name='孩子難過或生氣', exact=True).click()
                expect(self.page.locator('.card')).to_have_count(2)
                self.page.locator(entry).click()
                expect(self.page.locator('.card')).to_have_count(5)
                expect(self.page.locator('#active-filters')).to_be_empty()

    def test_filter_escape_and_close_restore_focus_and_mobile_actions_stay_visible(self):
        for method in ['escape', 'button', 'backdrop']:
            with self.subTest(method=method):
                self.page.locator('#ftog').click()
                if method == 'escape':
                    self.page.keyboard.press('Escape')
                elif method == 'button':
                    self.page.locator('#ovfilters .filter-close').click()
                else:
                    self.page.locator('#ovfilters').click(position={'x': 2, 'y': 2})
                expect(self.page.locator('#ftog')).to_be_focused()
                expect(self.page.locator('#ftog')).to_have_attribute('aria-expanded', 'false')
        self.page.locator('#ftog').click()
        for width, height in [(320, 568), (390, 844), (844, 390), (1280, 900)]:
            with self.subTest(width=width, height=height):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.locator('#situations details').evaluate_all('(nodes)=>nodes.forEach(n=>n.open=true)')
                self.page.locator('#fbody').evaluate('(el)=>el.scrollTop=el.scrollHeight')
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                for action in ['#filter-all-books', '#apply-filters']:
                    rect = self.page.locator(action).bounding_box()
                    self.assertGreaterEqual(rect['y'], 0)
                    self.assertLessEqual(rect['y']+rect['height'], height)
                self.page.locator('#apply-filters').focus()
                self.page.keyboard.press('Tab')
                expect(self.page.locator('#ovfilters .filter-close')).to_be_focused()

    def test_styles_show_preset_choices_match_aliases_and_preserve_custom_styles(self):
        self.page.locator('#ftog').click()
        expect(self.page.locator('#styles button')).to_have_count(12)
        for style in ['水彩', '手繪', '拼貼／剪紙', '攝影', '漫畫', '黑白線條', '溫柔療癒', '幽默趣味']:
            expect(self.page.locator('#styles').get_by_role('button', name=style, exact=True)).to_be_visible()
        self.page.locator('#apply-filters').click()
        self.load_facet_books()
        for style, title in [('水彩', '情緒書（投票）'), ('溫柔療癒', '情緒書（主題）'),
                             ('拼貼／剪紙', '睡前書（投票）'), ('插畫風格', '睡前書（主題）')]:
            with self.subTest(style=style):
                self.page.locator('#ftog').click()
                self.page.locator('#styles').get_by_role('button', name=style, exact=True).click()
                self.page.locator('#apply-filters').click()
                expect(self.page.locator('.book-link')).to_have_text([title])
                self.page.locator('#all-books').click()
        self.page.locator('#ftog').click()
        self.page.locator('#styles').get_by_role('button', name='攝影', exact=True).click()
        expect(self.page.locator('#apply-filters')).to_have_text('查看 0 本繪本')
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.card')).to_have_count(0)
        self.page.locator('#all-books').click()
        expect(self.page.locator('.card')).to_have_count(5)

    def test_young_class_and_styles_submission_deduplicate_reset_and_filter_after_publication(self):
        self.login_with_code()
        self.page.locator('#addb').click()
        self.page.locator('#f_t').fill('幼幼班的水彩故事')
        self.page.locator('#ovf .optional-fields summary').click()
        self.page.locator('#fs').get_by_role('button', name='幼幼班', exact=True).click()
        self.page.locator('#f_styles').get_by_role('button', name='水彩', exact=True).click()
        self.page.locator('#f_styles').get_by_role('button', name='溫柔療癒', exact=True).click()
        self.page.locator('#f_st').fill('水彩風格、溫柔,蠟筆,蠟筆')
        self.book_status = 503
        self.page.locator('#f_ok').click()
        expect(self.page.locator('#toast')).to_contain_text('test failed submission')
        expect(self.page.locator('#f_ok')).to_be_enabled()
        expect(self.page.locator('#f_styles [aria-pressed=true]')).to_have_count(2)
        self.book_status = 201
        self.page.locator('#f_ok').click()
        expect(self.page.locator('#ovf')).not_to_be_visible()
        payload = [r['body'] for r in self.requests if r['path'] == '/rest/v1/books' and r['method'] == 'POST'][-1]
        self.assertEqual(payload['suggested_stages'], ['幼幼班'])
        self.assertEqual(payload['styles'], ['水彩', '溫柔療癒', '蠟筆'])
        self.page.locator('#addb').click()
        expect(self.page.locator('#f_styles [aria-pressed=true]')).to_have_count(0)
        expect(self.page.locator('#fs [aria-pressed=true]')).to_have_count(0)
        expect(self.page.locator('#f_st')).to_have_value('')
        self.page.locator('#ovf .x').click()
        self.books[0]['status'] = 'published'
        self.stage_votes = [{'book_id': self.books[0]['id'], 'stage': '幼幼班', 'votes': 1}]
        self.page.reload(wait_until='networkidle')
        self.page.locator('#ftog').click()
        self.page.locator('#stages').get_by_role('button', name='幼幼班', exact=True).click()
        self.page.locator('#styles').get_by_role('button', name='水彩', exact=True).click()
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.book-link')).to_have_text(['幼幼班的水彩故事'])

    def test_young_class_can_be_voted_and_loaded_on_next_visit(self):
        self.load_flow_books()
        self.login_with_code()
        self.page.locator('.book-link').first.click()
        self.page.locator('#vs').get_by_role('button', name='幼幼班', exact=True).click()
        self.page.get_by_role('button', name='送出我的建議', exact=True).click()
        expect(self.page.locator('#md')).to_contain_text('你已經送出過建議')
        vote = next(r['body'] for r in self.requests if r['path'] == '/rest/v1/book_votes' and r['method'] == 'POST')
        self.assertEqual(vote['stages'], ['幼幼班'])
        self.page.locator('#ov .x').click()
        self.page.reload(wait_until='networkidle')
        self.page.locator('#ftog').click()
        self.page.locator('#stages').get_by_role('button', name='幼幼班', exact=True).click()
        self.page.locator('#apply-filters').click()
        expect(self.page.locator('.book-link')).to_have_text(['情緒書（投票）'])

    def test_recommendation_resumes_after_code_login(self):
        self.page.locator('#addb').click()
        saved = self.page.evaluate('JSON.parse(sessionStorage.getItem("pbintent"))')
        self.assertEqual(saved['kind'], 'recommend')
        self.assertNotIn('email', saved)
        self.assertNotIn('access_token', saved)
        self.finish_open_login()
        expect(self.page.locator('#ovf')).to_be_visible()
        expect(self.page.locator('#ova')).not_to_be_visible()
        self.assertIsNone(self.page.evaluate('sessionStorage.getItem("pbintent")'))
        self.page.locator('#f_t').fill('登入後接著填寫的書名')
        expect(self.page.locator('#f_t')).to_have_value('登入後接著填寫的書名')

    def test_recommendation_survives_reload_and_link_callback(self):
        self.page.locator('#addb').click()
        self.page.reload(wait_until='networkidle')
        self.page.goto(self.base+'?return=link#access_token=test-link&refresh_token=test-refresh&expires_in=3600', wait_until='networkidle')
        expect(self.page.locator('#ovf')).to_be_visible()
        self.assertNotIn('access_token', self.page.url)
        self.assertIsNone(self.page.evaluate('sessionStorage.getItem("pbintent")'))

    def test_login_in_another_tab_resumes_only_original_tab(self):
        self.page.locator('#addb').click()
        second = self.context.new_page()
        second.goto(self.base+'#access_token=test-link&refresh_token=test-refresh&expires_in=3600', wait_until='networkidle')
        expect(self.page.locator('#ovf')).to_be_visible()
        expect(second.locator('#ovf')).not_to_be_visible()

    def test_cancel_login_clears_intent_for_button_escape_and_backdrop(self):
        for method in ['button', 'escape', 'backdrop']:
            with self.subTest(method=method):
                self.page.locator('#addb').click()
                if method == 'button':
                    self.page.locator('#ova .x').click()
                elif method == 'escape':
                    self.page.keyboard.press('Escape')
                else:
                    self.page.locator('#ova').click(position={'x': 3, 'y': 3})
                expect(self.page.locator('#ova')).not_to_be_visible()
                self.assertIsNone(self.page.evaluate('sessionStorage.getItem("pbintent")'))
        self.login_with_code()
        expect(self.page.locator('#ovf')).not_to_be_visible()
        self.assertEqual(self.favorite_writes(), [])

    def test_failed_verification_preserves_intent_until_success(self):
        self.page.locator('#addb').click()
        self.verify_status = 403
        self.page.locator('#ac_e').fill('parent@example.com')
        self.page.locator('#ac_ok').click()
        self.page.locator('#ac_code').fill('000000')
        self.page.locator('#ac_confirm').click()
        expect(self.page.locator('#ac_error')).to_contain_text('驗證碼錯誤')
        expect(self.page.locator('#ovf')).not_to_be_visible()
        self.assertIsNotNone(self.page.evaluate('sessionStorage.getItem("pbintent")'))
        self.verify_status = 200
        self.page.locator('#ac_code').fill('123456')
        self.page.locator('#ac_confirm').click()
        expect(self.page.locator('#ovf')).to_be_visible()

    def test_detail_favorite_resumes_once_and_returns_to_same_book(self):
        self.open_book_for_favorite()
        self.finish_open_login()
        expect(self.page.locator('#book-title')).to_have_text('情緒書（投票）')
        expect(self.page.get_by_role('button', name='已收藏', exact=True)).to_be_visible()
        expect(self.page.locator('#fc')).to_have_text('1')
        self.assertEqual(self.favorites, {'emotion-vote'})
        self.assertEqual(len(self.favorite_writes()), 1)
        self.page.reload(wait_until='networkidle')
        expect(self.page.locator('#fc')).to_have_text('1')
        self.assertEqual(len(self.favorite_writes()), 1)

    def test_list_heart_resumes_without_opening_details(self):
        self.load_flow_books()
        self.page.get_by_role('button', name='收藏：情緒書（投票）', exact=True).click()
        self.finish_open_login()
        expect(self.page.locator('#ov')).not_to_be_visible()
        expect(self.page.get_by_role('button', name='取消收藏：情緒書（投票）', exact=True)).to_have_attribute('aria-pressed','true')
        self.assertEqual(self.favorites, {'emotion-vote'})

    def test_already_saved_favorite_does_not_toggle_off_or_write_again(self):
        self.open_book_for_favorite()
        self.favorites.add('emotion-vote')
        self.finish_open_login()
        expect(self.page.get_by_role('button', name='已收藏', exact=True)).to_be_visible()
        self.assertEqual(self.favorites, {'emotion-vote'})
        self.assertEqual(self.favorite_writes(), [])

    def test_duplicate_favorite_response_counts_as_saved(self):
        self.open_book_for_favorite()
        self.favorites.add('emotion-vote')
        self.stale_favorites = True
        self.finish_open_login()
        expect(self.page.get_by_role('button', name='已收藏', exact=True)).to_be_visible()
        self.assertEqual(self.favorites, {'emotion-vote'})
        self.assertEqual(len(self.favorite_writes()), 1)

    def test_favorite_save_failure_keeps_details_and_allows_retry(self):
        self.open_book_for_favorite()
        self.favorite_status = 500
        self.finish_open_login()
        expect(self.page.locator('#toast')).to_contain_text('收藏未完成')
        expect(self.page.get_by_role('button', name='加入收藏', exact=True)).to_be_visible()
        self.assertEqual(self.favorites, set())
        self.favorite_status = 201
        self.page.get_by_role('button', name='加入收藏', exact=True).click()
        expect(self.page.get_by_role('button', name='已收藏', exact=True)).to_be_visible()

    def test_unavailable_book_is_not_saved_after_login(self):
        self.open_book_for_favorite()
        self.books = [b for b in self.books if b['id'] != 'emotion-vote']
        self.finish_open_login()
        expect(self.page.locator('#toast')).to_contain_text('無法公開瀏覽')
        self.assertEqual(self.favorite_writes(), [])
        expect(self.page.locator('#ov')).not_to_be_visible()

    def test_favorite_uses_stable_book_id_when_order_changes(self):
        self.open_book_for_favorite()
        self.books.reverse()
        self.finish_open_login()
        expect(self.page.locator('#book-title')).to_have_text('情緒書（投票）')
        self.assertEqual(self.favorites, {'emotion-vote'})

    def test_expired_intent_does_not_resume(self):
        self.page.locator('#addb').click()
        self.page.evaluate('pendingLoginAction.createdAt=1;sessionStorage.setItem("pbintent",JSON.stringify(pendingLoginAction))')
        self.finish_open_login()
        expect(self.page.locator('#ovf')).not_to_be_visible()
        self.assertIsNone(self.page.evaluate('sessionStorage.getItem("pbintent")'))

    def test_same_page_resume_works_when_intent_storage_is_unavailable(self):
        self.page.evaluate('''()=>{
          for(const method of ['getItem','setItem','removeItem']){
            const original=Storage.prototype[method];
            Storage.prototype[method]=function(key,...args){if(key==='pbintent')throw new Error('test storage unavailable');return original.call(this,key,...args)};
          }
        }''')
        self.page.locator('#addb').click()
        self.finish_open_login()
        expect(self.page.locator('#ovf')).to_be_visible()


if __name__ == '__main__':
    unittest.main()
