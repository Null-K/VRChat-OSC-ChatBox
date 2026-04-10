from __future__ import annotations

import re
from typing import Callable, Dict

_VAR_PATTERN = re.compile(r"\{(\w+)\}")


def expand_template(template: str, fns: Dict[str, Callable[[], str]]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1).lower()
        if key in fns:
            try:
                return fns[key]()
            except Exception as e:
                return f"<{key}:err {e}>"
        return m.group(0)

    return _VAR_PATTERN.sub(repl, template)
