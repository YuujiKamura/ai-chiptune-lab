# AI Chiptune Lab

### 🎵 [▶ Live Demo — https://yuujikamura.github.io/ai-chiptune-lab/](https://yuujikamura.github.io/ai-chiptune-lab/)

複数 AI (Claude / Gemini / Codex) に 8-bit NES 風チップチューンを競作させる実験プロジェクト.

同じ制約 (A minor, 150 BPM, 4/4, pulse + triangle + noise の 4ch) のもとで各 AI が JSON で譜面を書く. Python が WAV にレンダし, ブラウザの Web Audio API が同じ JSON からリアルタイム合成する.

## 使い方 (プレイヤー)

上記 Live Demo を開いて **PLAY** ボタンクリック.

- 数字キー `1`〜`9` でバージョン切替
- `Space` で Play/Stop
- チャンネル個別 (P1 Lead / P2 Harm / Triangle Bass / Noise Drum) ミュート可能
- 作者バッジ表示: Claude (橙) / Gemini (青) / Codex (緑) / Human (黄)

## 構成

```
ai-chiptune-demo/
├── index.html              # Web Audio プレイヤー (単一ファイル完結)
├── render.py               # Python+numpy オフラインレンダラ
├── songs.js                # 自動生成 (render.py が songs/*.json を書き出す)
├── songs/                  # SSOT — 各バージョンは独立 JSON
│   ├── v0_original.json
│   ├── v5_codex_compose.json
│   ├── v11_claude_motif.json
│   └── ...
├── out/                    # WAV 出力 (オフライン評価用)
├── analysis.md             # Gemini による v0 音響評価
├── analysis_v2.md          # 同 v2
└── backfill_author.py      # 一回きりの author フィールド追加スクリプト
```

## スキーマ

```jsonc
{
  "id": "v0",                    // render.py がファイル名から自動上書き (無視される)
  "name": "v0 · Original",
  "author": "Claude",            // 必須. "Claude" | "Gemini" | "Codex" | "Human"
  "notes": "作曲意図を書く",
  "bpm": 150,
  "bars": 4,                     // 任意の整数. 各トラックは bars*16 steps 合計必須
  "key": "A minor",
  "progression": "Am - F - G - Am",
  "tracks": {
    "lead":  ["A4", 2, "E4", 1, "rest", 1, ...],   // [note, steps] ペア
    "harm":  [...],
    "bass":  [...],
    "drums": "K.H.S.H.K..KS.HH..."  // 1文字1step: K=kick, S=snare, H=hat, .=rest
  },
  "mix": {
    "master": 0.55,
    "lead_vol": 0.38,
    "lead_duty": 0.25,           // 0.125/0.25/0.5 (pulse wave の duty)
    "lead_wave": "pulse",        // "pulse"|"triangle"|"sawtooth"|"sine"|"fm"|"string"
    "lead_attack": 0.003,        // ADSR attack (秒)
    "lead_release": 0.04,
    "lead_overdrive": 1.0,       // tanh saturation gain
    "harm_vol": 0.28, ...
    "bass_vol": 0.55, ...
    "echo_mix": 0.3,             // DelayNode echo (曲全体)
    "echo_delay": 0.75,          // ビート単位の遅延
    "echo_feedback": 0.4
  }
}
```

### 音名
- `A2` 〜 `G5` 範囲. `#` / `b` で半音上下
- `"rest"` で休符 (音名位置)

### ステップ
- `bpm 150` なら 1 step = 16分音符 = 0.1 秒
- 1 小節 = 16 steps (4/4 の 16分音符グリッド)
- 全トラックの step 合計が `bars * 16` と一致しないと validator が `ValueError`

## 使い方 (編集)

```bash
# 新しいバリエーション追加
cp songs/v0_original.json songs/v15_my_version.json
# 編集 (id フィールドはコード自動, author は必須)

# レンダ + songs.js 再生成
python render.py

# 単一バージョンだけ
python render.py v15
```

ブラウザで `index.html` を Ctrl+F5 リロード → ドロップダウンに v15 が追加されてる.

## AI 競作の経緯

- **v0-v3, v6, v11** — Claude 作曲 (音感なし, 音楽理論ベース + 構造設計)
- **v4, v6_proper_breakbeat, v7-v10, v11_staccato_strike, v12_tears, v13, v14** — Gemini 作曲 (音響ネイティブ, ポエム寄り)
- **v5, v12_codex_compose2** — Codex 作曲 (GPT-5.4, 技巧派)

相互評価ログ: `analysis.md`, `analysis_v2.md` (Gemini が Claude の作品を音響解析 + 譜面批評)

## 技術的な特徴

- **Web Audio API** で NES 風矩形波を `PeriodicWave` で自作 (duty cycle 可変)
- **三角波** はビルトイン `OscillatorNode(type='triangle')`
- **ノイズドラム** は `AudioBufferSourceNode` + `BiquadFilter` で K/S/H を音色分け
- **FM合成** (Chowning) と **Karplus-Strong 弦合成** は Python 側でのみ実装
- scheduler は `currentTime + 0.5s` 先読みで **gapless loop**

## ライセンス

MIT. 自由に改造・再配布可.

---

実験としてスタートし, 途中で Python 側 render.py が Gemini により FM音源・Karplus-Strong・ADSR エンベロープ・エコー・オーバードライブまで拡張され, `pygame` 時代の素朴なチップチューンから半ば合成音源プレイグラウンドに進化した.
