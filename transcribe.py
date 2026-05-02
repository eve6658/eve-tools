#!/usr/bin/env python3
"""Transcribe audio using faster-whisper."""
import sys
from faster_whisper import WhisperModel

def transcribe(audio_path, model_size="base", language="zh"):
    print(f"Loading model: {model_size}...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print("Transcribing...")
    segments, info = model.transcribe(audio_path, language=language, beam_size=5)
    
    print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    
    full_text = []
    for segment in segments:
        print(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
        full_text.append(segment.text)
    
    return "\n".join(full_text)

if __name__ == "__main__":
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "audio.mp3"
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"
    language = sys.argv[3] if len(sys.argv) > 3 else "zh"
    output = sys.argv[4] if len(sys.argv) > 4 else None
    
    text = transcribe(audio_path, model_size, language)
    
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nSaved to {output}")
    else:
        print(f"\n--- Full Text ---\n{text}")
