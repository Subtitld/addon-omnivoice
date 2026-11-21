"""The tts.synthesize handler, with a stand-in for the model.

Copyright 2026 Subtitld contributors
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import wave
from pathlib import Path

from omnivoice_addon import engine, voices

REPO = Path(__file__).resolve().parents[1]


def _terminal(frames):
    terminal = [f for f in frames if f.get('type') in ('result', 'error')]
    assert len(terminal) == 1, frames
    return terminal[0]


def test_clone_with_transcript(run, reference, tmp_path):
    out = tmp_path / 'line.wav'
    frames, fake = run({'text': '  Olá,   mundo ', 'voice': voices.CLONE, 'output_path': str(out),
                        'language': 'pt-BR', 'voice_ref_audio': reference, 'voice_ref_text': 'Hello there',
                        'seed': 7})
    result = _terminal(frames)
    assert result['type'] == 'result', result
    text, kwargs = fake.calls[0]
    assert text == 'Olá, mundo'
    assert kwargs['reference'] == reference and kwargs['reference_text'] == 'Hello there'
    assert kwargs['language'] == 'pt' and kwargs['seed'] == 7 and kwargs['steps'] == engine.DEFAULT_STEPS
    assert kwargs['speed'] == 1.0 and kwargs['duration'] is None
    data = result['data']
    assert data['path'] == str(out) and data['sample_rate'] == 24000 and data['channels'] == 1
    with wave.open(str(out)) as clip:
        assert (clip.getnchannels(), clip.getsampwidth(), clip.getframerate()) == (1, 2, 24000)
        assert clip.getnframes() == 2400
    assert abs(data['duration_sec'] - 0.1) < 1e-6
    values = [f['value'] for f in frames if f['type'] == 'progress']
    assert values == sorted(values) and values[-1] == 1.0


def test_clone_without_transcript_is_refused(run, reference, tmp_path):
    frames, fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav'),
                        'voice_ref_audio': reference})
    error = _terminal(frames)
    assert error['code'] == 'bad_params' and 'words spoken in the clip' in error['message']
    assert not fake.calls


def test_clone_falls_back_to_the_configured_clip(run, reference, tmp_path, monkeypatch):
    monkeypatch.setenv('OMNIVOICE_VOICE_REF_AUDIO', reference)
    monkeypatch.setenv('OMNIVOICE_VOICE_REF_TEXT', 'configured words')
    frames, fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav')})
    assert _terminal(frames)['type'] == 'result'
    assert fake.calls[0][1]['reference_text'] == 'configured words'


def test_the_configured_transcript_never_pairs_with_the_hosts_clip(run, reference, tmp_path, monkeypatch):
    monkeypatch.setenv('OMNIVOICE_VOICE_REF_TEXT', 'words of another clip')
    frames, fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav'),
                        'voice_ref_audio': reference})
    assert _terminal(frames)['code'] == 'bad_params'
    assert not fake.calls


def test_clone_without_any_clip_is_refused(run, tmp_path):
    frames, fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav')})
    error = _terminal(frames)
    assert error['type'] == 'error' and error['code'] == 'bad_params'
    assert not fake.calls


def test_designed_voice_makes_its_anchor_once_per_speaker(run, tmp_path):
    params = {'text': 'Bom dia', 'voice': 'omnivoice-man-deep', 'language': 'pt-br', 'seed': 11,
              'output_path': str(tmp_path / 'a.wav')}
    frames, fake = run(params)
    assert _terminal(frames)['type'] == 'result'
    (anchor_text, anchor_kwargs), (line_text, line_kwargs) = fake.calls
    assert anchor_text == voices.ANCHORS['pt']
    assert anchor_kwargs['design'] == 'male, middle-aged, low pitch'
    assert anchor_kwargs['language'] == 'pt' and anchor_kwargs['seed'] == 11
    assert 'reference' not in anchor_kwargs
    assert line_text == 'Bom dia'
    assert line_kwargs['reference_text'] == voices.ANCHORS['pt']
    assert Path(line_kwargs['reference']).is_file()

    frames, fake = run(dict(params, text='Boa noite'))
    assert _terminal(frames)['type'] == 'result'
    assert [text for text, _ in fake.calls[-1:]] == ['Boa noite']
    assert len(fake.calls) == 3  # the anchor was reused

    frames, fake = run(dict(params, seed=12))  # another speaker, another voice
    assert len(fake.calls) == 5


def test_a_language_without_an_anchor_clones_the_english_one(run, tmp_path):
    frames, fake = run({'text': 'สวัสดี', 'voice': 'omnivoice-woman', 'language': 'th',
                        'output_path': str(tmp_path / 'a.wav')})
    assert _terminal(frames)['type'] == 'result'
    anchor_text, anchor_kwargs = fake.calls[0]
    assert anchor_text == voices.ANCHORS['en'] and anchor_kwargs['language'] == 'en'
    line_kwargs = fake.calls[1][1]
    assert line_kwargs['reference_text'] == voices.ANCHORS['en'] and line_kwargs['language'] == 'th'


def test_the_voice_you_describe_reads_the_settings(run, tmp_path, monkeypatch):
    params = {'text': 'Hi', 'voice': voices.DESCRIBED, 'output_path': str(tmp_path / 'a.wav')}
    error = _terminal(run(params)[0])
    assert error['code'] == 'bad_params'
    monkeypatch.setenv('OMNIVOICE_VOICE_GENDER', 'female')
    monkeypatch.setenv('OMNIVOICE_VOICE_AGE', 'elderly')
    monkeypatch.setenv('OMNIVOICE_VOICE_ACCENT', 'british accent')
    monkeypatch.setenv('OMNIVOICE_VOICE_PITCH', 'not a pitch')
    monkeypatch.setenv('OMNIVOICE_VOICE_WHISPER', 'true')
    frames, fake = run(params)
    assert _terminal(frames)['type'] == 'result'
    assert fake.calls[0][1]['design'] == 'female, elderly, british accent, whisper'


def test_rate_and_duration(run, reference, tmp_path):
    base = {'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav'),
            'voice_ref_audio': reference, 'voice_ref_text': 'Hello'}
    _frames, fake = run(dict(base, rate=25))
    assert fake.calls[-1][1]['speed'] == 1.25
    _frames, fake = run(dict(base, rate=-300, duration_sec=2.5))
    assert fake.calls[-1][1]['speed'] == 0.5 and fake.calls[-1][1]['duration'] == 2.5
    _frames, fake = run(dict(base, rate='fast', duration_sec='long'))
    assert fake.calls[-1][1]['speed'] == 1.0 and fake.calls[-1][1]['duration'] is None


def test_unknown_language_lets_the_model_tell(run, reference, tmp_path):
    _frames, fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav'),
                         'voice_ref_audio': reference, 'voice_ref_text': 'Hello', 'language': 'xx-yy'})
    assert fake.calls[0][1]['language'] == ''


def test_unknown_voice_and_missing_fields(run, tmp_path):
    error = _terminal(run({'text': 'Hi', 'voice': 'qwen3-ryan', 'output_path': str(tmp_path / 'a.wav')})[0])
    assert error['code'] == 'unsupported_voice'
    assert _terminal(run({'text': '   ', 'voice': voices.CLONE, 'output_path': 'x.wav'})[0])['code'] == 'bad_params'
    assert _terminal(run({'text': 'Hi', 'voice': voices.CLONE})[0])['code'] == 'bad_params'


def test_cancel_stops_the_line_between_steps(run, reference, tmp_path):
    out = tmp_path / 'a.wav'
    frames, _fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(out),
                         'voice_ref_audio': reference, 'voice_ref_text': 'Hello'}, cancel_at_step=3)
    error = _terminal(frames)
    assert error['type'] == 'error' and error['code'] == 'cancelled'
    assert not out.exists()


def test_settings_are_held_to_their_range(monkeypatch):
    from omnivoice_addon import __main__ as addon
    monkeypatch.setenv('OMNIVOICE_STEPS', '500')
    monkeypatch.setenv('OMNIVOICE_CFG', 'lots')
    options = addon._options()
    assert options['steps'] == 32 and options['cfg'] == 2.0


def test_the_process_says_hello_and_leaves_on_shutdown():
    env = dict(os.environ, PYTHONPATH=str(REPO))
    proc = subprocess.Popen([sys.executable, '-m', 'omnivoice_addon'], cwd=REPO, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        hello = json.loads(proc.stdout.readline())
        proc.stdin.write(b'{"type":"ready","host":"test"}\n')
        proc.stdin.write(b'{"id":"x","type":"asr.transcribe","params":{}}\n')
        proc.stdin.flush()
        error = json.loads(proc.stdout.readline())
        proc.stdin.write(b'{"type":"shutdown"}\n')
        proc.stdin.flush()
        assert proc.wait(timeout=20) == 0
    finally:
        proc.kill()
    assert hello['type'] == 'hello' and hello['addon'] == 'omnivoice'
    capability = hello['capabilities'][0]
    assert capability['task'] == 'tts.synthesize' and capability['voice_clone'] is True
    assert {v['id'] for v in capability['voices']} == set(voices.BY_ID)
    assert len(capability['languages']) > 600
    assert error == {'id': 'x', 'type': 'error', 'code': 'bad_params',
                     'message': "unsupported frame type 'asr.transcribe'", 'retryable': False}


def test_a_model_that_fails_on_metal_loads_on_the_cpu(run, reference, tmp_path, monkeypatch):
    monkeypatch.setattr(engine, 'choose_backend', lambda path: 'metal')
    backends = []

    def load(path, threads=0, backend='cpu'):
        backends.append(backend)
        if backend == 'metal':
            raise engine.EngineError('session: no Metal device')
        return engine.Loaded(lib=None, registry=None, model=None, session=None, threads=4, backend=backend)

    monkeypatch.setattr(engine, 'load', load)
    frames, _fake = run({'text': 'Hi', 'voice': voices.CLONE, 'output_path': str(tmp_path / 'a.wav'),
                         'voice_ref_audio': reference, 'voice_ref_text': 'Hello'})
    assert _terminal(frames)['type'] == 'result'
    assert backends == ['metal', 'cpu']
