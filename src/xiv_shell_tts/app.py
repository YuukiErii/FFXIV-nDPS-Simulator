import csv
import json
import os
import re
import sys
import traceback
import argparse
from collections import Counter
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk
import tkinter as tk


APP_NAME = "XIV in the Shell TTS Converter"
DEFAULT_MAP_PATH = Path("data") / "ff14_job_skill_en_cn_map.json"
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "cp936")


SPECIAL_ALIASES = {
    "Arms Length": "亲疏自行",
    "Arm's Length": "亲疏自行",
    "Tincture": "爆发药",
    "Grade 4 Gemdraught of Strength": "爆发药",
    "Grade 5 Gemdraught of Strength": "爆发药",
    "Grade 4 Gemdraught of Dexterity": "爆发药",
    "Grade 5 Gemdraught of Dexterity": "爆发药",
    "Grade 4 Gemdraught of Intelligence": "爆发药",
    "Grade 5 Gemdraught of Intelligence": "爆发药",
    "Grade 4 Gemdraught of Mind": "爆发药",
    "Grade 5 Gemdraught of Mind": "爆发药",
    "Pop Tengentsu": "天眼通生效",
}

ROMAN_TO_ARABIC = {
    "X": "10",
    "IX": "9",
    "VIII": "8",
    "VII": "7",
    "VI": "6",
    "V": "5",
    "IV": "4",
    "III": "3",
    "II": "2",
    "I": "1",
}


def resource_path(relative_path):
    rel = Path(relative_path)
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / rel

    source_dir = Path(__file__).resolve().parent
    for base in (Path.cwd(), source_dir, source_dir.parent):
        candidate = base / rel
        if candidate.exists():
            return candidate
    return source_dir / rel


def contains_cjk(text):
    return any("\u3400" <= ch <= "\u9fff" for ch in text)


def normalize_name(text):
    text = text.lower().strip()
    text = text.replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", text)


def roman_variants(name):
    variants = set()
    for roman, arabic in ROMAN_TO_ARABIC.items():
        variants.add(re.sub(rf"\b{roman}\b", arabic, name))
    return {item for item in variants if item != name}


def format_time(value):
    text = str(value).strip()
    if not text:
        return text
    try:
        return str(float(text))
    except ValueError:
        return text


