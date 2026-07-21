<div align="center">

# 📖 Scripture Reader TV

### Hosted King James Version Bible data for Roku and web applications

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-2ea44f?style=for-the-badge&logo=github)](https://app-developerz.github.io/)
[![Translation](https://img.shields.io/badge/Translation-KJV-6f42c1?style=for-the-badge)](#dataset)
[![Verses](https://img.shields.io/badge/Verses-31%2C102-blue?style=for-the-badge)](#dataset)
[![Format](https://img.shields.io/badge/Format-JSON-orange?style=for-the-badge&logo=json)](#available-files)

<br>

A lightweight, public JSON source containing the complete **66-book King James Version Bible**, structured for use by the **Scripture Reader Roku app**, websites, mobile apps, and other personal projects.

</div>

---

## 🌐 Live Data

<table>
  <thead>
    <tr>
      <th>File</th>
      <th>Description</th>
      <th>Live URL</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>kjv-flat.json</code></td>
      <td>Compact production version for applications</td>
      <td><a href="https://app-developerz.github.io/data/kjv-flat.json">Open compact JSON</a></td>
    </tr>
    <tr>
      <td><code>kjv-flat-pretty.json</code></td>
      <td>Indented version for reading and development</td>
      <td><a href="https://app-developerz.github.io/data/kjv-flat-pretty.json">Open pretty JSON</a></td>
    </tr>
  </tbody>
</table>

> Applications should normally use the compact `kjv-flat.json` file because it downloads faster and uses less bandwidth.

---

## 📊 Dataset

<table>
  <tbody>
    <tr><td><strong>Translation</strong></td><td>King James Version</td></tr>
    <tr><td><strong>Books</strong></td><td>66</td></tr>
    <tr><td><strong>Chapters</strong></td><td>1,189</td></tr>
    <tr><td><strong>Old Testament verses</strong></td><td>23,145</td></tr>
    <tr><td><strong>New Testament verses</strong></td><td>7,957</td></tr>
    <tr><td><strong>Total verses</strong></td><td>31,102</td></tr>
  </tbody>
</table>

Every verse is stored as one flat JSON object containing its book, chapter, verse number, full reference, testament, and text.

---

## 🧱 JSON Structure

```json
{
  "book": "John",
  "chapter": 11,
  "verse": 35,
  "reference": "John 11:35",
  "testament": "New",
  "text": "Jesus wept."
}
```

The complete file is a JSON array:

```json
[
  {
    "book": "Genesis",
    "chapter": 1,
    "verse": 1,
    "reference": "Genesis 1:1",
    "testament": "Old",
    "text": "In the beginning God created the heaven and the earth."
  }
]
```

---

## 📺 Roku Usage

The data can be downloaded inside a Roku `Task` node using `roUrlTransfer`.

```brightscript
function DownloadBible() as object
    transfer = CreateObject("roUrlTransfer")
    transfer.SetCertificatesFile("common:/certs/ca-bundle.crt")
    transfer.InitClientCertificates()
    transfer.SetUrl("https://app-developerz.github.io/data/kjv-flat.json")

    response = transfer.GetToString()

    if response = invalid or response = ""
        print "Bible download failed"
        return invalid
    end if

    bible = ParseJson(response)

    if bible = invalid
        print "Bible JSON parsing failed"
        return invalid
    end if

    print "Loaded "; bible.Count(); " verses"
    return bible
end function
```

### Find a specific verse

```brightscript
function FindVerse(bible as object, wantedReference as string) as object
    for each verse in bible
        if LCase(verse.reference) = LCase(wantedReference)
            return verse
        end if
    end for

    return invalid
end function
```

Example:

```brightscript
verse = FindVerse(bible, "John 3:16")

if verse <> invalid
    print verse.text
end if
```

---

## 🌐 JavaScript Usage

```javascript
async function loadBible() {
  const response = await fetch(
    "https://app-developerz.github.io/data/kjv-flat.json"
  );

  if (!response.ok) {
    throw new Error(`Bible request failed: ${response.status}`);
  }

  return response.json();
}

const bible = await loadBible();

const verse = bible.find(
  (entry) => entry.reference.toLowerCase() === "john 11:35"
);

console.log(verse?.text);
```

---

## 💻 PowerShell Usage

```powershell
$bible = Invoke-RestMethod `
    -Uri "https://app-developerz.github.io/data/kjv-flat.json"

$verse = $bible |
    Where-Object reference -eq "John 11:35" |
    Select-Object -First 1

$verse.text
```

---

## 📁 Repository Structure

```text
app-developerz.github.io/
├── README.md
└── data/
    ├── kjv-flat.json
    └── kjv-flat-pretty.json
```

---

## ✅ Validation

The generated dataset is validated for:

- 66 canonical books
- 1,189 chapters
- 31,102 total verses
- 23,145 Old Testament verses
- 7,957 New Testament verses
- Unique verse references
- Non-empty verse text
- Canonical book ordering
- Matching `book`, `chapter`, `verse`, and `reference` fields

---

## 🛠️ Intended Uses

This dataset is suitable for:

- Roku scripture-reading applications
- Bible search interfaces
- Daily verse applications
- Websites and progressive web apps
- Mobile applications
- Offline caching
- Scripture display systems
- Personal study tools

---

## 📜 Source and Usage

The included text is based on the **King James Version** dataset distributed by the [`farskipper/kjv`](https://github.com/farskipper/kjv) project.

The King James Version text is generally treated as public domain in the United States. Developers distributing an application internationally should verify any regional requirements that apply to their use.

---

## 👤 Maintainer

<div align="center">

**App Developerz**

[GitHub Profile](https://github.com/app-developerz)  
[Hosted Data](https://app-developerz.github.io/data/kjv-flat.json)

</div>

---

<div align="center">

Built for the <strong>Scripture Reader TV</strong> project.

</div>
