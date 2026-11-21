"""manifest.json agrees with the code: voices, languages, settings, version, model.

Copyright 2026 Subtitld contributors
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from omnivoice_addon import __version__, engine, languages, voices
from omnivoice_addon import __main__ as addon

REPO = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((REPO / 'manifest.json').read_text(encoding='utf-8'))
FIELDS = {field['key']: field for field in MANIFEST['config_schema']['fields']}


def test_identity_and_version():
    assert MANIFEST['id'] == 'omnivoice'
    assert MANIFEST['executable'] == 'bin/omnivoice-addon'
    assert MANIFEST['tasks'] == ['tts.synthesize']
    pyproject = (REPO / 'pyproject.toml').read_text(encoding='utf-8')
    assert re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1) == __version__
    assert MANIFEST['version'] == __version__ == addon.ADDON_VERSION


def test_voices_and_languages_match_the_code():
    assert MANIFEST['voices'] == voices.manifest_voices()
    assert MANIFEST['languages'] == languages.manifest_languages()
    assert len(languages.NAMES) > 600
    clone = [v for v in MANIFEST['voices'] if v.get('requires')]
    assert [v['id'] for v in clone] == [voices.CLONE]
    for voice in voices.VOICES:
        if voice.id not in (voices.CLONE, voices.DESCRIBED):
            assert voice.design, voice.id


def test_designs_use_only_omnivoice_attributes():
    known = set(voices.GENDERS + voices.AGES + voices.PITCHES + voices.ACCENTS + (voices.WHISPER,))
    for voice in voices.VOICES:
        items = [item.strip() for item in voice.design.split(',') if item.strip()]
        assert set(items) <= known, voice.id
        groups = [g for g in (voices.GENDERS, voices.AGES, voices.PITCHES, voices.ACCENTS)]
        assert all(sum(item in group for item in items) <= 1 for group in groups), voice.id


def test_anchor_sentences_are_for_languages_the_model_speaks():
    assert set(voices.ANCHORS) <= set(languages.NAMES)
    assert all(sentence.strip() for sentence in voices.ANCHORS.values())
    assert voices.anchor_for('pt') == ('pt', voices.ANCHORS['pt'])
    assert voices.anchor_for('th') == ('en', voices.ANCHORS['en'])
    assert voices.anchor_for('') == ('en', voices.ANCHORS['en'])


def test_language_tags_resolve():
    assert languages.resolve('pt-BR') == 'pt'
    assert languages.resolve('ar') == 'arb' and 'ar' in MANIFEST['languages']
    assert languages.resolve('zh_Hans') == 'zh'
    assert languages.resolve('xx') == '' and languages.resolve(None) == ''


def test_every_setting_the_code_reads_is_declared():
    read = set(addon._options())
    assert read <= set(FIELDS)
    # OmniVoice cannot clone without the clip's transcript, so the host's
    # timbre-only switch is not offered.
    assert 'skip_ref_text' not in FIELDS
    for key, group in (('voice_gender', voices.GENDERS), ('voice_age', voices.AGES),
                       ('voice_pitch', voices.PITCHES), ('voice_accent', voices.ACCENTS)):
        assert [o['value'] for o in FIELDS[key]['options']] == ['', *group], key


def test_setting_defaults_are_valid():
    for key, field in FIELDS.items():
        if field['type'] == 'select':
            assert field['default'] in [o['value'] for o in field['options']], key
        if field['type'] in ('int', 'number'):
            assert field['min'] <= field['default'] <= field['max'], key


def test_the_code_clamps_numbers_to_the_declared_range(monkeypatch):
    for key in ('steps', 'cfg', 'threads'):
        field = FIELDS[key]
        monkeypatch.setenv(f'OMNIVOICE_{key.upper()}', str(field['max'] * 10 + 1))
        assert addon._options()[key] == field['max'], key
        monkeypatch.setenv(f'OMNIVOICE_{key.upper()}', str(field['min'] - 1))
        assert addon._options()[key] == field['min'], key


def test_the_model_entry_is_the_pinned_revision():
    model = MANIFEST['models'][0]
    assert model['repo'] == engine.MODEL_REPO
    assert model['revision'] == engine.MODEL_REVISION
    assert model['size_mb'] == round(engine.MODEL_BYTES / 2**20)
    assert model['bundled'] is False
    assert MANIFEST['disk_required_mb'] > model['size_mb']


def test_cpu_lists_parse():
    assert engine._cpu_list('0-3,8,10-11\n') == [0, 1, 2, 3, 8, 10, 11]


def test_the_settings_are_the_ones_this_runtime_has():
    assert MANIFEST['compute'] == 'cpu' and MANIFEST['accelerators'] == ['mps']
    assert FIELDS['steps']['default'] == engine.DEFAULT_STEPS
    assert 'CC BY-NC' in MANIFEST['license'] and MANIFEST['models'][0]['license'] == 'CC BY-NC'
    assert MANIFEST['ram_required_mb'] >= 2048
