import asyncio
from unittest import TestCase

from tornado.options import parse_config_file

from core.mail import send_mail


class TestMail(TestCase):

    def setUp(self):
        parse_config_file('config.ini')

    def test_send(self):
        loop = asyncio.get_event_loop()

        # {
        #     "message": "Queued. Thank you.",
        #     "id": "<20111114174239.25659.5817@samples.mailgun.org>"
        # }

        result = loop.run_until_complete(send_mail('me@iscys.com', 'Hello', 'this is a test mail.'))
        self.assertIsNotNone(result, 'remote error')
        self.assertEqual(result['message'], 'Queued. Thank you.')

        # result = loop.run_until_complete(send_mail(
        #     ['me@iscys.com', 'supercys@gmail.com'],
        #     'Hello', 'this is a test mail.'))
        # self.assertEqual(result['message'], 'Queued. Thank you.')
