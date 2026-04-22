"""
AI-composed chiptune multi-version renderer.
Enhanced with Overdrive, Advanced Drums, and Structure support.
"""
import json
import sys
import glob
import os
import inspect
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent
SONGS_DIR = ROOT / 'songs'
OUT_DIR = ROOT / 'out'
OUT_DIR.mkdir(exist_ok=True)

SR = 44100
N_LOOPS = 2

NOTE_MAP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

def note_to_midi(n):
    if n is None or n == 'rest' or n == '.': return None
    pc = NOTE_MAP[n[0]]
    i = 1
    if i < len(n) and n[i] in '#b':
        pc += 1 if n[i] == '#' else -1
        i += 1
    return pc + (int(n[i:]) + 1) * 12

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

def adsr(n, attack_frac=0.003, release_frac=0.04, sustain=1.0):
    env = np.ones(n) * sustain
    a = max(1, int(n * attack_frac)); r = max(1, int(n * release_frac))
    if a + r > n: a = n // 2; r = n - a
    env[:a] = np.linspace(0, sustain, a)
    env[-r:] = np.linspace(sustain, 0, r)
    return env

def apply_overdrive(wave, gain=1.0):
    if gain <= 1.0: return wave
    return np.tanh(wave * gain)

def pulse_wave(freq, duration, duty, vol, attack=0.003, release=0.04, vibrato_rate=0, vibrato_depth=0, overdrive=1.0):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    t = np.arange(n) / SR
    if vibrato_rate > 0 and vibrato_depth > 0:
        phase = freq * (t + (vibrato_depth / (2 * np.pi * vibrato_rate)) * (1 - np.cos(2 * np.pi * vibrato_rate * t)))
    else: phase = t * freq
    w = np.where(phase % 1.0 < duty, 1.0, -1.0) * vol * adsr(n, attack, release)
    return apply_overdrive(w, overdrive)

def triangle_wave(freq, duration, vol, attack=0.003, release=0.04, vibrato_rate=0, vibrato_depth=0, overdrive=1.0):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    t = np.arange(n) / SR
    if vibrato_rate > 0 and vibrato_depth > 0:
        phase = freq * (t + (vibrato_depth / (2 * np.pi * vibrato_rate)) * (1 - np.cos(2 * np.pi * vibrato_rate * t)))
    else: phase = t * freq
    w = (4 * np.abs((phase % 1.0) - 0.5) - 1) * vol * adsr(n, attack, release)
    return apply_overdrive(w, overdrive)

def sawtooth_wave(freq, duration, vol, attack=0.003, release=0.04, vibrato_rate=0, vibrato_depth=0, overdrive=1.0):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    t = np.arange(n) / SR
    if vibrato_rate > 0 and vibrato_depth > 0:
        phase = freq * (t + (vibrato_depth / (2 * np.pi * vibrato_rate)) * (1 - np.cos(2 * np.pi * vibrato_rate * t)))
    else: phase = t * freq
    w = (2.0 * (phase % 1.0) - 1.0) * vol * adsr(n, attack, release)
    return apply_overdrive(w, overdrive)

def sine_wave(freq, duration, vol, attack=0.003, release=0.04, vibrato_rate=0, vibrato_depth=0, overdrive=1.0):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    t = np.arange(n) / SR
    if vibrato_rate > 0 and vibrato_depth > 0:
        phase = freq * (t + (vibrato_depth / (2 * np.pi * vibrato_rate)) * (1 - np.cos(2 * np.pi * vibrato_rate * t)))
    else: phase = t * freq
    w = np.sin(2 * np.pi * phase) * vol * adsr(n, attack, release)
    return apply_overdrive(w, overdrive)

def fm_wave(freq, duration, vol, attack=0.003, release=0.04, ratio=2.0, index=2.0, vibrato_rate=0, vibrato_depth=0, overdrive=1.0):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    t = np.arange(n) / SR
    if vibrato_rate > 0 and vibrato_depth > 0:
        v_mod = (vibrato_depth / (2 * np.pi * vibrato_rate)) * (1 - np.cos(2 * np.pi * vibrato_rate * t))
        base_phase = 2 * np.pi * freq * (t + v_mod)
        modulator = np.sin(2 * np.pi * freq * ratio * (t + v_mod)) * index
    else:
        base_phase = 2 * np.pi * freq * t
        modulator = np.sin(2 * np.pi * freq * ratio * t) * index
    w = np.sin(base_phase + modulator) * vol * adsr(n, attack, release)
    return apply_overdrive(w, overdrive)

