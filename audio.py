"""
Background music. Drop actual audio files at the paths below —
missing files are skipped silently, so the game still runs fine
with no sound.

Several keys can point at the SAME file (all four regular stages
share one track here) — play_music tracks the resolved file path,
not the key, so moving between stages that use the same track never
restarts it. It only actually reloads when the file changes.
"""
import pygame
import os

MUSIC_FILES = {
    "menu":         "assets/music/menu.mp3",
    "dead_forest":  "assets/music/music_stage1.mp3",
    "castle":       "assets/music/music_stage1.mp3",
    "terrace":      "assets/music/music_stage1.mp3",
    "throne_room":  "assets/music/music_stage1.mp3",
    "boss":         "assets/music/throne_room.mp3",
}
audio_state = {"path": None, "volume": 0.5}


def play_music(key, loops=-1, fade_ms=900):
    path = MUSIC_FILES.get(key)
    if not path or not os.path.exists(path):
        pygame.mixer.music.stop()
        audio_state["path"] = None
        return
    if audio_state["path"] == path:
        return  # same track already playing — let it keep going
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(audio_state["volume"])
        pygame.mixer.music.play(loops, fade_ms=fade_ms)
        audio_state["path"] = path
    except Exception as e:
        print(f"FAILED to load music {path}: {e}")
        audio_state["path"] = None


def set_music_volume(vol):
    audio_state["volume"] = max(0.0, min(1.0, vol))
    pygame.mixer.music.set_volume(audio_state["volume"])
