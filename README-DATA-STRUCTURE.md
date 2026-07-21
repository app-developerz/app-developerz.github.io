# Scripture Reader hosted data structure

This package is ready to copy into the root of:

```text
app-developerz/app-developerz.github.io
```

## Directory layout

```text
.nojekyll
data/
├── app-config.json
├── version.json
├── index.json
├── manifest.json
├── kjv-flat.json
├── kjv-flat-pretty.json
└── books/
    ├── genesis.json
    ├── exodus.json
    ├── ...
    └── revelation.json
tools/
└── build-bible-data.py
```

## App startup flow

1. Download `data/app-config.json`.
2. Read `indexUrl`.
3. Download the small `data/index.json`.
4. Display the 66 books from the index.
5. Download only the selected book file.
6. Navigate its grouped `chapters` and `verses` arrays.

## Public endpoints

```text
https://app-developerz.github.io/data/app-config.json
https://app-developerz.github.io/data/version.json
https://app-developerz.github.io/data/index.json
https://app-developerz.github.io/data/books/john.json
https://app-developerz.github.io/data/kjv-flat.json
```

## Book file structure

```json
{
  "schemaVersion": 1,
  "dataVersion": "1.0.0",
  "translation": "KJV",
  "book": {
    "order": 43,
    "name": "John",
    "slug": "john",
    "testament": "New",
    "chapterCount": 21,
    "verseCount": 879
  },
  "chapters": [
    {
      "chapter": 1,
      "verseCount": 51,
      "verses": [
        {
          "verse": 1,
          "reference": "John 1:1",
          "text": "In the beginning was the Word..."
        }
      ]
    }
  ]
}
```

## Rebuilding

From the repository root:

```powershell
python .\tools\build-bible-data.py
```

The full compact file remains the source of truth:

```text
data/kjv-flat.json
```

## Validated totals

- 66 books
- 1,189 chapters
- 23,145 Old Testament verses
- 7,957 New Testament verses
- 31,102 total verses
