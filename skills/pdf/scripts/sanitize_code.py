import re
import html
import sys
from typing import Dict

# ---------- Step 0: restore literal unicode escapes/entities to real chars ----------
_RE_UNICODE_ESC = re.compile(r"(\\u[0-9a-fA-F]{4})|(\\U[0-9a-fA-F]{8})|(\\x[0-9a-fA-F]{2})")

def _restore_escapes(s: str) -> str:
    # HTML entities: &#179; &#x2264; &alpha; ...
    s = html.unescape(s)

    # Literal backslash escapes: "\\u00B3" -> "³"
    def _dec(m: re.Match) -> str:
        esc = m.group(0)
        try:
            if esc.startswith("\\u") or esc.startswith("\\U"):
                return chr(int(esc[2:], 16))
            if esc.startswith("\\x"):
                return chr(int(esc[2:], 16))
        except Exception:
            return esc
        return esc

    return _RE_UNICODE_ESC.sub(_dec, s)

# ---------- Step 1: superscripts/subscripts -> <super>/<sub> ----------
_SUPERSCRIPT_MAP: Dict[str, str] = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-", "⁼": "=", "⁽": "(", "⁾": ")",
    "ⁿ": "n", "ᶦ": "i",
}

_SUBSCRIPT_MAP: Dict[str, str] = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
    "ₐ": "a", "ₑ": "e", "ₕ": "h", "ᵢ": "i", "ⱼ": "j",
    "ₖ": "k", "ₗ": "l", "ₘ": "m", "ₙ": "n", "ₒ": "o",
    "ₚ": "p", "ᵣ": "r", "ₛ": "s", "ₜ": "t", "ᵤ": "u",
    "ᵥ": "v", "ₓ": "x",
}

def _replace_super_sub(s: str) -> str:
    out = []
    for ch in s:
        if ch in _SUPERSCRIPT_MAP:
            out.append(f"<super>{_SUPERSCRIPT_MAP[ch]}</super>")
        elif ch in _SUBSCRIPT_MAP:
            out.append(f"<sub>{_SUBSCRIPT_MAP[ch]}</sub>")
        else:
            out.append(ch)
    return "".join(out)

# ---------- Step 2: symbol fallback for SimHei (protect tags, then replace) ----------
_SYMBOL_FALLBACK: Dict[str, str] = {
    # Currently empty - enable entries as needed for fonts missing specific glyphs
    # "±": "+/-",
    # "×": "*",
    # "÷": "/",
    # "≤": "<=",
    # "≥": ">=",
    # "≠": "!=",
    # "≈": "~=",
    # "∞": "inf",
}

def _fallback_symbols(s: str) -> str:
    # Protect <super>/<sub> tags from being modified
    placeholders = {}
    def _protect_tag(m: re.Match) -> str:
        key = f"@@TAG{len(placeholders)}@@"
        placeholders[key] = m.group(0)
        return key

    protected = re.sub(r"</?super>|</?sub>", _protect_tag, s)

    # Replace symbols
    protected = "".join(_SYMBOL_FALLBACK.get(ch, ch) for ch in protected)

    # Restore tags
    for k, v in placeholders.items():
        protected = protected.replace(k, v)

    return protected

def sanitize_code(text: str) -> str:
    """
    Full sanitization pipeline for PDF generation code.
    - Restore unicode escapes/entities to real characters
    - Replace superscript/subscript unicode with <super>/<sub>
    - Replace other risky symbols with ASCII/text fallbacks
    """
    s = _restore_escapes(text)
    s = _replace_super_sub(s)
    s = _fallback_symbols(s)
    return s

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sanitize_code.py <target_script.py>")
        sys.exit(1)
    target = sys.argv[1]
    with open(target, "r", encoding="utf-8") as f:
        code = f.read()
    sanitized = sanitize_code(code)
    with open(target, "w", encoding="utf-8") as f:
        f.write(sanitized)
    print(f"Sanitized: {target}")