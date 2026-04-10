"""
占位符注册表，此处列表在运行时会被追加到末尾

在 EXTRA_PLACEHOLDER_CATEGORIES 中追加 (分类名, [(key, 说明, factory), ...])
factory 签名为 Callable[[VarContext], Callable[[], str]]
默认分类见 catalog._default_categories
"""

from __future__ import annotations

from typing import Callable, List, Tuple

from vrc_osc_chatbox.variables.context import VarContext

VarCategoryRow = Tuple[str, str, Callable[[VarContext], Callable[[], str]]]
CategoryDef = Tuple[str, List[VarCategoryRow]]

EXTRA_PLACEHOLDER_CATEGORIES: List[CategoryDef] = []
