import yt_dlp
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
import requests
import io
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
from mutagen.mp4 import MP4, MP4Cover
import threading
import json
import shutil

VERSION = "Beta 1.0.0"

class AboutWindow:
    def __init__(self, parent):
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Hakkında")
        self.window.geometry("400x300")
        self.window.transient(parent)
        
        frame = ctk.CTkFrame(self.window)
        frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        title = ctk.CTkLabel(
            frame,
            text="Youtube MP3/MP4 İndirme Yazılımı (kelle)",
            font=("Helvetica", 20, "bold")
        )
        title.pack(pady=10)
        
        version = ctk.CTkLabel(
            frame,
            text=f"Version: {VERSION}"
        )
        version.pack(pady=5)
        
        developer = ctk.CTkLabel(
            frame,
            text="Yapımcı: Kelle (Kerem)"
        )
        developer.pack(pady=5)
        
        description = ctk.CTkLabel(
            frame,
            text="YouTube'dan MP3 ve MP4 indirmek için\ngeliştirilmiş modern bir araç.",
            wraplength=300
        )
        description.pack(pady=20)

class ColorfulText(ctk.CTkLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.colors = ["#FFB3BA", "#BAFFC9", "#BAE1FF", "#FFFFBA"]  # Soft renkler
        self.current_color = 0
        self.text = "K E R E M"
        self.update_color()

    def update_color(self):
        self.configure(text=self.text, text_color=self.colors[self.current_color])
        self.current_color = (self.current_color + 1) % len(self.colors)
        self.after(1000, self.update_color)  # Her saniyede renk değişimi

class YouTubeDownloaderGUI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title(f"KELLE MP3/MP4 İNDİRME YAZILIMI {VERSION}")
        self.window.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # FFmpeg yolunu ayarla
        self.setup_ffmpeg()

        # Ana frame
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # URL girişi
        self.url_label = ctk.CTkLabel(
            self.main_frame, 
            text="YouTube URL'leri (virgülle ayırarak birden fazla URL girebilirsiniz):"
        )
        self.url_label.pack(pady=5)
        
        self.url_entry = ctk.CTkTextbox(self.main_frame, height=100)
        self.url_entry.pack(pady=5, padx=20, fill="x")

        # Format seçimi
        self.format_var = tk.StringVar(value="mp3")
        self.format_frame = ctk.CTkFrame(self.main_frame)
        self.format_frame.pack(pady=10)
        
        self.mp3_radio = ctk.CTkRadioButton(
            self.format_frame, 
            text="MP3", 
            variable=self.format_var, 
            value="mp3",
            command=self.update_quality_options
        )
        self.mp3_radio.pack(side="left", padx=10)
        
        self.mp4_radio = ctk.CTkRadioButton(
            self.format_frame, 
            text="MP4", 
            variable=self.format_var, 
            value="mp4",
            command=self.update_quality_options
        )
        self.mp4_radio.pack(side="left", padx=10)

        # Metadata ve Thumbnail seçenekleri
        self.options_frame = ctk.CTkFrame(self.main_frame)
        self.options_frame.pack(pady=10)

        self.metadata_var = tk.BooleanVar(value=True)
        self.metadata_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Etiketleri İndir (Şarkı/Video bilgilerini ekle)",
            variable=self.metadata_var
        )
        self.metadata_checkbox.pack(side="left", padx=10)

        self.thumbnail_var = tk.BooleanVar(value=True)
        self.thumbnail_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Thumbnail İndir (İndirme hızını düşürebilir)",
            variable=self.thumbnail_var
        )
        self.thumbnail_checkbox.pack(side="left", padx=10)

        # Kalite seçimi
        self.quality_label = ctk.CTkLabel(self.main_frame, text="Kalite:")
        self.quality_label.pack(pady=5)
        
        self.quality_var = tk.StringVar()
        self.quality_combobox = ctk.CTkComboBox(
            self.main_frame,
            variable=self.quality_var
        )
        self.quality_combobox.pack(pady=5)
        self.update_quality_options()

        # İndirme dizini seçimi
        self.dir_button = ctk.CTkButton(
            self.main_frame,
            text="İndirme Dizini Seç",
            command=self.select_directory
        )
        self.dir_button.pack(pady=10)
        
        self.dir_label = ctk.CTkLabel(self.main_frame, text="")
        self.dir_label.pack(pady=5)

        # İndirme butonu
        self.download_button = ctk.CTkButton(
            self.main_frame,
            text="İndir",
            command=self.start_download
        )
        self.download_button.pack(pady=10)

        # Progress bars
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(pady=10, fill="x", padx=20)

        self.overall_label = ctk.CTkLabel(self.progress_frame, text="Genel İlerleme:")
        self.overall_label.pack(pady=2)
        
        self.overall_progress = ctk.CTkProgressBar(self.progress_frame)
        self.overall_progress.pack(fill="x", pady=2)
        self.overall_progress.set(0)

        self.current_label = ctk.CTkLabel(self.progress_frame, text="Mevcut İndirme:")
        self.current_label.pack(pady=2)
        
        self.current_progress = ctk.CTkProgressBar(self.progress_frame)
        self.current_progress.pack(fill="x", pady=2)
        self.current_progress.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(self.main_frame, text="")
        self.status_label.pack(pady=5)

        # Rengarenk KEREM yazısı
        self.colorful_name = ColorfulText(self.window)
        self.colorful_name.place(relx=0.95, rely=0.95, anchor="se")

        # Menü bar
        self.menu_bar = tk.Menu(self.window)
        self.window.config(menu=self.menu_bar)
        
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Yardım", menu=self.help_menu)
        self.help_menu.add_command(label="Hakkında", command=self.show_about)

        self.output_dir = os.getcwd()
        self.dir_label.configure(text=f"İndirme dizini: {self.output_dir}")

    def setup_ffmpeg(self):
        # FFmpeg'in uygulama klasöründe olup olmadığını kontrol et
        app_dir = os.path.dirname(os.path.abspath(__file__))
        ffmpeg_dir = os.path.join(app_dir, "ffmpeg", "bin")
        
        if not os.path.exists(ffmpeg_dir):
            os.makedirs(ffmpeg_dir, exist_ok=True)
        
        # FFmpeg yolunu sistem PATH'ine ekle
        if ffmpeg_dir not in os.environ['PATH']:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']

    def show_about(self):
        AboutWindow(self.window)

    def update_quality_options(self):
        if self.format_var.get() == "mp3":
            qualities = ["128", "192", "256", "320"]
            self.quality_combobox.configure(values=qualities)
            self.quality_combobox.set("320")
        else:
            qualities = ["360", "480", "720", "1080", "2k", "4k"]
            self.quality_combobox.configure(values=qualities)
            self.quality_combobox.set("1080")

    def select_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir = dir_path
            self.dir_label.configure(text=f"İndirme dizini: {self.output_dir}")

    def update_overall_progress(self, progress):
        self.overall_progress.set(progress)
        self.window.update_idletasks()

    def update_current_progress(self, progress):
        self.current_progress.set(progress)
        self.window.update_idletasks()

    def update_status(self, text):
        self.status_label.configure(text=text)
        self.window.update_idletasks()

    def add_metadata(self, file_path, info, thumbnail_data):
        try:
            if file_path.endswith('.mp3'):
                audio = MP3(file_path, ID3=ID3)
                
                try:
                    audio.add_tags()
                except mutagen.id3.error:
                    pass

                if thumbnail_data:
                    audio.tags.add(
                        APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,
                            desc='Cover',
                            data=thumbnail_data
                        )
                    )

                audio.tags.add(TIT2(encoding=3, text=info['title']))
                audio.tags.add(TPE1(encoding=3, text=info.get('uploader', 'Unknown')))
                audio.tags.add(TALB(encoding=3, text=info.get('album', 'YouTube')))
                
                audio.save()

            elif file_path.endswith('.mp4'):
                video = MP4(file_path)
                video['\xa9nam'] = info['title']
                video['\xa9ART'] = info.get('uploader', 'Unknown')
                video['\xa9alb'] = info.get('album', 'YouTube')
                
                if thumbnail_data:
                    video['covr'] = [MP4Cover(thumbnail_data)]
                
                video.save()

        except Exception as e:
            print(f"Metadata eklenirken hata oluştu: {str(e)}")

    def clean_thumbnail_files(self, base_path):
        try:
            # Thumbnail dosya uzantıları
            thumbnail_extensions = ['.jpg', '.png', '.webp']
            base_name = os.path.splitext(base_path)[0]
            
            for ext in thumbnail_extensions:
                thumbnail_path = base_name + ext
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
        except Exception as e:
            print(f"Thumbnail temizlenirken hata oluştu: {str(e)}")

    def download_media(self, url):
        format_type = self.format_var.get()
        quality = self.quality_var.get()
        include_metadata = self.metadata_var.get()
        include_thumbnail = self.thumbnail_var.get()
        
        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'writethumbnail': include_thumbnail,
            }
        else:
            ydl_opts = {
                'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]',
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'writethumbnail': include_thumbnail,
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Thumbnail'i indir (eğer seçenek işaretliyse)
                thumbnail_data = None
                if include_thumbnail and include_metadata:
                    thumbnail_url = info.get('thumbnail')
                    if thumbnail_url:
                        response = requests.get(thumbnail_url)
                        if response.status_code == 200:
                            thumbnail_data = response.content

                self.update_status(f"İndiriliyor: {info['title']}")
                ydl.download([url])

                file_name = ydl.prepare_filename(info)
                if format_type == 'mp3':
                    file_name = os.path.splitext(file_name)[0] + '.mp3'
                elif format_type == 'mp4':
                    file_name = os.path.splitext(file_name)[0] + '.mp4'

                if include_metadata:
                    self.add_metadata(file_name, info, thumbnail_data)
                if include_thumbnail:
                    self.clean_thumbnail_files(file_name)

                self.update_status(f"İndirme tamamlandı: {info['title']}")
                return True

        except Exception as e:
            self.update_status(f"Hata: {str(e)}")
            return False

    def start_download(self):
        urls = [url.strip() for url in self.url_entry.get("1.0", tk.END).strip().split(',') if url.strip()]
        
        if not urls:
            self.update_status("Lütfen en az bir URL girin.")
            return

        self.download_button.configure(state="disabled")
        
        def download_thread():
            total = len(urls)
            successful = 0
            
            for i, url in enumerate(urls):
                if self.download_media(url):
                    successful += 1
                self.update_overall_progress((i + 1) / total)
            
            self.update_status(f"İndirme tamamlandı. {successful}/{total} başarılı.")
            self.download_button.configure(state="normal")
            self.overall_progress.set(0)
            self.current_progress.set(0)

        threading.Thread(target=download_thread, daemon=True).start()

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = YouTubeDownloaderGUI()
    app.run()