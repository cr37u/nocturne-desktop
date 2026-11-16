"""Qt Linguist workflow for Nocturne.

    python tools/i18n_tool.py update    # extract strings -> nocturne/i18n/nocturne_{ro,en,ru}.ts
    python tools/i18n_tool.py release   # compile .ts -> .qm with pyside6-lrelease
    python tools/i18n_tool.py check     # report untranslated strings (exit 1 if any)

Strings come from ``qsTr()`` in QML and from ``QCoreApplication.translate`` / the small
``_t()``/``tr()`` helpers in Python. Existing translations in the .ts files are kept;
new strings are filled from ``tools/translations_seed.py`` when available.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "nocturne"
I18N = PKG / "i18n"
LANGS = {"ro": "ro_RO", "en": "en_US", "ru": "ru_RU"}
NUMERUS_FORMS = {"ro": 3, "en": 2, "ru": 3}

_STR = r'"((?:[^"\\]|\\.)*)"'
QML_CALL = re.compile(r"qsTr\(\s*" + _STR + r"(\s*,\s*\"[^\"]*\"\s*,)?")
PY_TRANSLATE = re.compile(r"QCoreApplication\.translate\(\s*" + _STR + r"\s*,\s*" + _STR + r"(\s*,\s*None\s*,)?")
PY_HELPER_DEF = re.compile(r"def (_t|tr)\(.*?\).*?QCoreApplication\.translate\(\s*(?:\"([^\"]+)\"|context)", re.S)


def _unescape(s: str) -> str:
    return s.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8") if "\\" in s else s


def extract() -> dict[tuple[str, str], bool]:
    """Return {(context, source): numerus}."""
    found: dict[tuple[str, str], bool] = {}
    for qml in sorted((PKG / "qml").rglob("*.qml")):
        ctx = qml.stem
        for m in QML_CALL.finditer(qml.read_text(encoding="utf-8")):
            key = (ctx, _unescape(m.group(1)))
            found[key] = found.get(key, False) or bool(m.group(2))
    for py in sorted(PKG.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        for m in PY_TRANSLATE.finditer(text):
            if m.group(1) in ("Downloads", "App", "Player", "Tray", "Windows", "Notifications", "Fmt"):
                key = (m.group(1), _unescape(m.group(2)))
                found[key] = found.get(key, False) or bool(m.group(3))
        helper = re.search(r"def _t\([^)]*\)[^:]*:\s*\n\s*return QCoreApplication\.translate\(\"([^\"]+)\"", text)
        if helper:
            ctx = helper.group(1)
            for m in re.finditer(r"\b_t\(\s*" + _STR + r"(\s*,\s*[a-z_]+\s*)?\)", text):
                key = (ctx, _unescape(m.group(1)))
                found[key] = found.get(key, False) or bool(m.group(2))
        for m in re.finditer(r"\btr\(\s*\"Fmt\"\s*,\s*" + _STR + r"(\s*,\s*[^)]+)?\)", text):
            key = ("Fmt", _unescape(m.group(1)))
            found[key] = found.get(key, False) or bool(m.group(2))
    return found


def _load_ts(path: Path) -> dict[tuple[str, str], list[str]]:
    result: dict[tuple[str, str], list[str]] = {}
    if not path.exists():
        return result
    tree = ET.parse(path)
    for ctx in tree.getroot().findall("context"):
        name = ctx.findtext("name") or ""
        for msg in ctx.findall("message"):
            source = msg.findtext("source") or ""
            tr = msg.find("translation")
            if tr is None or tr.get("type") in ("unfinished", "obsolete"):
                continue
            forms = [f.text or "" for f in tr.findall("numerusform")]
            result[(name, source)] = forms if forms else [tr.text or ""]
    return result


def _seed() -> dict[str, dict[tuple[str, str], list[str]]]:
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from translations_seed import SEED  # type: ignore[import-not-found]
    except ImportError:
        return {}
    out: dict[str, dict[tuple[str, str], list[str]]] = {lang: {} for lang in LANGS}
    for key, per_lang in SEED.items():
        ctx, source = key if isinstance(key, tuple) else ("*", key)
        for lang, value in per_lang.items():
            out[lang][(ctx, source)] = value if isinstance(value, list) else [value]
    return out


def _lookup(table: dict[tuple[str, str], list[str]], ctx: str, source: str) -> list[str] | None:
    return table.get((ctx, source)) or table.get(("*", source))


def update() -> int:
    strings = extract()
    seed = _seed()
    I18N.mkdir(parents=True, exist_ok=True)
    missing_total = 0
    for lang, locale in LANGS.items():
        path = I18N / f"nocturne_{lang}.ts"
        existing = _load_ts(path)
        root = ET.Element("TS", version="2.1", language=locale)
        missing = 0
        for ctx_name in sorted({c for c, _ in strings}):
            ctx_el = ET.SubElement(root, "context")
            ET.SubElement(ctx_el, "name").text = ctx_name
            for (c, source), numerus in sorted(strings.items()):
                if c != ctx_name:
                    continue
                msg = ET.SubElement(ctx_el, "message")
                if numerus:
                    msg.set("numerus", "yes")
                ET.SubElement(msg, "source").text = source
                value = existing.get((c, source)) or _lookup(seed.get(lang, {}), c, source)
                if value is None and lang == "en" and not numerus:
                    value = [source]
                tr_el = ET.SubElement(msg, "translation")
                if value is None:
                    tr_el.set("type", "unfinished")
                    missing += 1
                    if numerus:
                        for _ in range(NUMERUS_FORMS[lang]):
                            ET.SubElement(tr_el, "numerusform")
                elif numerus:
                    forms = list(value) + [value[-1]] * (NUMERUS_FORMS[lang] - len(value))
                    for form in forms[: NUMERUS_FORMS[lang]]:
                        ET.SubElement(tr_el, "numerusform").text = form
                else:
                    tr_el.text = value[0]
        ET.indent(root)
        xml = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + ET.tostring(root, encoding="unicode") + "\n"
        path.write_text(xml, encoding="utf-8")
        print(f"{path.name}: {len(strings)} strings, {missing} untranslated")
        missing_total += missing
    return 1 if missing_total else 0


def _lrelease() -> list[str]:
    exe = shutil.which("pyside6-lrelease")
    if exe:
        return [exe]
    candidate = Path(sys.executable).with_name("pyside6-lrelease.exe")
    if candidate.exists():
        return [str(candidate)]
    return [sys.executable, "-m", "PySide6.scripts.pyside_tool", "lrelease"]


def release() -> int:
    code = 0
    for lang in LANGS:
        ts = I18N / f"nocturne_{lang}.ts"
        qm = I18N / f"nocturne_{lang}.qm"
        result = subprocess.run([*_lrelease(), str(ts), "-qm", str(qm)], capture_output=True, text=True)
        print(result.stdout.strip() or result.stderr.strip())
        code |= result.returncode
    return code


def check() -> int:
    bad = 0
    for lang in LANGS:
        tree = ET.parse(I18N / f"nocturne_{lang}.ts")
        for msg in tree.getroot().iter("message"):
            tr = msg.find("translation")
            if tr is not None and tr.get("type") == "unfinished":
                bad += 1
                print(f"[{lang}] {msg.findtext('source')}")
    return 1 if bad else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "update"
    if cmd == "list":
        for (ctx, src), num in sorted(extract().items()):
            print(f"{ctx}\t{'N' if num else '-'}\t{src}")
        sys.exit(0)
    sys.exit({"update": update, "release": release, "check": check}[cmd]())