class SkillTranslator:
    def __init__(self, map_path=None):
        self.map_path = Path(map_path) if map_path else resource_path(DEFAULT_MAP_PATH)
        with open(self.map_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.en_to_cn = dict(payload["en_to_cn"])
        self.cn_to_en = dict(payload.get("cn_to_en", {}))
        self.en_to_cn.update(SPECIAL_ALIASES)
        self.normalized = {}
        self._build_aliases()

    def _add_alias(self, alias, value):
        if not alias:
            return
        self.en_to_cn.setdefault(alias, value)
        self.normalized.setdefault(normalize_name(alias), value)

    def _build_aliases(self):
        for en_name, cn_name in list(self.en_to_cn.items()):
            self.normalized.setdefault(normalize_name(en_name), cn_name)
            for alias in roman_variants(en_name):
                self._add_alias(alias, cn_name)

    def translate(self, raw_name):
        name = str(raw_name).strip()
        if not name:
            return name, False
        if name in self.cn_to_en or contains_cjk(name):
            return name, True
        if name in self.en_to_cn:
            return self.en_to_cn[name], True
        normalized = normalize_name(name)
        if normalized in self.normalized:
            return self.normalized[normalized], True
        parenthetical_base = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        if parenthetical_base and parenthetical_base != name:
            if parenthetical_base in self.en_to_cn:
                return self.en_to_cn[parenthetical_base], True
            normalized_base = normalize_name(parenthetical_base)
            if normalized_base in self.normalized:
                return self.normalized[normalized_base], True
        return name, False


def read_csv_with_fallback(path):
    last_error = None
    for encoding in TEXT_ENCODINGS:
        try:
            with open(path, "r", encoding=encoding, newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                rows = list(csv.reader(f, dialect))
            return rows, encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeError(f"无法识别 CSV 编码: {last_error}")


def read_text_lines_with_fallback(path):
    last_error = None
    for encoding in TEXT_ENCODINGS:
        try:
            with open(path, "r", encoding=encoding, newline="") as f:
                return f.readlines(), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeError(f"无法识别文本编码: {last_error}")


def get_time_from_timeline_line(line_str):
    text = line_str.strip()
    if not text:
        return None
    match = re.match(r"^#?\s*(-?\d+\.?\d*)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def default_merged_output_path(skillline_path):
    path = Path(skillline_path)
    stem = path.stem
    if stem.lower().endswith("_skillline"):
        stem = stem[: -len("_skillline")]
    return path.with_name(f"{stem}_Merged.txt")


def merge_timeline_files(timeline_path, skillline_path, output_path=None):
    output_path = Path(output_path) if output_path else default_merged_output_path(skillline_path)
    all_lines = []
    sources = []

    for label, path in (("timeline", Path(timeline_path)), ("skillline", Path(skillline_path))):
        if not path.exists():
            raise FileNotFoundError(f"找不到文件：{path}")
        lines, encoding = read_text_lines_with_fallback(path)
        accepted = 0
        for line in lines:
            time_value = get_time_from_timeline_line(line)
            if time_value is not None:
                all_lines.append((time_value, line))
                accepted += 1
            elif line.strip():
                all_lines.append((float("-inf"), line))
                accepted += 1
        sources.append({"label": label, "path": str(path), "encoding": encoding, "rows": accepted})

    if not all_lines:
        raise ValueError("副本时间轴和技能轴都没有可合并的行。")

    all_lines.sort(key=lambda item: item[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        for _, line in all_lines:
            f.write(line)

    return {
        "rows": len(all_lines),
        "sources": sources,
        "preview": [line.rstrip("\r\n") for _, line in all_lines[:20]],
        "output": str(output_path),
    }


def looks_like_header(row):
    lower = [cell.strip().lower() for cell in row]
    return "time" in lower and any(name in lower for name in ("action", "skill", "skillname", "name"))


def detect_columns(headers):
    lower_to_header = {header.strip().lower(): header for header in headers}
    time_col = lower_to_header.get("time") or lower_to_header.get("timestamp") or lower_to_header.get("start")
    action_col = (
        lower_to_header.get("action")
        or lower_to_header.get("skill")
        or lower_to_header.get("skillname")
        or lower_to_header.get("name")
    )
    if not time_col or not action_col:
        raise ValueError("CSV 中需要能识别出 time 和 action/skill/name 列。")
    return time_col, action_col


def load_axis(path):
    raw_rows, encoding = read_csv_with_fallback(path)
    raw_rows = [row for row in raw_rows if any(cell.strip() for cell in row)]
    if not raw_rows:
        raise ValueError("CSV 是空的。")

    if looks_like_header(raw_rows[0]):
        headers = [cell.strip() for cell in raw_rows[0]]
        data_rows = raw_rows[1:]
    else:
        max_len = max(len(row) for row in raw_rows)
        headers = ["time", "action"] + [f"extra_{i}" for i in range(3, max_len + 1)]
        data_rows = raw_rows

    normalized_rows = []
    for row in data_rows:
        padded = row + [""] * (len(headers) - len(row))
        normalized_rows.append(dict(zip(headers, padded)))

    time_col, action_col = detect_columns(headers)
    return headers, normalized_rows, time_col, action_col, encoding


def convert_axis(input_path, output_txt_path, output_csv_path=None, translator=None):
    translator = translator or SkillTranslator()
    headers, rows, time_col, action_col, encoding = load_axis(input_path)

    output_lines = []
    translated_rows = []
    missing = Counter()
    translated_count = 0

    for row in rows:
        time_text = format_time(row.get(time_col, ""))
        raw_action = str(row.get(action_col, "")).strip()
        if not time_text or not raw_action:
            continue

        skill, ok = translator.translate(raw_action)
        if ok:
            translated_count += 1
        else:
            missing[raw_action] += 1

        output_lines.append(f'{time_text} "<{skill}>~" tts "{skill}"')
        new_row = dict(row)
        new_row[action_col] = skill
        if time_col in new_row:
            new_row[time_col] = time_text
        translated_rows.append(new_row)

    if not output_lines:
        raise ValueError("没有可输出的技能行。")

    output_txt_path = Path(output_txt_path)
    output_txt_path.parent.mkdir(parents=True, exist_ok=True)
    output_txt_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    if output_csv_path:
        output_csv_path = Path(output_csv_path)
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(translated_rows)

    return {
        "input_encoding": encoding,
        "rows": len(output_lines),
        "translated": translated_count,
        "untranslated": sum(missing.values()),
        "missing": missing,
        "preview": output_lines[:20],
        "output_txt": str(output_txt_path),
        "output_csv": str(output_csv_path) if output_csv_path else "",
    }


class TTSConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("980x760")
        self.root.minsize(900, 650)

        self.colors = {
            "bg": "#141821",
            "panel": "#1d2430",
            "panel2": "#252e3d",
            "fg": "#eef2f8",
            "muted": "#9aa8bc",
            "accent": "#6ee7b7",
            "accent2": "#8ab4ff",
            "danger": "#ff8c8c",
        }

        self.input_path = StringVar()
        self.output_path = StringVar()
        self.timeline_path = StringVar()
        self.merged_output_path = StringVar()
        self.write_cn_csv = BooleanVar(value=True)
        self.status = StringVar(value="Ready")
        self.translator = None

        self._configure_style()
        self._build_ui()
        self._load_translator()

    def _configure_style(self):
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 10))
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"])
        style.configure("Muted.TLabel", foreground=self.colors["muted"])
        style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"), foreground=self.colors["fg"])
        style.configure("Accent.TLabel", foreground=self.colors["accent"])
        style.configure("TButton", padding=(14, 8), background=self.colors["panel2"], foreground=self.colors["fg"])
        style.map("TButton", background=[("active", "#334155")])
        style.configure("Primary.TButton", background="#2563eb", foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])
        style.configure("TCheckbutton", background=self.colors["panel"], foreground=self.colors["fg"])
        style.map("TCheckbutton", background=[("active", self.colors["panel"])])
        style.configure("Horizontal.TProgressbar", troughcolor=self.colors["panel"], background=self.colors["accent"])

    def _panel(self, parent, **pack):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        frame.pack(**pack)
        return frame

    def _build_ui(self):
        shell = ttk.Frame(self.root, padding=22)
        shell.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(shell)
        header.pack(fill=tk.X, pady=(0, 16))
        ttk.Label(header, text="XIV in the Shell TTS", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="CSV → 中文技能名 → TTS timeline", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))

        files = self._panel(shell, fill=tk.X, pady=(0, 14))
        self._path_row(files, "输入轴", self.input_path, self.choose_input)
        self._path_row(files, "输出 TXT", self.output_path, self.choose_output)
        self._path_row(files, "副本时间轴", self.timeline_path, self.choose_timeline)
        self._path_row(files, "合并输出", self.merged_output_path, self.choose_merged_output)

        options = ttk.Frame(files, style="Panel.TFrame")
        options.pack(fill=tk.X, pady=(12, 0))
        ttk.Checkbutton(options, text="同时输出翻译后 CSV", variable=self.write_cn_csv).pack(side=tk.LEFT)
        ttk.Button(options, text="打开输出目录", command=self.open_output_dir).pack(side=tk.RIGHT)
        ttk.Button(options, text="转换", style="Primary.TButton", command=self.convert).pack(side=tk.RIGHT, padx=(0, 10))

        body = ttk.Frame(shell)
        body.pack(fill=tk.BOTH, expand=True)

        left = self._panel(body, side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))
        ttk.Label(left, text="预览", style="Accent.TLabel").pack(anchor="w")
        self.preview = tk.Text(
            left,
            bg="#0f172a",
            fg=self.colors["fg"],
            insertbackground=self.colors["fg"],
            relief="flat",
            wrap="none",
            font=("Consolas", 10),
            height=18,
        )
        self.preview.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        right = self._panel(body, side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(7, 0))
        right.configure(width=310)
        ttk.Label(right, text="转换状态", style="Accent.TLabel").pack(anchor="w")
        self.summary = tk.Text(
            right,
            bg=self.colors["panel"],
            fg=self.colors["fg"],
            relief="flat",
            wrap="word",
            font=("Segoe UI", 10),
            width=34,
            height=18,
        )
        self.summary.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        footer = ttk.Frame(shell)
        footer.pack(fill=tk.X, pady=(14, 0))
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X)
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

    def _path_row(self, parent, label, variable, command):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill=tk.X, pady=5)
        ttk.Label(row, text=label, background=self.colors["panel"], width=10).pack(side=tk.LEFT)
        entry = tk.Entry(
            row,
            textvariable=variable,
            bg="#111827",
            fg=self.colors["fg"],
            insertbackground=self.colors["fg"],
            relief="flat",
            font=("Segoe UI", 10),
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(8, 8))
        ttk.Button(row, text="浏览", command=command).pack(side=tk.LEFT)

    def _load_translator(self):
        try:
            self.translator = SkillTranslator()
            self._write_summary(f"Loaded mapping:\n{self.translator.map_path}\n\nEntries: {len(self.translator.en_to_cn)}")
            self.status.set("Ready")
        except Exception as exc:
            self.status.set("Mapping load failed")
            self._write_summary(str(exc))
            messagebox.showerror(APP_NAME, f"加载中英文对照表失败：\n{exc}")

    def _set_output_path(self, path, force_merged=False):
        previous_output = self.output_path.get()
        previous_merged_default = str(default_merged_output_path(previous_output)) if previous_output else ""
        self.output_path.set(str(path))
        if force_merged or not self.merged_output_path.get() or self.merged_output_path.get() == previous_merged_default:
            self.merged_output_path.set(str(default_merged_output_path(path)))

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="选择 XIV in the Shell CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.input_path.set(path)
        default_out = Path(path).with_name(f"{Path(path).stem}_skillline.txt")
        self._set_output_path(default_out, force_merged=True)
        self.refresh_preview()

    def choose_output(self):
        initial = self.output_path.get() or (
            str(Path(self.input_path.get()).with_name(f"{Path(self.input_path.get()).stem}_skillline.txt"))
            if self.input_path.get()
            else ""
        )
        path = filedialog.asksaveasfilename(
            title="保存 TTS TXT",
            initialfile=Path(initial).name if initial else "skillline.txt",
            initialdir=str(Path(initial).parent) if initial else os.getcwd(),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._set_output_path(path)

    def choose_timeline(self):
        path = filedialog.askopenfilename(
            title="选择副本时间轴 TXT",
            filetypes=[
                ("Timeline/Text files", "*.txt *.timeline *.log"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self.timeline_path.set(path)
        if self.output_path.get() and not self.merged_output_path.get():
            self.merged_output_path.set(str(default_merged_output_path(self.output_path.get())))

    def choose_merged_output(self):
        initial = self.merged_output_path.get()
        if not initial and self.output_path.get():
            initial = str(default_merged_output_path(self.output_path.get()))
        elif not initial and self.timeline_path.get():
            timeline = Path(self.timeline_path.get())
            initial = str(timeline.with_name(f"{timeline.stem}_Merged.txt"))
        path = filedialog.asksaveasfilename(
            title="保存合并 TXT",
            initialfile=Path(initial).name if initial else "merged.txt",
            initialdir=str(Path(initial).parent) if initial else os.getcwd(),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.merged_output_path.set(path)

    def translated_csv_path(self):
        if not self.input_path.get():
            return ""
        output_dir = Path(self.output_path.get()).parent if self.output_path.get() else Path(self.input_path.get()).parent
        src = Path(self.input_path.get())
        return str(output_dir / f"{src.stem}CN.csv")

    def refresh_preview(self):
        if not self.input_path.get() or not self.translator:
            return
        try:
            headers, rows, time_col, action_col, encoding = load_axis(self.input_path.get())
            lines = []
            missing = []
            for row in rows[:14]:
                skill, ok = self.translator.translate(row.get(action_col, ""))
                if not ok:
                    missing.append(row.get(action_col, ""))
                lines.append(f'{format_time(row.get(time_col, ""))} "<{skill}>~" tts "{skill}"')
            self._write_preview("\n".join(lines))
            self._write_summary(
                f"Input encoding: {encoding}\n"
                f"Rows detected: {len(rows)}\n"
                f"Time column: {time_col}\n"
                f"Action column: {action_col}\n"
                f"Preview untranslated: {len(missing)}"
            )
            self.status.set("Preview ready")
        except Exception as exc:
            self._write_preview("")
            self._write_summary(str(exc))
            self.status.set("Preview failed")

    def convert(self):
        if not self.input_path.get():
            messagebox.showwarning(APP_NAME, "请先选择输入 CSV。")
            return
        if not self.output_path.get():
            messagebox.showwarning(APP_NAME, "请先选择输出 TXT。")
            return
        if not self.translator:
            messagebox.showerror(APP_NAME, "中英文对照表没有加载成功。")
            return

        try:
            self.progress["value"] = 20
            self.root.update_idletasks()
            csv_path = self.translated_csv_path() if self.write_cn_csv.get() else None
            result = convert_axis(self.input_path.get(), self.output_path.get(), csv_path, self.translator)
            self.progress["value"] = 65
            self.root.update_idletasks()

            merge_result = None
            if self.timeline_path.get():
                merged_path = self.merged_output_path.get() or str(default_merged_output_path(result["output_txt"]))
                self.merged_output_path.set(merged_path)
                merge_result = merge_timeline_files(self.timeline_path.get(), result["output_txt"], merged_path)

            self.progress["value"] = 100
            preview_lines = merge_result["preview"] if merge_result else result["preview"]
            self._write_preview("\n".join(preview_lines))
            missing_lines = "\n".join(f"- {name} x{count}" for name, count in result["missing"].most_common(15))
            if not missing_lines:
                missing_lines = "None"
            merge_summary = ""
            if merge_result:
                source_lines = "\n".join(
                    f"- {source['label']}: {source['rows']} lines ({source['encoding']})"
                    for source in merge_result["sources"]
                )
                merge_summary = (
                    f"\n\nMerged:\n{merge_result['output']}\n"
                    f"Merged lines: {merge_result['rows']}\n"
                    f"Sources:\n{source_lines}"
                )
            self._write_summary(
                f"Rows: {result['rows']}\n"
                f"Translated: {result['translated']}\n"
                f"Untranslated: {result['untranslated']}\n\n"
                f"TXT:\n{result['output_txt']}\n\n"
                f"CSV:\n{result['output_csv'] or '(disabled)'}\n\n"
                f"{merge_summary}\n\n"
                f"Untranslated names:\n{missing_lines}"
            )
            self.status.set("Done")
            messagebox.showinfo(APP_NAME, "转换并合并完成。" if merge_result else "转换完成。")
        except Exception as exc:
            self.progress["value"] = 0
            self._write_summary(f"{exc}\n\n{traceback.format_exc()}")
            self.status.set("Convert failed")
            messagebox.showerror(APP_NAME, f"转换失败：\n{exc}")

    def open_output_dir(self):
        target = self.merged_output_path.get() or self.output_path.get() or self.input_path.get()
        if not target:
            return
        folder = Path(target).parent
        if folder.exists():
            os.startfile(folder)

    def _write_preview(self, text):
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, text)

    def _write_summary(self, text):
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, text)


def main():
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description=APP_NAME)
        parser.add_argument("--self-test", action="store_true")
        parser.add_argument("--convert")
        parser.add_argument("--out")
        parser.add_argument("--cn-csv")
        parser.add_argument("--timeline")
        parser.add_argument("--merged-out")
        parser.add_argument("input_file", nargs="?")
        args = parser.parse_args()
        translator = SkillTranslator()
        if args.self_test:
            return
        if args.convert:
            if not args.out:
                raise SystemExit("--out is required with --convert")
            result = convert_axis(args.convert, args.out, args.cn_csv, translator)
            if args.timeline:
                merge_timeline_files(args.timeline, result["output_txt"], args.merged_out)
            return
        if args.input_file:
            input_path = Path(args.input_file)
            output_txt = input_path.with_name(f"{input_path.stem}_skillline.txt")
            output_csv = input_path.with_name(f"{input_path.stem}CN.csv")
            result = convert_axis(input_path, output_txt, output_csv, translator)
            if args.timeline:
                merge_timeline_files(args.timeline, result["output_txt"], args.merged_out)
            return

    root = Tk()
    app = TTSConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