def string_wave(freq, duration, vol, attack=0.003, release=0.04, overdrive=1.0):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    period = int(SR / freq)
    if period <= 0: return np.zeros(n)
    ring_buf = np.random.uniform(-1, 1, period)
    out = np.zeros(n)
    for i in range(n):
        val = ring_buf[i % period]
        out[i] = val
        ring_buf[i % period] = (val + ring_buf[(i + 1) % period]) * 0.496
    w = out * vol * adsr(n, attack, release)
    return apply_overdrive(w, overdrive)

def drum_hit(kind, duration):
    n = int(SR * duration)
    if n <= 0: return np.zeros(0)
    t = np.arange(n) / SR
    if kind == 'K':
        f = 150 * np.exp(-t * 50) + 40
        w = np.sin(2 * np.pi * f * t); env = np.exp(-t * 15)
        return w * env * 1.2
    elif kind == 'S':
        noise = np.random.uniform(-1, 1, n)
        sos = butter(2, [1000, 3000], 'bandpass', fs=SR, output='sos')
        noise_f = sosfilt(sos, noise)
        tone = np.where((t * 220) % 1.0 < 0.5, 1.0, -1.0) * np.exp(-t * 40)
        env = np.exp(-t * 12)
        return (noise_f * 0.8 + tone * 0.4) * env * 1.0
    else:
        noise = np.random.uniform(-1, 1, n)
        sos = butter(2, 7000, 'highpass', fs=SR, output='sos'); env = np.exp(-t * 40)
        return sosfilt(sos, noise) * env * 0.3

def apply_echo(audio, bpm, delay_beats=0.75, feedback=0.4, mix_ratio=0.3):
    delay_samples = int(SR * (60 / bpm) * delay_beats)
    if delay_samples <= 0: return audio
    out = np.copy(audio)
    for i in range(delay_samples, len(audio)): out[i] += out[i - delay_samples] * feedback
    return audio * (1 - mix_ratio) + out * mix_ratio

def render_events_track(events, voice_fn, step_sec, intro_sec, loop_sec, **voice_kw):
    total_sec = intro_sec + (loop_sec * N_LOOPS)
    total_samples = int(SR * total_sec); out = np.zeros(total_samples)
    sig = inspect.signature(voice_fn); valid_params = sig.parameters.keys()
    gate = voice_kw.pop('gate', 0.92); filtered_kw = {k: v for k, v in voice_kw.items() if k in valid_params}
    for run_idx in range(1 + N_LOOPS):
        current_time = 0
        start_offset = 0 if run_idx == 0 else intro_sec + (run_idx - 1) * loop_sec
        for i in range(0, len(events), 2):
            note, steps = events[i], events[i + 1]
            dur = steps * step_sec * gate; midi = note_to_midi(note)
            if run_idx == 0:
                if current_time < intro_sec and midi is not None:
                    chunk = voice_fn(mtof(midi), dur, **filtered_kw)
                    s = int(current_time * SR); e = min(s + len(chunk), total_samples)
                    out[s:e] += chunk[:e - s]
            else:
                if current_time >= intro_sec and midi is not None:
                    write_t = start_offset + (current_time - intro_sec)
                    chunk = voice_fn(mtof(midi), dur, **filtered_kw)
                    s = int(write_t * SR); e = min(s + len(chunk), total_samples)
                    out[s:e] += chunk[:e - s]
            current_time += steps * step_sec
    return out

def render_drums(drum_str, step_sec, intro_sec, loop_sec):
    total_sec = intro_sec + (loop_sec * N_LOOPS)
    total_samples = int(SR * total_sec); out = np.zeros(total_samples)
    for run_idx in range(1+N_LOOPS):
        current_time = 0
        start_offset = 0 if run_idx == 0 else intro_sec + (run_idx - 1) * loop_sec
        for hit in drum_str:
            if hit != '.':
                dur = step_sec * (0.2 if hit == 'H' else 0.5); chunk = drum_hit(hit, dur)
                if run_idx == 0:
                    if current_time < intro_sec:
                        s = int(current_time * SR); e = min(s + len(chunk), total_samples); out[s:e] += chunk[:e - s]
                else:
                    if current_time >= intro_sec:
                        write_t = start_offset + (current_time - intro_sec)
                        s = int(write_t * SR); e = min(s + len(chunk), total_samples); out[s:e] += chunk[:e - s]
            current_time += step_sec
    return out

