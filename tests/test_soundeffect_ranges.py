import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from web_server import Handler


class RangeTests(unittest.TestCase):
    def test_video_seek_ranges_and_head(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / 'test.mp4'
            video.write_bytes(bytes(range(256)) * 8)

            class FileHandler(Handler):
                def do_GET(self):
                    self._serve_file(video)
                do_HEAD = do_GET

            server = ThreadingHTTPServer(('127.0.0.1', 0), FileHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for method, value, expected, content in [
                    ('GET', None, 200, video.read_bytes()),
                    ('HEAD', None, 200, b''),
                    ('GET', 'bytes=300-399', 206, video.read_bytes()[300:400]),
                    ('GET', 'bytes=2000-', 206, video.read_bytes()[2000:]),
                    ('GET', 'bytes=-10', 206, video.read_bytes()[-10:]),
                    ('GET', 'bytes=2048-', 416, b''),
                    ('GET', 'bytes=3-2', 416, b''),
                    ('GET', 'bytes=-0', 416, b''),
                ]:
                    with self.subTest(method=method, range=value):
                        client = http.client.HTTPConnection(*server.server_address)
                        client.request(method, '/', headers={'Range': value} if value else {})
                        response = client.getresponse()
                        self.assertEqual(response.status, expected)
                        self.assertEqual(response.read(), content)
                        if expected == 206:
                            self.assertTrue(response.getheader('Content-Range').startswith('bytes '))
                        client.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
