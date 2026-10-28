"""The saved sound pack's full audio, shared by the server and portable builder."""
import json
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs


LABELS = {
    '01-proud-to-be-an-american': ('Proud to be an American', 'Lee Greenwood'),
    '02-jojo-leave-get-out': ('Leave (Get Out)', 'JoJo'),
    '03-lenny-kravitz-american-woman': ('American Woman', 'Lenny Kravitz'),
    '04-northern-ireland-wonderful-day': ('Days Like This', 'Northern Ireland'),
    '05-nigel-farage-boring': ('Boring, boring, boring', 'Nigel Farage'),
    '06-eagle': ('Eagle', 'Sound effect'),
    '07-air-horn': ('Air horn', 'Sound effect'),
    '08-soulja-boy-kiss-me-thru-the-phone': ('Kiss Me Thru the Phone', 'Soulja Boy'),
    '09-northern-irish-bouncer': ('Belfast bouncer', 'Northern Ireland'),
}


def load_library(downloads: Path) -> list[dict]:
    pack = downloads / 'stream-deck-sounds'
    manifest = pack / 'sources-and-timestamps.json'
    if not manifest.exists():
        return []
    library = []
    for record in json.loads(manifest.read_text()):
        audio = (pack / record['full_audio']).resolve()
        if not audio.is_relative_to(pack.resolve()) or not audio.is_file():
            continue
        name, category = LABELS.get(record['name'], (record['title'], 'Your audio'))
        presets = []
        for clip in record['clips']:
            label = 'Original cut'
            if len(record['clips']) > 1:
                label = 'Single boring' if clip['end_seconds'] == 1 else 'Triple boring'
            presets.append({'label': label, 'start': clip['start_seconds'], 'end': clip['end_seconds']})
        library.append({
            'id': record['name'], 'name': name, 'category': category,
            'youtubeId': parse_qs(urlparse(record['url']).query).get('v', [None])[0],
            'duration': record['audio_duration_seconds'],
            'url': '/downloads/' + quote(audio.relative_to(downloads.resolve()).as_posix()),
            'presets': presets,
        })
        video = (pack / record['full_video']).resolve()
        if video.is_relative_to(pack.resolve()) and video.is_file():
            library[-1]['videoUrl'] = '/downloads/' + quote(video.relative_to(downloads.resolve()).as_posix())
    return library
