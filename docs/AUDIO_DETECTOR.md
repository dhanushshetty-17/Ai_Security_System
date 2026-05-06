# Module 4: Audio Threat Detection

## What It Does

`detectors/audio_detector.py` uses Google YAMNet from TensorFlow Hub to classify
audio chunks and map AudioSet labels into security alerts:

- `SCREAM DETECTED`
- `GUNSHOT DETECTED`
- `GLASS BREAK DETECTED`
- `EXPLOSION DETECTED`

## Threat Scores

- Scream: `60`
- Gunshot: `120`
- Glass break: `70`
- Explosion: `100`

## How It Works

1. Audio is loaded or captured as mono 16 kHz waveform chunks.
2. `YamNetClassifier` runs the pretrained YAMNet model.
3. Raw AudioSet classes such as `Screaming`, `Gunshot, gunfire`, `Glass`, and
   `Explosion` are matched through configurable aliases.
4. `AudioThreatDetector` converts classifications into shared `Detection`
   objects and active alerts.
5. A short cooldown prevents repeated popups for the same continuous sound.

## Microphone Demo

```python
from security_ai_system.audio.audio_sources import MicrophoneAudioStream
from security_ai_system.detectors.audio_detector import AudioThreatDetector

detector = AudioThreatDetector(camera_id="microphone-0")
detector.load()

with MicrophoneAudioStream(chunk_seconds=1.0) as mic:
    while True:
        chunk = mic.read(timeout=2.0)
        if chunk is None:
            continue

        result = detector.predict(chunk)
        for alert in result.alerts:
            print(alert.label, alert.confidence, alert.threat_score)
```

Stop the script with `Ctrl+C`.

## File Demo

```python
from security_ai_system.audio.audio_sources import iter_audio_chunks, load_audio_file
from security_ai_system.detectors.audio_detector import AudioThreatDetector

waveform = load_audio_file("demo_audio.wav")
detector = AudioThreatDetector(camera_id="audio-file")
detector.load()

for chunk in iter_audio_chunks(waveform, chunk_seconds=1.0, hop_seconds=0.5):
    result = detector.predict(chunk)
    for alert in result.alerts:
        print(alert.label, alert.confidence)
```

`librosa` can load WAV/MP3 and some video containers when the local backend has
FFmpeg support. For stable Windows demos, use extracted WAV files.

## Unit Tests

These tests do not load TensorFlow Hub. They validate waveform preparation,
threat label mapping, detector conversion, and alert cooldown:

```powershell
cd security_ai_system
python -m unittest tests.test_audio_detection
```

## Troubleshooting

- If TensorFlow install fails, confirm you are using Python 3.10 64-bit.
- If YAMNet fails to download, check network access or pre-cache the TensorFlow
  Hub model.
- If microphone capture fails, check Windows microphone privacy permissions and
  close other apps using the device.
- If video audio cannot be loaded directly, extract audio to WAV first with
  FFmpeg and pass the WAV file to `load_audio_file`.

