"""
Background music. Drop actual audio files (.ogg or .mp3) at the paths
below — missing files are skipped silently, so the game still runs
fine with no sound.
"""
import pygame
import os

MUSIC_FILES = {
    "menu":         "assets/music/menu.ogg",
    "dead_forest":  "assets/music/dead_forest.ogg",
    "castle":       "assets/music/castle.ogg",
    "terrace":      "assets/music/terrace.ogg",
    "throne_room":  "assets/music/throne_room.ogg",
    "boss":         "assets/music/boss.ogg",
}
audio_state = {"key": None, "volume": 0.5}


def play_music(key, loops=-1, fade_ms=900):
    if audio_state["key"] == key:
        return
    path = MUSIC_FILES.get(key)
    if not path or not os.path.exists(path):
        pygame.mixer.music.stop()
        audio_state["key"] = None
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(audio_state["volume"])
        pygame.mixer.music.play(loops, fade_ms=fade_ms)
        audio_state["key"] = key
    except Exception as e:
        print(f"FAILED to load music {path}: {e}")
        audio_state["key"] = None


def set_music_volume(vol):
    audio_state["volume"] = max(0.0, min(1.0, vol))
    pygame.mixer.music.set_volume(audio_state["volume"])
