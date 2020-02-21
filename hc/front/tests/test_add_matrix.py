from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class AddMatrixTestCase(BaseTestCase):
    def setUp(self):
        super(AddMatrixTestCase, self).setUp()
        self.url = "/projects/%s/add_matrix/" % self.project.code

    @override_settings(MATRIX_ACCESS_TOKEN="foo")
    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Integration Settings", status_code=200)

    @override_settings(MATRIX_ACCESS_TOKEN="foo")
    @override_settings(MATRIX_HOMESERVER="fake-homeserver")
    @patch("hc.front.forms.requests.post")
    def test_it_works(self, mock_post):
        mock_post.return_value.json.return_value = {"room_id": "fake-room-id"}

        form = {"alias": "!foo:example.org"}
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "matrix")
        self.assertEqual(c.value, "fake-room-id")
        self.assertEqual(c.project, self.project)
