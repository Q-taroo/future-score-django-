from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class DesignTemplateTests(SimpleTestCase):
    def render_home(self, authenticated=False):
        return render_to_string('predictions/home.html', {
            'user': SimpleNamespace(is_authenticated=authenticated, is_admin=False),
            'predictions': [], 'categories': [], 'NOTE_TUTORIAL_URL': '',
        })

    def test_onboarding_and_accessible_landmark(self):
        html = self.render_home()
        self.assertIn('未来を考えるって、', html)
        self.assertIn('新規登録する', html)
        self.assertIn('id="main-content"', html)
        self.assertIn('楽しみ方の3ステップ', html)
        self.assertIn('href="/tutorial/"', html)

    def test_returning_user_path(self):
        html = self.render_home(True)
        self.assertIn('自分の予測を振り返る', html)
        self.assertNotIn('>新規登録する</a>', html)

    def test_no_fake_live_numbers(self):
        self.assertIn('実際の投票画面ではありません', self.render_home())
        self.assertIn('デモの予測・参加データを含みます', self.render_home())

    def test_main_navigation_has_home_and_labeled_icons(self):
        html = self.render_home()
        self.assertIn('aria-label="メインメニュー"', html)
        for label in ('ホーム', '予測一覧', 'ランキング', '使い方'):
            self.assertIn(f'<span>{label}</span>', html)
        self.assertEqual(html.count('class="nav-icon"'), 4)
