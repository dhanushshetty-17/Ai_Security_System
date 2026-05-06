"""Audio input helpers for microphone and file-based demos."""

from __future__ import annotations

import queue
from pathlib import Path
from typing import Iterator

import numpy as np

from security_ai_system.audio.yamnet_classifier import YAMNET_SAMPLE_RATE, prepare_waveform


def load_audio_file(path: str | Path, sample_rate: int = YAMNET_SAMPLE_RATE) -> np.ndarray:
    """Load audio from a file and resample it for YAMNet.

    `librosa` can load WAV/MP3 and many video containers when the local audio
    backend has FFmpeg support. For presentation demos, WAV files are the most
    reliable option on Windows.
    """

    import librosa

    waveform, _ = librosa.load(str(path), sr=sample_rate, mono=True)
    return prepare_waveform(waveform)


def iter_audio_chunks(
    waveform: np.ndarray,
    sample_rate: int = YAMNET_SAMPLE_RATE,
    chunk_seconds: float = 1.0,
    hop_seconds: float | None = None,
) -> Iterator[np.ndarray]:
    """Yield fixed-size waveform chunks for streaming-style classification."""

    prepared = prepare_waveform(waveform)
    chunk_size = max(1, int(sample_rate * chunk_seconds))
    hop_size = max(1, int(sample_rate * (hop_seconds or chunk_seconds)))

    for start in range(0, len(prepared), hop_size):
        chunk = prepared[start : start + chunk_size]
        if len(chunk) < chunk_size:
            padded = np.zeros(chunk_size, dtype=np.float32)
            padded[: len(chunk)] = chunk
            chunk = padded
        yield chunk.astype(np.float32, copy=False)


class MicrophoneAudioStream:
    """Small sounddevice-based microphone chunk reader."""

    def __init__(
        self,
        sample_rate: int = YAMNET_SAMPLE_RATE,
        chunk_seconds: float = 1.0,
        device: int | str | None = None,
        queue_size: int = 8,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.device = device
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=queue_size)
        self._stream = None

    def start(self) -> None:
        """Start microphone capture."""

        import sounddevice as sd

        blocksize = int(self.sample_rate * self.chunk_seconds)

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            if status:
                return
            chunk = prepare_waveform(np.asarray(indata).copy())
            try:
                self._queue.put_nowait(chunk)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                self._queue.put_nowait(chunk)

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=blocksize,
            device=self.device,
            callback=callback,
        )
        self._stream.start()

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        """Read the next microphone chunk, or None on timeout."""

        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        """Stop microphone capture and release the device."""

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def __enter__(self) -> "MicrophoneAudioStream":
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        self.stop()

