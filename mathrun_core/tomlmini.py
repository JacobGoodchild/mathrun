"""Tiny TOML reader.

Uses the standard-library ``tomllib`` when it exists (Python 3.11+). Older
Pythons (Linux Mint 21 ships 3.10) fall back to a small parser that handles
the subset mathrun's own files use: tables, dotted table names, strings,
integers, floats, booleans and (possibly multi-line) arrays of those.
"""

try:  # pragma: no cover - depends on Python version
    import tomllib as _tomllib
except ImportError:  # pragma: no cover
    _tomllib = None


class TomlError(ValueError):
    pass


def loads(text):
    if _tomllib is not None:
        return _tomllib.loads(text)
    return _mini_loads(text)


def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return loads(f.read())


def _strip_comment(line):
    out, in_str, quote, i = [], False, "", 0
    while i < len(line):
        c = line[i]
        if in_str:
            out.append(c)
            if c == "\\" and quote == '"' and i + 1 < len(line):
                out.append(line[i + 1])
                i += 1
            elif c == quote:
                in_str = False
        elif c in "\"'":
            in_str, quote = True, c
            out.append(c)
        elif c == "#":
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).strip()


def _parse_value(s):
    s = s.strip()
    if not s:
        raise TomlError("missing value")
    if s[0] == '"':
        if not s.endswith('"') or len(s) < 2:
            raise TomlError("bad string: %r" % s)
        body = s[1:-1]
        return (body.replace('\\"', '"').replace("\\n", "\n")
                .replace("\\t", "\t").replace("\\\\", "\\"))
    if s[0] == "'":
        if not s.endswith("'") or len(s) < 2:
            raise TomlError("bad string: %r" % s)
        return s[1:-1]
    if s[0] == "[":
        if not s.endswith("]"):
            raise TomlError("bad array: %r" % s)
        return [_parse_value(p) for p in _split_array(s[1:-1])]
    if s == "true":
        return True
    if s == "false":
        return False
    t = s.replace("_", "")
    try:
        return int(t, 0) if t.lower().startswith(("0x", "0o", "0b")) else int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        raise TomlError("cannot parse value: %r" % s)


def _split_array(body):
    parts, depth, cur, in_str, quote = [], 0, [], False, ""
    for c in body:
        if in_str:
            cur.append(c)
            if c == quote:
                in_str = False
            continue
        if c in "\"'":
            in_str, quote = True, c
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p for p in parts if p.strip()]


def _mini_loads(text):
    root = {}
    table = root
    pending = None  # (key, accumulated text) for multi-line arrays
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if pending is not None:
            pending = (pending[0], pending[1] + " " + line)
            if pending[1].count("[") == pending[1].count("]"):
                table[pending[0]] = _parse_value(pending[1])
                pending = None
            continue
        if not line:
            continue
        if line.startswith("["):
            if not line.endswith("]"):
                raise TomlError("bad table header: %r" % raw)
            table = root
            for part in line[1:-1].strip().split("."):
                part = part.strip().strip('"')
                table = table.setdefault(part, {})
            continue
        if "=" not in line:
            raise TomlError("expected key = value: %r" % raw)
        key, val = line.split("=", 1)
        key = key.strip().strip('"')
        val = val.strip()
        if val.startswith("[") and val.count("[") != val.count("]"):
            pending = (key, val)
            continue
        table[key] = _parse_value(val)
    if pending is not None:
        raise TomlError("unterminated array for key %r" % pending[0])
    return root
