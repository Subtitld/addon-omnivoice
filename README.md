# OmniVoice add-on for Subtitld

Text-to-speech for [Subtitld](https://subtitld.org) dubbing with k2-fsa's
[OmniVoice](https://github.com/k2-fsa/OmniVoice): more than 600 languages at
24 kHz, in the speaker's own voice cloned from the video, across languages, or
in a voice designed from a few attributes.

**The model's weights are for non-commercial use only (CC BY-NC).** The
add-on itself is Apache-2.0.

## Voices

- **Speaker's own voice (cloned from the video).** Subtitld cuts a clip of the
  speaker from the video and sends it with the subtitle text spoken in it.
  OmniVoice clones the voice from the clip and its words, and speaks the line
  in any of its languages, whatever the clip's language. It needs those words:
  *Clone the timbre only* doesn't work with this add-on.
- **Designed voices**: Woman, Woman with a lower voice, Older woman, Man, Man
  with a deep voice, Older man, Teenage girl, Teenage boy, Child, Whispering
  woman, and *Voice you describe*, built from the attributes you pick in
  Configure (gender, age, pitch, an accent for English, whisper). OmniVoice
  makes up a new voice every time, so the add-on makes each speaker's voice
  once, as a fixed sentence, and every line of that speaker clones it. Two
  speakers given the same designed voice still sound like two people.

The voice is chosen per speaker in Subtitld's dubbing panel. A speaker's
*Rate* sets OmniVoice's pace.

## Languages

646, from Afrikaans to Zulu, with many regional languages and varieties: the
list is OmniVoice's own (`omnivoice_addon/languages.py`, generated from
audio.cpp's copy by `tools/regen_languages.py`). The add-on passes the
project's language to OmniVoice, and lets it tell the language from the text
when it doesn't know the tag.

## What it needs

- **Disk:** about 1.5 GB. The model, 1.35 GB, downloads from Hugging Face on
  the first synthesis, at a pinned revision, checked by sha256, into
  Subtitld's model cache. An interrupted download resumes. `HF_ENDPOINT`
  points it at a mirror; `OMNIVOICE_MODEL_DIR` at a folder that already holds
  the file.
- **Memory:** about 2.5 GB free.
- **Time:** OmniVoice refines the whole line in a fixed number of diffusion
  steps. With the default 16, a cloned line takes about 6 seconds per second
  of speech on an Intel Core i7-13700T (8 performance cores), and a line
  without a clip about half that. 32 steps, OmniVoice's own default, take
  twice as long and come a little closer to the speaker. On an Apple Silicon
  Mac it runs on the GPU.

After the download nothing leaves the machine.

## Settings

| Setting | Default | |
|---|---|---|
| Quality steps | 16 | diffusion steps; 8 to 32 |
| Guidance | 2.0 | how closely speech follows the text and voice |
| CPU threads | 0 | the performance cores on a CPU that has efficiency cores too, else one per core |
| Voice gender, age, pitch, accent, whisper | | for *Voice you describe* |
| Fallback reference clip / transcript | | for the cloned voice when Subtitld has no clip to send |

## How it runs the model

Speech is made by [audio.cpp](https://github.com/0xShug0/audio.cpp)
(Apache-2.0), a C++ runtime on ggml, which the add-on calls through its C API
with ctypes. `tools/build_native.py` builds it from source at a pinned commit
with only OmniVoice compiled in, and applies one patch,
`tools/patches/audiocpp-step-callback.patch`: a callback before each diffusion
step, so a line reports its progress and stops between two steps when it is
cancelled. Upstream's C API runs a line to its end. ggml picks the build for
the processor it runs on, from SSE4.2 to AVX-512. On an Apple Silicon Mac it
runs on the GPU (Metal), once a short test line in a separate process has
shown that works there; `OMNIVOICE_DEVICE=cpu` or `metal` skips the test.

The model is OmniVoice with its weights in 8-bit (Q8_0), as audio.cpp's
project converted it. In our tests on English, Portuguese and Japanese lines
cloned from an English clip, every word was transcribed correctly and the
clones scored 0.80–0.82 in speaker similarity.

The add-on itself needs nothing but Python's standard library. It is built
the same way as the VoxCPM add-on, which runs on audio.cpp too.

## Building

Linux, in the AlmaLinux 8 container, so the archive runs on glibc 2.28 and
newer (needs Docker):

```bash
tools/build_linux.sh                      # audio.cpp, tests, the bundle, the archive
tools/test_archive.sh almalinux:8         # the archive, installed as Subtitld does, on AlmaLinux 8
```

`OMNIVOICE_TEST_MODELS_DIR` (a folder holding `omnivoice/OmniVoice-GGUF/`, or
an empty one to download into) also has the archive speak and cancel for real.
For the engine tests with the model, from source, set `OMNIVOICE_TEST_MODEL`
to the GGUF file:

```bash
python tools/build_native.py              # Linux: tools/build_native_linux.sh
pip install -e '.[build,dev]'
OMNIVOICE_TEST_MODEL=/path/to/omnivoice-q8_0.gguf pytest
pyinstaller pyinstaller.spec --noconfirm
dist/omnivoice-addon/omnivoice-addon --self-test
```

The release workflow builds, proves and publishes every platform on a tag
`v<version>` matching `manifest.json`; a manual run can build only some
platforms (`targets`). `tools/assemble_licences.py` fails the build when a
native file in the bundle has no notice.

## Licence

The add-on is Apache-2.0. audio.cpp is Apache-2.0, with ggml, cJSON, libyaml,
utf8proc and llama.cpp's tokenizer (MIT) compiled in. The OmniVoice weights
are CC BY-NC (k2-fsa): speech made with them is for non-commercial use only.
Each archive carries `THIRD_PARTY_LICENSES/` with the licence of everything
frozen into it, and our patch to audio.cpp.

Voice cloning makes speech that sounds like a real person. Clone voices you
have the right to use, and say that a dub is synthetic where it matters.
