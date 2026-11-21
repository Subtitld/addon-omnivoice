"""The voices the add-on offers.

Copyright 2026 Subtitld contributors
SPDX-License-Identifier: Apache-2.0

Two kinds of voice:

- `omnivoice-clone` clones the speaker from the video: the host hands over a
  clip of their speech and its transcript. OmniVoice needs the transcript.
- The others are designed from attributes OmniVoice knows (gender, age,
  pitch, whisper, an English accent). OmniVoice makes a new voice from them
  on every line, and a dub needs the same voice on every line. So a designed
  voice is made once per speaker, as a fixed sentence (an "anchor"), cached,
  and every line clones the anchor.
"""

from __future__ import annotations

from dataclasses import dataclass

CLONE = 'omnivoice-clone'
DESCRIBED = 'omnivoice-described'

# OmniVoice's voice-design vocabulary (audio.cpp's prompt_builder.cpp): one
# item of each group at most.
GENDERS = ('male', 'female')
AGES = ('child', 'teenager', 'young adult', 'middle-aged', 'elderly')
PITCHES = ('very low pitch', 'low pitch', 'moderate pitch', 'high pitch', 'very high pitch')
ACCENTS = ('american accent', 'british accent', 'australian accent', 'canadian accent', 'indian accent',
           'chinese accent', 'japanese accent', 'korean accent', 'portuguese accent', 'russian accent')
WHISPER = 'whisper'


@dataclass(frozen=True)
class Voice:
    id: str
    display_name: str
    design: str = ''   # OmniVoice attributes; empty for the clone, and for DESCRIBED (from the settings)


VOICES = (
    Voice(CLONE, "Speaker's own voice (cloned from the video)"),
    Voice('omnivoice-woman', 'Woman', 'female, young adult, moderate pitch'),
    Voice('omnivoice-woman-low', 'Woman, lower voice', 'female, middle-aged, low pitch'),
    Voice('omnivoice-older-woman', 'Older woman', 'female, elderly'),
    Voice('omnivoice-man', 'Man', 'male, young adult, moderate pitch'),
    Voice('omnivoice-man-deep', 'Man, deep voice', 'male, middle-aged, low pitch'),
    Voice('omnivoice-older-man', 'Older man', 'male, elderly, low pitch'),
    Voice('omnivoice-girl', 'Teenage girl', 'female, teenager, high pitch'),
    Voice('omnivoice-boy', 'Teenage boy', 'male, teenager'),
    Voice('omnivoice-child', 'Child', 'child, high pitch'),
    Voice('omnivoice-whisper', 'Whispering woman', 'female, young adult, whisper'),
    Voice(DESCRIBED, 'Voice you describe (in Configure)'),
)
BY_ID = {voice.id: voice for voice in VOICES}


def design_from_settings(gender: str, age: str, pitch: str, accent: str, whisper: bool) -> str:
    """The attributes chosen in Configure, as OmniVoice takes them; '' when none is."""
    items = [value for value, allowed in ((gender, GENDERS), (age, AGES), (pitch, PITCHES), (accent, ACCENTS))
             if value in allowed]
    if whisper:
        items.append(WHISPER)
    return ', '.join(items)


# Anchor sentences: about six seconds of plain speech, worded so that no form
# depends on the speaker's gender. A line in a language with none here clones
# the English anchor, which OmniVoice does across languages.
ANCHORS = {
    'en': 'Good morning. Today we have a long road ahead of us, so it would be wise to set off early, '
          'before the rain begins.',
    'pt': 'Bom dia. Hoje temos um longo caminho pela frente, então é melhor sair cedo, '
          'antes que a chuva comece.',
    'es': 'Buenos días. Hoy tenemos un largo camino por delante, así que conviene salir temprano, '
          'antes de que empiece a llover.',
    'fr': "Bonjour. Aujourd'hui, nous avons une longue route devant nous, alors mieux vaut partir tôt, "
          'avant que la pluie ne commence.',
    'de': 'Guten Morgen. Heute liegt ein langer Weg vor uns, also brechen wir besser früh auf, '
          'bevor der Regen beginnt.',
    'it': 'Buongiorno. Oggi abbiamo una lunga strada davanti a noi, quindi conviene partire presto, '
          'prima che cominci a piovere.',
    'nl': 'Goedemorgen. Vandaag hebben we een lange weg voor de boeg, dus we kunnen beter vroeg vertrekken, '
          'voordat het gaat regenen.',
    'pl': 'Dzień dobry. Dziś czeka nas długa droga, więc lepiej wyruszyć wcześnie, '
          'zanim zacznie padać deszcz.',
    'ru': 'Доброе утро. Сегодня у нас впереди долгая дорога, поэтому лучше выйти пораньше, '
          'пока не начался дождь.',
    'zh': '早上好。今天我们还有很长的路要走，所以最好早点出发，趁着还没下雨。',
    'ja': 'おはようございます。今日は長い道のりになりそうなので、雨が降り出す前に早めに出発しましょう。',
    'ko': '좋은 아침이에요. 오늘은 갈 길이 멀어서, 비가 오기 전에 일찍 출발하는 게 좋겠어요.',
}


def anchor_for(language: str) -> tuple[str, str]:
    """(language, sentence) of the anchor for a line in `language` (an OmniVoice code)."""
    if language in ANCHORS:
        return language, ANCHORS[language]
    return 'en', ANCHORS['en']


def manifest_voices() -> list[dict]:
    """The voice list as manifest.json and the hello frame carry it."""
    out = []
    for voice in VOICES:
        entry = {'id': voice.id, 'language': '*', 'display_name': voice.display_name}
        if voice.id == CLONE:
            entry['requires'] = ['voice_ref_audio', 'voice_ref_text']
        out.append(entry)
    return out
