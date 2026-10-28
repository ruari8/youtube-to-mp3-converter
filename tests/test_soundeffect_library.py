import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deploy/soundeffect'))
from library import Library, InputError, youtube_id
import auth


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'public/media').mkdir(parents=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4',
                        '-c:a', 'aac', str(self.root / 'public/media/tone.m4a')], check=True)
        self.seed = [{'id':'tone', 'youtubeId':'UaUa_0qPPgc', 'name':'Tone', 'url':'/media/tone.m4a', 'duration':4,
                      'presets':[{'start':0,'end':1}]}]
        self.lib = Library(self.root / 'data', self.root / 'public', self.seed, worker=False)

    def tearDown(self):
        self.temp.cleanup()

    def test_url_boundary_and_duplicate_imports(self):
        for url in ['https://youtu.be/UaUa_0qPPgc?t=2', 'https://www.youtube.com/watch?v=UaUa_0qPPgc&list=ignored',
                    'https://m.youtube.com/shorts/UaUa_0qPPgc']:
            self.assertEqual(youtube_id(url), 'UaUa_0qPPgc')
            self.assertTrue(self.lib.import_video(url)['existing'])
        for url in ['file:///etc/passwd', 'https://youtube.com.evil.test/watch?v=UaUa_0qPPgc',
                    'https://youtube.com@127.0.0.1/watch?v=UaUa_0qPPgc', 'https://youtube.com:443/watch?v=UaUa_0qPPgc',
                    'https://127.0.0.1/', 'https://youtube.com/playlist?list=abc', None]:
            with self.assertRaises(InputError):
                youtube_id(url)
        first = self.lib.import_video('https://youtu.be/abcdefghijk')
        again = self.lib.import_video('https://www.youtube.com/watch?v=abcdefghijk')
        self.assertEqual(first['job']['id'], again['job']['id'])
        self.lib.import_video('https://youtu.be/bcdefghijkl')
        self.lib.import_video('https://youtu.be/cdefghijklm')
        with self.assertRaises(InputError):
            self.lib.import_video('https://youtu.be/defghijklmn')

    def test_saved_mp3_duration_persistence_and_reversible_removal(self):
        clip = self.lib.save_clip({'trackId':'tone','name':'My tone','start':.5,'end':2.75})
        file = self.root / 'data/clips' / (clip['id'] + '.mp3')
        info = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)]))
        self.assertEqual(info['streams'][0]['codec_name'], 'mp3')
        self.assertAlmostEqual(float(info['format']['duration']), 2.25, delta=.06)
        self.lib.remove_clip(clip['id'])
        self.assertEqual(self.lib.board(), [])
        self.assertTrue(file.exists())
        self.lib.remove_clip(clip['id'], restore=True)
        reopened = Library(self.root / 'data', self.root / 'public', self.seed, worker=False)
        self.assertEqual(reopened.board(), [clip])
        self.lib.seed_board()
        self.lib.seed_board()
        self.assertEqual(len(self.lib.board()), 2)
        for start, end in [(-1,1),(2,1),(0,5),(float('nan'),1),(0,float('inf')),(True,2)]:
            with self.assertRaises(InputError):
                self.lib.save_clip({'trackId':'tone','name':'Invalid','start':start,'end':end})

    def test_download_preflight_rejects_live_and_long_videos(self):
        job = self.lib.import_video('https://youtu.be/abcdefghijk')['job']
        for metadata in [{'duration':601}, {'duration':100,'is_live':True}, {'duration':None}]:
            with patch('library.run', return_value=json.dumps(metadata).encode()) as runner:
                with self.assertRaises(InputError):
                    self.lib.download(job)
                self.assertEqual(runner.call_count,1)

    def test_mac_status_requires_socks_reply_not_just_a_listening_port(self):
        with patch.dict('os.environ', {'SOUNDCUT_PROXY':'socks5://127.0.0.1:18088'}):
            with patch('library.socket.create_connection') as connect:
                connection = connect.return_value.__enter__.return_value
                connection.recv.side_effect = [b'\x05', b'\x00']
                self.assertTrue(self.lib.connection()['available'])
                connection.sendall.assert_called_with(b'\x05\x01\x00')
                connection.recv.side_effect = TimeoutError()
                self.assertFalse(self.lib.connection()['available'])

    def test_http_requires_session_and_same_origin_for_mutations(self):
        auth.Handler.config = {'session_key':'cd'*32}
        auth.Handler.library = self.lib
        server = auth.ThreadingHTTPServer(('127.0.0.1',0),auth.Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        cookie = f'{auth.COOKIE}=' + auth.session_token(bytes.fromhex('cd'*32))
        def request(method, path, body=None, headers=None):
            connection = http.client.HTTPConnection(*server.server_address)
            connection.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers or {})
            response = connection.getresponse()
            value = response.status,json.loads(response.read())
            connection.close()
            return value
        try:
            self.assertEqual(request('GET','/api/library')[0],401)
            self.assertEqual(request('GET','/api/library',headers={'Cookie':cookie})[1],self.seed)
            payload = {'trackId':'tone','name':'HTTP sound','start':0,'end':1}
            self.assertEqual(request('POST','/api/board',payload,{'Cookie':cookie})[0],403)
            headers = {'Cookie':cookie,'Origin':auth.ORIGIN}
            code, clip = request('POST','/api/board',payload,headers)
            self.assertEqual(code,200)
            self.assertEqual(request('DELETE','/api/board/'+clip['id'],headers=headers)[0],200)
            self.assertEqual(request('POST','/api/board/'+clip['id']+'/restore',headers=headers)[0],200)
            self.assertEqual(request('POST','/api/imports',{'url':'http://localhost/'},headers)[0],400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
