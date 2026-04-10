from __future__ import annotations

import platform
import tkinter as tk
from typing import Any, Dict

import psutil
import ttkbootstrap as ttk
from ttkbootstrap.constants import PRIMARY, SECONDARY
from ttkbootstrap.dialogs import Messagebox
from tkinter import scrolledtext

from pythonosc.udp_client import SimpleUDPClient

from vrc_osc_chatbox.constants import CHATBOX_MAX_LEN, DEFAULT_TEMPLATE, METADATA
from vrc_osc_chatbox.config import default_config_dict, load_config_dict, save_config_dict
from vrc_osc_chatbox.paths import config_path, resolve_icon_path
from vrc_osc_chatbox.osc import send_chatbox
from vrc_osc_chatbox.variables import (
    VarContext,
    build_placeholder_categories,
    build_var_fns,
    expand_template,
)


def _tk_text_theme_kw(co: object) -> dict:
    return {
        "bg": co.bg,
        "fg": co.fg,
        "insertbackground": co.primary,
        "selectbackground": co.selectbg,
        "selectforeground": co.selectfg,
        "relief": tk.FLAT,
        "highlightthickness": 0,
        "borderwidth": 0,
    }


class App(ttk.Window):
    def __init__(self) -> None:
        super().__init__(themename=METADATA.theme, title=METADATA.app_title)
        self.geometry("1040x640")
        self.minsize(1040, 590)
        self._apply_window_icon()

        self._ctx = VarContext()
        self._var_fns = build_var_fns(self._ctx)
        self._after_id: str | None = None
        self._running = False

        co = self.style.colors

        main = ttk.Frame(self, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        body = ttk.Frame(main)
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, minsize=360, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_card = ttk.Labelframe(body, text="占位符变量", padding=(10, 8, 10, 10))
        left_card.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 12))

        ttk.Label(left_card, text="双击或选中后点击按钮插入").pack(anchor=tk.W, pady=(0, 6))

        tree_frame = ttk.Frame(left_card)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        cols = ("desc",)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="tree headings",
            height=22,
            selectmode="browse",
        )
        self.tree.heading("#0", text="变量")
        self.tree.column("#0", width=180, minwidth=120)
        self.tree.heading("desc", text="说明")
        self.tree.column("desc", width=260, minwidth=100)
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree_key: Dict[str, str] = {}

        for cat_name, rows in build_placeholder_categories(self._ctx):
            pid = self.tree.insert("", tk.END, text=cat_name, open=True)
            for key, desc, _ in rows:
                iid = self.tree.insert(pid, tk.END, text=f"{{{key}}}", values=(desc,))
                self._tree_key[iid] = key

        self.tree.bind("<Double-1>", self._on_tree_double)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        btn_row = ttk.Frame(left_card)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="插入选中变量", command=self._insert_selected_var, bootstyle=PRIMARY).pack(
            fill=tk.X, pady=(0, 4)
        )
        self.lbl_sel_hint = ttk.Label(btn_row, text="仅子节点可插入")
        self.lbl_sel_hint.pack(anchor=tk.W)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky=tk.NSEW)

        net_card = ttk.Labelframe(right, text="OSC 设置", padding=(12, 10, 12, 10))
        net_card.pack(fill=tk.X, pady=(0, 10))
        row1 = ttk.Frame(net_card)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="IP").pack(side=tk.LEFT)
        self.entry_host = ttk.Entry(row1, width=16)
        self.entry_host.insert(0, "127.0.0.1")
        self.entry_host.pack(side=tk.LEFT, padx=(8, 16))
        ttk.Label(row1, text="端口").pack(side=tk.LEFT)
        self.entry_port = ttk.Entry(row1, width=8)
        self.entry_port.insert(0, "9000")
        self.entry_port.pack(side=tk.LEFT, padx=(8, 20))
        self.var_sound = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="发送时播放提示音", variable=self.var_sound, bootstyle="round-toggle").pack(
            side=tk.LEFT
        )

        tpl_card = ttk.Labelframe(right, text="消息模板", padding=(12, 10, 12, 10))
        tpl_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.txt_template = scrolledtext.ScrolledText(
            tpl_card,
            height=10,
            wrap=tk.WORD,
            **_tk_text_theme_kw(co),
        )
        self.txt_template.pack(fill=tk.BOTH, expand=True)

        prev_card = ttk.Labelframe(right, text="预览", padding=(12, 10, 12, 10))
        prev_card.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        self.preview = scrolledtext.ScrolledText(
            prev_card,
            height=5,
            wrap=tk.WORD,
            state=tk.DISABLED,
            **_tk_text_theme_kw(co),
        )
        try:
            self.preview.configure(disabledforeground=co.secondary)
        except tk.TclError:
            pass
        self.preview.pack(fill=tk.BOTH, expand=True)

        act = ttk.Labelframe(right, text="操作", padding=(12, 10, 12, 10))
        act.pack(fill=tk.X)
        ttk.Button(act, text="预览", command=self._on_preview, bootstyle=SECONDARY).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(act, text="发送一次", command=self._on_send_once, bootstyle=PRIMARY).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(act, text="保存配置", command=self._save_config, bootstyle=SECONDARY).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(act, text="定时 (秒)").pack(side=tk.LEFT, padx=(12, 4))
        self.spin_interval = ttk.Spinbox(act, from_=0.5, to=3600.0, increment=0.5, width=7)
        self.spin_interval.delete(0, tk.END)
        self.spin_interval.insert(0, "3")
        self.spin_interval.pack(side=tk.LEFT)
        self.btn_timer = ttk.Button(act, text="开始定时发送", command=self._toggle_timer, bootstyle=SECONDARY)
        self.btn_timer.pack(side=tk.LEFT, padx=8)

        status_row = ttk.Frame(right)
        status_row.pack(fill=tk.X, pady=(8, 0))
        self.lbl_status = ttk.Label(status_row, text="就绪")
        self.lbl_status.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, expand=True)
        self.lbl_version = ttk.Label(
            status_row,
            text=f"v{METADATA.version} · {METADATA.author}",
            bootstyle=SECONDARY,
            cursor="hand2",
        )
        self.lbl_version.pack(side=tk.RIGHT)
        self.lbl_version.bind("<Button-1>", lambda _e: self._on_about_author())

        self._apply_config(load_config_dict())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, lambda: psutil.cpu_percent(interval=0.2))

    def _apply_window_icon(self) -> None:
        if platform.system() != "Windows":
            return
        p = resolve_icon_path()
        if not p:
            return
        try:
            icon_path = str(p.resolve())
            self.iconbitmap(icon_path)
            self.iconbitmap(default=icon_path)
        except tk.TclError:
            pass

    def _on_about_author(self) -> None:
        Messagebox.show_info(title=METADATA.about_title, message=METADATA.about_message())

    def _apply_config(self, cfg: Dict[str, Any]) -> None:
        self.entry_host.delete(0, tk.END)
        self.entry_host.insert(0, str(cfg.get("host", "127.0.0.1")))
        self.entry_port.delete(0, tk.END)
        self.entry_port.insert(0, str(int(cfg.get("port", 9000))))
        self.var_sound.set(bool(cfg.get("sound", False)))
        self.txt_template.delete("1.0", tk.END)
        self.txt_template.insert(tk.END, str(cfg.get("template", DEFAULT_TEMPLATE)))
        self.spin_interval.delete(0, tk.END)
        self.spin_interval.insert(0, str(cfg.get("interval", 3.0)))

    def _save_config(self) -> None:
        try:
            port = int(self.entry_port.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError
            interval = float(self.spin_interval.get())
            if interval < 0.2:
                raise ValueError
        except ValueError:
            Messagebox.show_error(
                title="错误",
                message="端口须为 1–65535 的整数，定时秒数须为 ≥3.0 的数字",
            )
            return
        data = {
            "template": self.txt_template.get("1.0", tk.END).rstrip("\n"),
            "host": self.entry_host.get().strip() or "127.0.0.1",
            "port": port,
            "sound": bool(self.var_sound.get()),
            "interval": interval,
        }
        try:
            save_config_dict(data)
        except OSError as e:
            Messagebox.show_error(title="保存失败", message=str(e))
            return
        self.lbl_status.configure(text=f"配置已保存: {config_path()}")

    def _persist_config_silent(self) -> None:
        d = default_config_dict()
        tpl = self.txt_template.get("1.0", tk.END).rstrip("\n")
        host = self.entry_host.get().strip() or "127.0.0.1"
        try:
            port = int(self.entry_port.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            port = int(d["port"])
        try:
            interval = float(self.spin_interval.get())
            if interval < 0.2:
                raise ValueError
        except ValueError:
            interval = float(d["interval"])
        data = {
            "template": tpl,
            "host": host,
            "port": port,
            "sound": bool(self.var_sound.get()),
            "interval": interval,
        }
        try:
            save_config_dict(data)
        except OSError:
            pass

    def _insert_text(self, s: str) -> None:
        self.txt_template.insert(tk.INSERT, s)
        self.txt_template.focus_set()

    def _on_tree_select(self, _evt: tk.Event | None = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid in self._tree_key:
            self.lbl_sel_hint.configure(text=f"将插入: {{{self._tree_key[iid]}}}")
        else:
            self.lbl_sel_hint.configure(text="请选择具体变量")

    def _on_tree_double(self, _evt: tk.Event) -> None:
        self._insert_selected_var()

    def _insert_selected_var(self) -> None:
        sel = self.tree.selection()
        if not sel:
            Messagebox.show_info(title="提示", message="请先在左侧选中一个变量")
            return
        iid = sel[0]
        key = self._tree_key.get(iid)
        if not key:
            Messagebox.show_info(title="提示", message="请展开分类并选择具体变量")
            return
        self._insert_text("{" + key + "}")

    def _get_client(self) -> SimpleUDPClient | None:
        host = self.entry_host.get().strip() or "127.0.0.1"
        try:
            port = int(self.entry_port.get().strip())
        except ValueError:
            Messagebox.show_error(title="错误", message="端口必须是数字，请修改后重试")
            return None
        if not 1 <= port <= 65535:
            Messagebox.show_error(title="错误", message="端口范围 1–65535 ，请修改后重试")
            return None
        return SimpleUDPClient(host, port)

    def _sound_on(self) -> bool:
        return bool(self.var_sound.get())

    def _on_preview(self) -> None:
        self._refresh_var_fns()
        raw = self.txt_template.get("1.0", tk.END).rstrip("\n")
        out = expand_template(raw, self._var_fns)
        self.preview.configure(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, out)
        if len(out) > CHATBOX_MAX_LEN:
            self.preview.insert(tk.END, f"\n\n[长度 {len(out)}，限制 {CHATBOX_MAX_LEN}，发送时超出部分将被截断]")
        self.preview.configure(state=tk.DISABLED)
        self.lbl_status.configure(text=f"已预览: {len(out)} 字符")

    def _refresh_var_fns(self) -> None:
        self._var_fns = build_var_fns(self._ctx)

    def _on_send_once(self) -> None:
        client = self._get_client()
        if not client:
            return
        self._refresh_var_fns()
        raw = self.txt_template.get("1.0", tk.END).rstrip("\n")
        text = expand_template(raw, self._var_fns)
        if len(text) > CHATBOX_MAX_LEN:
            text = text[:CHATBOX_MAX_LEN]
        try:
            send_chatbox(client, text, self._sound_on())
            self.lbl_status.configure(text=f"已发送: {len(text)} 字符")
        except OSError as e:
            Messagebox.show_error(title="发送失败", message=str(e))
            self.lbl_status.configure(text="发送失败")

    def _cancel_after_timer(self) -> None:
        if self._after_id is None:
            return
        try:
            self.after_cancel(self._after_id)
        except tk.TclError:
            pass
        self._after_id = None

    def _toggle_timer(self) -> None:
        if self._running:
            self._running = False
            self._cancel_after_timer()
            self.btn_timer.configure(text="开始定时发送")
            self.lbl_status.configure(text="定时已停止")
            return
        try:
            interval = float(self.spin_interval.get())
        except ValueError:
            Messagebox.show_error(title="错误", message="定时秒数无效，请修改后重试")
            return
        if interval < 3.0:
            Messagebox.show_warning(title="提示", message="间隔过短可能导致风控，建议 ≥3 秒")
        self._running = True
        self.btn_timer.configure(text="停止定时发送")
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        if not self._running:
            return
        try:
            interval = float(self.spin_interval.get())
        except ValueError:
            interval = 2.0
        interval_ms = int(max(0.2, interval) * 1000)
        self._after_id = self.after(interval_ms, self._tick_send)

    def _tick_send(self) -> None:
        self._after_id = None
        if not self._running:
            return
        client = self._get_client()
        if not client:
            self._running = False
            self._cancel_after_timer()
            self.btn_timer.configure(text="开始定时发送")
            self.lbl_status.configure(text="定时已停止，请检查 OSC 配置是否正确")
            return
        self._refresh_var_fns()
        raw = self.txt_template.get("1.0", tk.END).rstrip("\n")
        text = expand_template(raw, self._var_fns)
        if len(text) > CHATBOX_MAX_LEN:
            text = text[:CHATBOX_MAX_LEN]
        try:
            send_chatbox(client, text, self._sound_on())
            self.lbl_status.configure(text=f"定时发送中: {len(text)} 字符")
        except OSError as e:
            self.lbl_status.configure(text=f"发送失败: {e}")
        self._schedule_tick()

    def _on_close(self) -> None:
        self._running = False
        self._cancel_after_timer()
        self._persist_config_silent()
        self.destroy()