def render_song(song):
    bpm = song['bpm']; bars = song['bars']
    intro_bars = song.get('intro_bars', 0); loop_bars = bars - intro_bars
    step_sec = 60 / bpm / 4; intro_sec = intro_bars * 16 * step_sec; loop_sec = loop_bars * 16 * step_sec
    mix = song['mix']
    def get_wave_fn(name):
        return {'pulse': pulse_wave, 'triangle': triangle_wave, 'sawtooth': sawtooth_wave,
                'sine': sine_wave, 'fm': fm_wave, 'string': string_wave}.get(name, pulse_wave)
    def render_track(tname, wave_fn):
        return render_events_track(song['tracks'][tname], wave_fn, step_sec, intro_sec, loop_sec,
                                   vol=mix[tname + '_vol'], duty=mix.get(tname + '_duty', 0.5),
                                   attack=mix.get(tname + '_attack', 0.003), release=mix.get(tname + '_release', 0.04),
                                   ratio=mix.get(tname + '_fm_ratio', 2.0), index=mix.get(tname + '_fm_index', 2.0),
                                   gate=mix.get(tname + '_gate', 0.92), vibrato_rate=mix.get(tname + '_vibrato_rate', 0),
                                   vibrato_depth=mix.get(tname + '_vibrato_depth', 0), overdrive=mix.get(tname + '_overdrive', 1.0))
    lead = render_track('lead', get_wave_fn(mix.get('lead_wave', 'pulse')))
    harm = render_track('harm', get_wave_fn(mix.get('harm_wave', 'pulse')))
    bass = render_track('bass', get_wave_fn(mix.get('bass_wave', 'triangle')))
    drums = render_drums(song['tracks']['drums'], step_sec, intro_sec, loop_sec)
    mix_buf = (lead + harm + bass + drums) * mix['master']
    if mix.get('echo_mix', 0) > 0:
        mix_buf = apply_echo(mix_buf, bpm, delay_beats=mix.get('echo_delay', 0.75),
                            feedback=mix.get('echo_feedback', 0.4), mix_ratio=mix.get('echo_mix', 0.3))
    peak = float(np.max(np.abs(mix_buf)))
    if peak > 1.0: mix_buf = mix_buf / peak * 0.98
    return mix_buf, peak, intro_sec + (loop_sec * N_LOOPS)

VALID_AUTHORS = {'Claude', 'Gemini', 'Codex', 'Human'}

def validate_song(song):
    if 'author' not in song:
        raise ValueError(f"{song['id']}: missing 'author' field (required — must be one of {sorted(VALID_AUTHORS)})")
    if song['author'] not in VALID_AUTHORS:
        raise ValueError(f"{song['id']}: author='{song['author']}' not in {sorted(VALID_AUTHORS)}")
    bar_steps = 16 * song['bars']
    for tname in ('lead', 'harm', 'bass'):
        total = sum(song['tracks'][tname][1::2])
        if total != bar_steps: raise ValueError(f"{song['id']}: {tname} sums to {total}, expected {bar_steps}")
    if len(song['tracks']['drums']) != bar_steps: raise ValueError(f"{song['id']}: drums length {len(song['tracks']['drums'])}, expected {bar_steps}")

def export_songs_js(songs):
    path = ROOT / 'songs.js'
    payload = 'window.SONGS = ' + json.dumps(songs, ensure_ascii=False, indent=2) + ';\n'
    path.write_text(payload, encoding='utf-8')

def load_songs():
    songs = []
    for p in sorted(SONGS_DIR.glob('*.json')):
        with open(p, encoding='utf-8') as f: song = json.load(f)
        song['id'] = p.stem  # id is code-derived from filename. JSON id field is ignored.
        validate_song(song); songs.append(song)
    return songs

def main():
    args = sys.argv[1:]; songs = load_songs()
    if '--export-js' in args: export_songs_js(songs); return
    target = next((a for a in args if not a.startswith('-')), None)
    for song in songs:
        if target and not (song['id'] == target or song['id'].startswith(target + '_')): continue
        print(f"Rendering [{song['id']}] {song['name']} by {song['author']} ...")
        mix, peak, dur = render_song(song)
        wavfile.write(OUT_DIR / f"bgm_{song['id']}.wav", SR, (mix * 32767).astype(np.int16))
    export_songs_js(songs)

if __name__ == '__main__': main()
