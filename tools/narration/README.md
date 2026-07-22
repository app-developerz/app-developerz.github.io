# Scripture Reader Narration Generator

This tool reads the Scripture Reader KJV JSON and generates one MP3 per verse
using the same Microsoft Edge neural TTS workflow used for the original five
sample verses.

## Default voice

```text
Voice: en-US-GuyNeural
Rate:  -5%
Path:  audio/kjv/{book-slug}/{chapter}/{verse}.mp3
```

Example:

```text
audio/kjv/john/11/35.mp3
```

## Install

Open PowerShell in this folder:

```powershell
py -m pip install --upgrade edge-tts
```

## Test one verse

```powershell
py .\generate_narration.py `
    --reference "John 11:35"
```

Or use the PowerShell wrapper:

```powershell
.\Generate-Narration.ps1 `
    -Reference "John 11:35"
```

## Generate one book

```powershell
.\Generate-Narration.ps1 `
    -Book "John"
```

Multiple books:

```powershell
.\Generate-Narration.ps1 `
    -Book "John","Romans","Ephesians"
```

## Generate the full Bible

```powershell
.\Generate-Narration.ps1 -All
```

The generator is resumable. Existing non-empty MP3 files are skipped, so
rerunning the same command continues from where the previous run stopped.

## Generate directly into the website repository

Copy this generator folder into the website repository under:

```text
tools/narration/
```

From the website repository root:

```powershell
cd .\tools\narration

.\Generate-Narration.ps1 `
    -Book "John" `
    -Output "..\..\audio\kjv"
```

Generated files will appear as:

```text
app-developerz.github.io/
└── audio/
    └── kjv/
        └── john/
            ├── manifest.json
            ├── 1/
            │   ├── 1.mp3
            │   ├── 2.mp3
            │   └── ...
            └── 11/
                └── 35.mp3
```

After pushing the files, John 11:35 will be available at:

```text
https://app-developerz.github.io/audio/kjv/john/11/35.mp3
```

## Local JSON mode

To avoid repeatedly downloading the book JSON, point the Python generator at
the website repository's local `data` directory:

```powershell
py .\generate_narration.py `
    --book "John" `
    --local-data-root "..\..\data" `
    --output "..\..\audio\kjv"
```

## Options

```text
--book "John"          Generate a book; may be repeated
--reference "John 3:16"
--all                  Generate all 66 books
--voice                Default: en-US-GuyNeural
--rate                 Default: -5%
--concurrency          Default: 2
--include-reference    Speak the reference before the text
--overwrite            Replace existing MP3 files
```

Keep concurrency low. The tool defaults to two simultaneous requests and adds
a small delay between successful requests.

## App URL construction

The Roku app does not need a 31,102-entry audio index. It can construct the
audio URL from the current JSON values:

```text
https://app-developerz.github.io/audio/kjv/
    {book.slug}/{chapter.chapter}/{verse.verse}.mp3
```

For example:

```text
https://app-developerz.github.io/audio/kjv/john/11/35.mp3
```

## Local virtual environment

Version 1.1 creates a `.venv` folder beside the scripts and installs
`edge-tts` there. This prevents conflicts between the Python launcher, roaming
user packages, and other Python installations.

Run normally:

```powershell
.\Generate-Narration.ps1 `
    -Reference "Genesis 1:1" `
    -Output "..\..\audio\kjv"
```

To force a clean dependency reinstall:

```powershell
.\Generate-Narration.ps1 `
    -Reference "Genesis 1:1" `
    -Output "..\..\audio\kjv" `
    -ReinstallDependencies
```


## Seamless whole-chapter narration

A Roku Audio playlist starts a new HTTPS request for every verse. On some Roku
devices that creates several seconds of buffering between verses.

After generating all per-verse MP3s for a book, build one continuous MP3 per
chapter:

```powershell
.\Build-Chapter-Narration.ps1 -Book "Genesis"
```

The default output is:

```text
audio/
└── kjv-chapters/
    └── genesis/
        ├── 1.mp3
        ├── 1.json
        ├── 2.mp3
        ├── 2.json
        └── ...
```

The builder trims only leading and trailing silence from each verse, keeps
internal speech pauses, adds a 180 ms transition, and creates timing JSON so the
Roku screen can follow the narration.

Regenerate with a shorter pause:

```powershell
.\Build-Chapter-Narration.ps1 `
    -Book "Genesis" `
    -GapMilliseconds 120 `
    -Overwrite
```


## Python 3.13 chapter-builder fix

Version 1.3 removes `pydub`, `audioop`, and `pyaudioop` entirely.

The chapter builder now:

1. decodes and trims each MP3 with FFmpeg;
2. concatenates 24 kHz mono PCM using Python's built-in `wave` module;
3. records exact verse boundaries from PCM frame counts;
4. encodes the final continuous chapter MP3 with FFmpeg.

Run Genesis:

```powershell
.\Build-Chapter-Narration.ps1 `
    -Book "Genesis" `
    -ReinstallDependencies
```


## FFmpeg temporary-file fix

Version 1.3.1 writes temporary chapter audio as:

```text
1.part.mp3
```

and explicitly passes `-f mp3` to FFmpeg. This fixes the Windows FFmpeg error:

```text
Unable to choose an output format for '1.mp3.part'
```
