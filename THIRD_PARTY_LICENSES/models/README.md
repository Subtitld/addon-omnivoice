# The model

The add-on downloads OmniVoice the first time a line is spoken; none of it is
in this archive.

OmniVoice is by Han Zhu, Lingxuan Ye, Wei Kang, Zengwei Yao, Liyong Guo,
Fangjun Kuang, Zhifeng Han, Weiji Zhuang, Long Lin and Daniel Povey (k2-fsa),
published as [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice). Its
code is Apache-2.0; its pre-trained weights are licensed **CC BY-NC**, for
non-commercial use only, "due to constraints from its training data". The
model card names no version of the licence; [CC-BY-NC-4.0.txt](CC-BY-NC-4.0.txt)
is its current version, for reference.

The add-on uses the weights as converted to GGUF, with 8-bit (Q8_0) matrices,
by the audio.cpp project, published in
[audio-cpp/audio.cpp-gguf](https://huggingface.co/audio-cpp/audio.cpp-gguf)
under the same licence. It is fetched at the revision `engine.MODEL_REVISION`
names (in the add-on's source, `omnivoice_addon/engine.py`) and checked
against its pinned sha256.

| File | What it is | When it downloads |
|------|------------|-------------------|
| `OmniVoice-GGUF/omnivoice-q8_0.gguf` (1.35 GB) | OmniVoice with its weights in 8-bit: the language model, the audio tokenizer and the text tokenizer | The first line |

Speech made with these weights may be used for non-commercial purposes only.
