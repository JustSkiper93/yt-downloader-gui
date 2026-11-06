import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from yt_dlp import YoutubeDL

QUALITIES = {
    "Лучшее": None,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("580x340")
        self.resizable(False, False)

        self.folder = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.mode = tk.StringVar(value="video")
        self.quality = tk.StringVar(value="Лучшее")
        self.playlist = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Вставь ссылку и нажми «Скачать»")

        self.build_ui()

        if not shutil.which("ffmpeg"):
            messagebox.showwarning(
                "ffmpeg не найден",
                "Для склейки видео со звуком и конвертации в mp3 нужен ffmpeg.\n"
                "Установи его (ffmpeg.org) и перезапусти программу.",
            )

    def build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # Ссылка
        ttk.Label(self, text="Ссылка на видео или плейлист:").pack(anchor="w", **pad)
        self.url_entry = ttk.Entry(self)
        self.url_entry.pack(fill="x", padx=12)
        self.url_entry.focus()

        # Режим
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill="x", **pad)
        ttk.Radiobutton(mode_frame, text="Видео (mp4)", variable=self.mode,
                        value="video", command=self.on_mode).pack(side="left")
        ttk.Radiobutton(mode_frame, text="Только звук (mp3)", variable=self.mode,
                        value="audio", command=self.on_mode).pack(side="left", padx=16)

        # Качество и плейлист
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill="x", **pad)
        ttk.Label(opt_frame, text="Качество:").pack(side="left")
        self.quality_box = ttk.Combobox(opt_frame, textvariable=self.quality,
                                        values=list(QUALITIES), state="readonly", width=10)
        self.quality_box.pack(side="left", padx=8)
        ttk.Checkbutton(opt_frame, text="Скачать весь плейлист",
                        variable=self.playlist).pack(side="left", padx=16)

        # Папка
        folder_frame = ttk.Frame(self)
        folder_frame.pack(fill="x", **pad)
        ttk.Label(folder_frame, text="Папка:").pack(side="left")
        ttk.Entry(folder_frame, textvariable=self.folder).pack(
            side="left", fill="x", expand=True, padx=8)
        ttk.Button(folder_frame, text="Выбрать…", command=self.choose_folder).pack(side="left")

        # Кнопка
        self.button = ttk.Button(self, text="Скачать", command=self.start)
        self.button.pack(pady=10)

        # Прогресс и статус
        self.progress = ttk.Progressbar(self, maximum=100)
        self.progress.pack(fill="x", padx=12)
        ttk.Label(self, textvariable=self.status, wraplength=550).pack(anchor="w", **pad)

    def on_mode(self):
        state = "readonly" if self.mode.get() == "video" else "disabled"
        self.quality_box.configure(state=state)

    def choose_folder(self):
        path = filedialog.askdirectory(initialdir=self.folder.get())
        if path:
            self.folder.set(path)

    def start(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showinfo("Нет ссылки", "Вставь ссылку на видео.")
            return
        self.button.configure(state="disabled")
        self.progress["value"] = 0
        self.status.set("Начинаю…")
        threading.Thread(target=self.download, args=(url,), daemon=True).start()

    def build_options(self):
        outtmpl = str(Path(self.folder.get()) / "%(title)s.%(ext)s")
        opts = {
            "outtmpl": outtmpl,
            "noplaylist": not self.playlist.get(),
            "progress_hooks": [self.hook],
            "quiet": True,
            "no_warnings": True,
        }
        if self.mode.get() == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            h = QUALITIES[self.quality.get()]
            if h:
                opts["format"] = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            else:
                opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"
        return opts

    def download(self, url):
        try:
            with YoutubeDL(self.build_options()) as ydl:
                ydl.download([url])
            self.after(0, self.done, "Готово! Файл сохранён в выбранной папке.")
        except Exception as e:
            self.after(0, self.done, f"Ошибка: {e}", True)

    def hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                percent = d["downloaded_bytes"] / total * 100
                speed = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()
                self.after(0, self.update_progress, percent,
                           f"Скачивание: {percent:.1f}%  {speed}  осталось {eta}")
        elif d["status"] == "finished":
            self.after(0, self.update_progress, 100, "Обработка файла…")

    def update_progress(self, percent, text):
        self.progress["value"] = percent
        self.status.set(text)

    def done(self, message, error=False):
        self.button.configure(state="normal")
        self.status.set(message)
        if error:
            messagebox.showerror("Ошибка", message)


if __name__ == "__main__":
    App().mainloop()
