import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import subprocess
import threading
import os
import sys
import re
import time
import locale
import signal
import platform # YENİ: Windows/Mac ayrımı için eklendi

# --- TASARIM VE RENK PALETİ ---
BEZEL_COLOR = "#111111"
SCREEN_COLOR = "#FBF0D9"
INPUT_BG = "#F2E3C6"
BORDER_COLOR = "#D4C4A9"
INK_COLOR = "#30281F"
INK_HOVER = "#1A1510"
HOVER_SEPIA_DARK = "#E2D3B8"
CANCEL_RED = "#D9534F"
LOGO_COLOR = "#3A3A3A"
DASHED_BORDER = "#C4B49A"
PROGRESS_BG = "#D4C4A9"
PROGRESS_FILL = "#30281F"
PAUSE_COLOR = "#E6A817"

MAIN_FONT = "Bookerly"
FONT_TITLE = (MAIN_FONT, 22, "bold")
FONT_HEADER = (MAIN_FONT, 18, "bold")
FONT_OPTION = (MAIN_FONT, 16)
FONT_STATUS = (MAIN_FONT, 14, "bold")
FONT_SMALL = (MAIN_FONT, 12)

# ====================================================================
# ÖZEL DROPDOWN SINIFI
# ====================================================================
class KindleDropdown(ctk.CTkFrame):
    _active_dropdown = None

    def __init__(self, master, root_window, values, command=None, height=40):
        super().__init__(master, height=height, fg_color=INPUT_BG,
                         border_color=BORDER_COLOR, border_width=1, corner_radius=6)
        self.pack_propagate(False)
        self.root_window = root_window
        self.values = values
        self.command = command
        self.current_value = values[0] if values else ""

        self.btn = ctk.CTkButton(self, text=self.current_value, font=FONT_OPTION,
                                 fg_color="transparent", text_color=INK_COLOR,
                                 hover_color=HOVER_SEPIA_DARK, anchor="w", command=self.toggle)
        self.btn.pack(side="left", fill="both", expand=True, padx=5)

        self.arrow = ctk.CTkButton(self, text="▼", font=FONT_SMALL, width=30,
                                   fg_color="transparent", text_color=INK_COLOR,
                                   hover_color=HOVER_SEPIA_DARK, command=self.toggle)
        self.arrow.pack(side="right", fill="y", padx=2)

        self.menu_frame = None
        self._bind_id = None
        self._enabled = True

    def toggle(self):
        if not self._enabled:
            return
        if self.menu_frame:
            self.close()
        else:
            self.open()

    def open(self):
        if not self.values or not self._enabled:
            return

        if KindleDropdown._active_dropdown and KindleDropdown._active_dropdown != self:
            KindleDropdown._active_dropdown.close()
        KindleDropdown._active_dropdown = self

        w = self.winfo_width()
        menu_h = len(self.values) * 35 + 10

        self.menu_frame = ctk.CTkFrame(
            self.root_window,
            width=w,
            height=menu_h,
            fg_color=INPUT_BG,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=6
        )
        self.menu_frame.pack_propagate(False)

        x = self.winfo_rootx() - self.root_window.winfo_rootx()
        y_down = self.winfo_rooty() - self.root_window.winfo_rooty() + self.winfo_height()

        if y_down + menu_h > self.root_window.winfo_height():
            y = self.winfo_rooty() - self.root_window.winfo_rooty() - menu_h
        else:
            y = y_down

        self.menu_frame.place(x=x, y=y)
        self.menu_frame.lift()

        for val in self.values:
            btn = ctk.CTkButton(
                self.menu_frame, text=val, font=FONT_OPTION, anchor="w",
                fg_color="transparent", text_color=INK_COLOR,
                hover_color=HOVER_SEPIA_DARK
            )
            btn.configure(command=lambda v=val: self.select(v))
            btn.pack(fill="x", padx=2, pady=2)

        self._bind_id = self.root_window.bind("<Button-1>", self._on_global_click, add="+")

    def _on_global_click(self, event):
        if not self.menu_frame or not self.menu_frame.winfo_exists():
            return

        try:
            x, y = self.root_window.winfo_pointerxy()
            widget = self.root_window.winfo_containing(x, y)

            menu_x1 = self.menu_frame.winfo_rootx()
            menu_y1 = self.menu_frame.winfo_rooty()
            menu_x2 = menu_x1 + self.menu_frame.winfo_width()
            menu_y2 = menu_y1 + self.menu_frame.winfo_height()

            in_menu_area = (menu_x1 <= x <= menu_x2) and (menu_y1 <= y <= menu_y2)

            if widget in (self.btn, self.arrow, self, self.menu_frame):
                return
            if widget and widget.winfo_toplevel() == self.menu_frame:
                return
            if in_menu_area:
                return

            self.close()
        except Exception:
            pass

    def close(self):
        if self.menu_frame:
            self.menu_frame.destroy()
            self.menu_frame = None

        if self._bind_id:
            self.root_window.unbind("<Button-1>", self._bind_id)
            self._bind_id = None

        if KindleDropdown._active_dropdown == self:
            KindleDropdown._active_dropdown = None

    def select(self, value):
        if not self._enabled:
            return
        self.current_value = value
        self.btn.configure(text=value)
        self.close()
        if self.command:
            self.command(value)

    def set(self, value):
        self.current_value = value
        self.btn.configure(text=value)

    def get(self):
        return self.current_value

    def set_enabled(self, enabled):
        self._enabled = enabled
        state = "normal" if enabled else "disabled"
        self.btn.configure(state=state)
        self.arrow.configure(state=state)
        if not enabled:
            self.close()

# ====================================================================

class KindleizerApp:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(False)
        self.root.title("Kindleizer v1.0")
        self.root.configure(bg=BEZEL_COLOR)
        ctk.set_appearance_mode("light")

        # --- İŞLETİM SİSTEMİ KONTROLÜ ---
        self.os_name = platform.system()

        self.pdf_path = ""
        self.output_path = ""
        self.is_drawer_open = False
        self.process = None
        self.is_cancelled = False
        self.is_paused = False

        self.idx_model = 0
        self.idx_zoom = 2
        self.idx_wrap = 0
        self.idx_after = 0
        self.val_color = False

        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                self.base_path = sys._MEIPASS
            else:
                self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        # YENİ: K2pdfopt isim ve yol ayarlaması (Windows vs Mac)
        self.k2_name = "k2pdfopt.exe" if self.os_name == "Windows" else "k2pdfopt"
        self.k2_path = os.path.join(self.base_path, self.k2_name)
        
        if not os.path.exists(self.k2_path):
            self.k2_path = os.path.join(os.path.dirname(sys.executable), self.k2_name)
        if not os.path.exists(self.k2_path):
            self.k2_path = self.k2_name # Son çare sistem PATH

        self.langs = {
            'tr': {
                'title': 'Kindleizer v1.0', 'name': '🇹🇷 Türkçe',
                'drop': 'PDF Dosyasını Buraya Sürükleyin', 'drop_btn': 'Gözat',
                'model': 'Kindle Modeli:', 'color': '🎨 Renkleri Koru (Colorsoft vb. için)',
                'zoom': 'Yazı Büyütme:', 'wrap': 'Sayfa Düzeni:', 'out': 'Kayıt Konumu:',
                'after': 'İşlem Bitince:', 'start': 'DÖNÜŞTÜRMEYİ BAŞLAT', 'cancel': 'İptal Et',
                'pause': 'Duraklat', 'resume': 'Devam Et',
                'ready': 'Hazır.', 'rem': 'Kalan:', 'elapsed': 'Geçen:', 'done': '✅ DÖNÜŞÜM TAMAMLANDI!',
                'cancelled': '❌ İptal Edildi.', 'paused': '⏸️ Duraklatıldı',
                'warn': 'Lütfen bir PDF seçin!', 'clear': 'Kaldır',
                'ow_title': 'Dosya Zaten Var', 'ow_msg': 'Üzerine yazılsın mı?',
                'preparing': 'Dönüşüm başlatılıyor, lütfen bekleyin...',
                'm_opts': [
                    "6\" Standart (Basic, Eski Paperwhite)",
                    "6.8\" Paperwhite 2021",
                    "7\" Geniş (Oasis, Colorsoft, PW 2024)",
                    "10.2\" Scribe",
                    "Legacy (Eski Düşük Çözünürlük)"
                ],
                'z_opts': [
                    "1.00 - Orijinal (Küçük yazılar)",
                    "1.15 - Orta",
                    "1.30 - Yüksek (Önerilen)",
                    "1.45 - Maksimum (Büyük yazılar)"
                ],
                'w_opts': [
                    "Serbest Akış - Sadece metinler içindir (hızlı)",
                    "Düzeni Koru - Makale ve Görselli kitaplar içindir"
                ],
                'a_opts': ["Klasörde Göster", "Dosyayı Aç", "Hiçbir Şey Yapma"]
            },
            'en': {
                'title': 'Kindleizer v1.0', 'name': '🇺🇸 English',
                'drop': 'Drag & Drop PDF Here', 'drop_btn': 'Browse',
                'model': 'Kindle Model:', 'color': '🎨 Preserve Colors (for Colorsoft etc.)',
                'zoom': 'Text Zoom:', 'wrap': 'Page Layout:', 'out': 'Save Location:',
                'after': 'After Process:', 'start': 'START CONVERSION', 'cancel': 'Cancel',
                'pause': 'Pause', 'resume': 'Resume',
                'ready': 'Ready.', 'rem': 'Rem:', 'elapsed': 'Elapsed:', 'done': '✅ CONVERSION COMPLETE!',
                'cancelled': '❌ Cancelled.', 'paused': '⏸️ Paused',
                'warn': 'Please select a PDF!', 'clear': 'Remove',
                'ow_title': 'File Exists', 'ow_msg': 'Overwrite it?',
                'preparing': 'Starting conversion, please wait...',
                'm_opts': [
                    "6\" Standard (Basic, Old Paperwhite)",
                    "6.8\" Paperwhite 2021",
                    "7\" Wide (Oasis, Colorsoft, PW 2024)",
                    "10.2\" Scribe",
                    "Legacy (Old Low Resolution)"
                ],
                'z_opts': [
                    "1.00 - Original (Small text)",
                    "1.15 - Medium",
                    "1.30 - High (Recommended)",
                    "1.45 - Maximum (Large text)"
                ],
                'w_opts': [
                    "Reflow - For text only (fast)",
                    "Preserve Layout - For articles and books with illustrations"
                ],
                'a_opts': ["Show in Folder", "Open File", "Do Nothing"]
            }
        }

        self.model_specs = [
            {"w": "1072", "h": "1448", "m": "0.10", "dpi": "300"},
            {"w": "1236", "h": "1648", "m": "0.00", "dpi": "300"},
            {"w": "1264", "h": "1680", "m": "0.05", "dpi": "300"},
            {"w": "1860", "h": "2480", "m": "0.05", "dpi": "300"},
            {"w": "758",  "h": "1024", "m": "0.10", "dpi": "212"}
        ]

        try:
            loc = locale.getlocale()[0]
            current_locale = loc[:2] if loc else 'en'
            self.current_lang = current_locale if current_locale in self.langs else 'en'
        except:
            self.current_lang = 'en'

        self.setup_ui()

        self.root.update_idletasks()
        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()
        min_w, min_h = 680, 850
        final_w = max(req_w, min_w)
        final_h = max(req_h, min_h)
        self.root.geometry(f"{final_w}x{final_h}")

    def capture_state(self):
        if hasattr(self, 'zoom_box') and self.zoom_box.winfo_exists():
            L = self.langs[self.current_lang]
            try:
                self.idx_model = L['m_opts'].index(self.cihaz_box.get())
            except:
                pass
            try:
                self.idx_zoom = L['z_opts'].index(self.zoom_box.get())
            except:
                pass
            try:
                self.idx_wrap = L['w_opts'].index(self.wrap_box.get())
            except:
                pass
            try:
                self.idx_after = L['a_opts'].index(self.after_box.get())
            except:
                pass
            self.val_color = self.color_switch.get()

    def set_ui_state(self, enabled, converting=False):
        state = "normal" if enabled else "disabled"
        for dropdown in [self.cihaz_box, self.zoom_box, self.wrap_box, self.after_box]:
            if dropdown.winfo_exists():
                dropdown.set_enabled(enabled)
        if self.color_switch.winfo_exists():
            self.color_switch.configure(state=state)
        if hasattr(self, 'browse_btn') and self.browse_btn.winfo_exists():
            self.browse_btn.configure(state=state)
        if hasattr(self, 'clear_btn') and self.clear_btn.winfo_exists():
            self.clear_btn.configure(state=state)
        try:
            if enabled:
                self.drop_frame.drop_target_register(DND_FILES)
                self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
                self.drop_frame.configure(cursor="hand2")
            else:
                self.drop_frame.drop_target_unregister()
                self.drop_frame.dnd_bind('<<Drop>>', None)
                self.drop_frame.configure(cursor="arrow")
        except: pass
        if hasattr(self, 'out_btn') and self.out_btn.winfo_exists():
            self.out_btn.configure(state=state)
        self.btn_baslat.configure(state=state)
        if converting:
            self.btn_cancel.pack(side="left", padx=(0, 5))
            self.btn_pause.pack(side="left")
        else:
            self.btn_cancel.pack_forget()
            self.btn_pause.pack_forget()
        if self.btn_lang.winfo_exists():
            if enabled:
                self.btn_lang.bind("<Button-1>", lambda e: self.toggle_drawer())
                self.btn_lang.configure(cursor="hand2")
            else:
                self.btn_lang.unbind("<Button-1>")
                self.btn_lang.configure(cursor="arrow")
        if not enabled and self.is_drawer_open:
            self.drawer.place_forget()
            self.is_drawer_open = False
        self.root.update()

    def setup_ui(self):
        L = self.langs[self.current_lang]
        for widget in self.root.winfo_children():
            widget.destroy()

        self.logo_label = ctk.CTkLabel(self.root, text="kindle", font=("Helvetica", 22, "bold"), text_color=LOGO_COLOR)
        self.logo_label.pack(side="bottom", pady=(0, 15))

        self.screen_frame = ctk.CTkFrame(self.root, fg_color=SCREEN_COLOR, corner_radius=2)
        self.screen_frame.pack(fill="both", expand=True, padx=25, pady=(8, 8))
        main_pad = 25

        self.drop_frame = ctk.CTkFrame(self.screen_frame, fg_color=INPUT_BG, border_color=DASHED_BORDER, border_width=2, corner_radius=12)
        self.drop_frame.pack(fill="x", padx=main_pad, pady=(20, 15), ipady=10)
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.drop_frame.configure(cursor="hand2")

        self.drop_icon = ctk.CTkLabel(self.drop_frame, text="📄", font=(MAIN_FONT, 36), text_color=INK_COLOR)
        self.drop_icon.pack(pady=(10, 0))

        status_text = os.path.basename(self.pdf_path) if self.pdf_path else L['drop']
        self.lbl_drop = ctk.CTkLabel(self.drop_frame, text=status_text, font=(MAIN_FONT, 14, "bold"), text_color=INK_COLOR if self.pdf_path else "#8A7B69")
        self.lbl_drop.pack()

        btn_frame = ctk.CTkFrame(self.drop_frame, fg_color="transparent")
        btn_frame.pack(pady=(5, 10))

        if not self.pdf_path:
            ctk.CTkLabel(btn_frame, text="veya", font=FONT_SMALL, text_color="#8A7B69").pack(side="left", padx=5)
            self.browse_btn = ctk.CTkButton(btn_frame, text=L['drop_btn'], font=FONT_SMALL, fg_color="transparent", text_color=INK_COLOR, hover_color=HOVER_SEPIA_DARK, border_width=1, border_color=BORDER_COLOR, corner_radius=20, command=self.pdf_sec)
            self.browse_btn.pack(side="left", padx=5)
        else:
            self.clear_btn = ctk.CTkButton(btn_frame, text=L['clear'], font=FONT_SMALL, fg_color="transparent", text_color=CANCEL_RED, hover_color="#F0E0D0", border_width=1, border_color=CANCEL_RED, corner_radius=20, command=self.clear_pdf)
            self.clear_btn.pack(side="left", padx=5)

        opt_frame = ctk.CTkFrame(self.screen_frame, fg_color="transparent")
        opt_frame.pack(fill="x", padx=main_pad)

        self.add_label(opt_frame, L['model'])
        self.cihaz_box = KindleDropdown(opt_frame, self.root, values=L['m_opts'])
        self.cihaz_box.set(L['m_opts'][self.idx_model])
        self.cihaz_box.pack(fill="x", pady=(0, 8))

        self.color_switch = ctk.CTkSwitch(opt_frame, text=L['color'], font=FONT_OPTION, text_color=INK_COLOR, fg_color=BORDER_COLOR, progress_color=INK_COLOR)
        if self.val_color: self.color_switch.select()
        else: self.color_switch.deselect()
        self.color_switch.pack(anchor="w", pady=(0, 15))

        self.add_label(opt_frame, L['zoom'])
        self.zoom_box = KindleDropdown(opt_frame, self.root, values=L['z_opts'])
        self.zoom_box.set(L['z_opts'][self.idx_zoom])
        self.zoom_box.pack(fill="x", pady=(0, 15))

        self.add_label(opt_frame, L['wrap'])
        self.wrap_box = KindleDropdown(opt_frame, self.root, values=L['w_opts'])
        self.wrap_box.set(L['w_opts'][self.idx_wrap])
        self.wrap_box.pack(fill="x", pady=(0, 15))

        self.add_label(opt_frame, L['out'])
        out_container = ctk.CTkFrame(opt_frame, fg_color="transparent")
        out_container.pack(fill="x", pady=(0, 15))
        self.lbl_out = ctk.CTkLabel(out_container, text=os.path.basename(self.output_path) if self.output_path else "...", font=FONT_OPTION, text_color=INK_COLOR)
        self.lbl_out.pack(side="left")
        self.out_btn = ctk.CTkButton(out_container, text="📁", width=40, font=FONT_OPTION, fg_color=INPUT_BG, text_color=INK_COLOR, border_width=1, border_color=BORDER_COLOR, corner_radius=6, command=self.output_sec, hover_color=HOVER_SEPIA_DARK)
        self.out_btn.pack(side="right")

        self.add_label(opt_frame, L['after'])
        self.after_box = KindleDropdown(opt_frame, self.root, values=L['a_opts'])
        self.after_box.set(L['a_opts'][self.idx_after])
        self.after_box.pack(fill="x", pady=(0, 25))

        button_frame = ctk.CTkFrame(self.screen_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=main_pad, pady=(5, 5))

        self.btn_baslat = ctk.CTkButton(button_frame, text=L['start'], fg_color=INK_COLOR, hover_color=INK_HOVER, text_color=SCREEN_COLOR, font=FONT_TITLE, height=50, corner_radius=10, command=self.cevir_baslat)
        self.btn_baslat.pack(side="left", fill="x", expand=True)

        self.btn_cancel = ctk.CTkButton(button_frame, text=L['cancel'], fg_color="transparent", hover_color="#F0E0D0", text_color=CANCEL_RED, font=FONT_OPTION, height=50, width=100, corner_radius=10, border_width=1, border_color=CANCEL_RED, command=self.cancel_conversion)
        self.btn_pause = ctk.CTkButton(button_frame, text=L['pause'], fg_color=PAUSE_COLOR, hover_color="#D4A017", text_color="#FFFFFF", font=FONT_OPTION, height=50, width=100, corner_radius=10, command=self.toggle_pause)

        self.progress = ctk.CTkProgressBar(self.screen_frame, progress_color=PROGRESS_FILL, fg_color=PROGRESS_BG, height=22, corner_radius=11)
        self.progress.pack(fill="x", padx=main_pad, pady=(10, 8))
        self.progress.set(0)

        self.bottom_frame = ctk.CTkFrame(self.screen_frame, fg_color="transparent")
        self.bottom_frame.pack(fill="x", padx=main_pad, pady=(0, 15))

        self.lbl_status = ctk.CTkLabel(self.bottom_frame, text=L['ready'], font=(MAIN_FONT, 14, "bold"), text_color=INK_COLOR)
        self.lbl_status.pack(side="left", expand=True, padx=(40, 0))

        self.setup_drawer()

    def add_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=FONT_HEADER, text_color=INK_COLOR).pack(anchor="w", pady=(2, 1))

    def handle_drop(self, event):
        if self.btn_baslat.cget("state") == "disabled": return
        self.capture_state()
        path = event.data.strip('{} ')
        self.pdf_path = path
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path).strip()
        file_name, ext = os.path.splitext(base_name)
        self.output_path = os.path.join(dir_name, f"{file_name}_kindleized.pdf")
        self.setup_ui()

    def pdf_sec(self):
        if self.btn_baslat.cget("state") == "disabled": return
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.capture_state()
            self.pdf_path = path
            dir_name = os.path.dirname(path)
            base_name = os.path.basename(path).strip()
            file_name, ext = os.path.splitext(base_name)
            self.output_path = os.path.join(dir_name, f"{file_name}_kindleized.pdf")
            self.setup_ui()

    def clear_pdf(self):
        if self.btn_baslat.cget("state") == "disabled": return
        self.capture_state()
        self.pdf_path = ""
        self.output_path = ""
        self.setup_ui()

    def output_sec(self):
        if self.btn_baslat.cget("state") == "disabled": return
        if not self.pdf_path: return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=os.path.basename(self.output_path))
        if path:
            self.output_path = path
            self.lbl_out.configure(text=os.path.basename(path))

    def toggle_pause(self):
        if not self.process or self.process.poll() is not None:
            return
        
        # YENİ: Windows işletim sisteminde duraklatma sinyalleri farklıdır
        if self.os_name == "Windows":
            messagebox.showinfo("Bilgi", "Duraklatma özelliği şu an sadece Mac sistemlerinde çalışmaktadır.")
            return

        L = self.langs[self.current_lang]
        if self.is_paused:
            os.kill(self.process.pid, signal.SIGCONT)
            self.is_paused = False
            self.btn_pause.configure(text=L['pause'])
            self.lbl_status.configure(text=L['ready'])
        else:
            os.kill(self.process.pid, signal.SIGSTOP)
            self.is_paused = True
            self.btn_pause.configure(text=L['resume'])
            self.lbl_status.configure(text=L['paused'])

    def cancel_conversion(self):
        if self.process and self.process.poll() is None:
            self.is_cancelled = True
            if self.is_paused and self.os_name != "Windows":
                os.kill(self.process.pid, signal.SIGCONT) 
            self.process.terminate()
            L = self.langs[self.current_lang]
            self.lbl_status.configure(text=L['cancelled'])
            self.set_ui_state(True)
            self.progress.set(0)
            self.is_paused = False

    def cevir_baslat(self):
        if not self.pdf_path or not self.output_path:
            return

        if not os.path.exists(self.k2_path):
            messagebox.showerror("Hata", f"k2pdfopt motoru bulunamadı:\n{self.k2_path}")
            return

        if os.path.exists(self.output_path):
            L = self.langs[self.current_lang]
            overwrite = messagebox.askyesno(L['ow_title'], L['ow_msg'])
            if not overwrite:
                new_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=os.path.basename(self.output_path))
                if new_path:
                    self.output_path = new_path
                    self.lbl_out.configure(text=os.path.basename(new_path))
                else:
                    return

        self.is_cancelled = False
        self.is_paused = False
        self.set_ui_state(False, converting=True)
        self.btn_baslat.configure(text="⏳ ...")
        self.progress.set(0)
        L = self.langs[self.current_lang]
        self.lbl_status.configure(text=L['preparing'])
        
        # Sadece Mac'te yetkilendirme yapar
        if self.os_name != "Windows":
            try: os.chmod(self.k2_path, 0o755)
            except: pass
            
        threading.Thread(target=self.run_logic, daemon=True).start()

    # YENİ: K2pdfopt akıllı motor mantığı geri eklendi (Eski f2p komutları silindi)
    def run_logic(self):
        L = self.langs[self.current_lang]
        current_model_idx = L['m_opts'].index(self.cihaz_box.get())
        m = self.model_specs[current_model_idx]
        mag = self.zoom_box.get().split(" ")[0]
        wrap_text = self.wrap_box.get()
        
        # Hangi Mod?
        is_preserve = ("Koru" in wrap_text or "Preserve" in wrap_text or "Mantieni" in wrap_text or 
                       "Preservar" in wrap_text or "beibehalten" in wrap_text or "Préserver" in wrap_text)
        
        color_args = ["-c"] if self.color_switch.get() else []
        cores = str(max(1, (os.cpu_count() or 2) - 1))

        # Ortak Argümanlar
        cmd = [self.k2_path, self.pdf_path, "-nt", cores, "-x", "-w", m['w'], "-h", m['h'], "-dpi", m['dpi']]

        # Akıllı Dal (Smart Branch)
        if is_preserve:
            # Akademik/Görselli kitaplar için
            cmd.extend(["-bp", "-m", "0.05"]) 
        else:
            # Düz yazılar için
            cmd.extend(["-as", "-bp", "-m", m['m']])

        cmd.extend(color_args)
        cmd.extend(["-mag", mag, "-y", "-o", self.output_path])

        # Windows'a özel subprocess ayarları
        kwargs = {}
        if self.os_name != "Windows":
            kwargs['preexec_fn'] = os.setsid
        else:
            # Windows'ta K2pdfopt konsolunun belirmemesi için (İsteğe bağlı)
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0

        try:
            self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True, **kwargs)
            try:
                self.process.stdin.write("\n")
                self.process.stdin.flush()
            except: pass

            start_time = time.time()
            for line in self.process.stdout:
                if self.is_cancelled:
                    break
                match = re.search(r"PAGE\s+(\d+)\s+of\s+(\d+)", line)
                if match:
                    curr, total = int(match.group(1)), int(match.group(2))
                    yuzde = curr / total
                    gecen = time.time() - start_time
                    kalan = ((total - curr) * (gecen / curr)) if curr > 0 else 0
                    g_dk, g_sn = divmod(int(gecen), 60)
                    k_dk, k_sn = divmod(int(kalan), 60)
                    msg = f"%{int(yuzde*100)} ({curr}/{total})   ⏳ {L['elapsed']} {g_dk}m {g_sn}s | {L['rem']} {k_dk}m {k_sn}s"
                    self.root.after(0, lambda m=msg, y=yuzde: self.update_progress(m, y))
            
            self.process.wait()
            if not self.is_cancelled:
                self.root.after(0, self.finish)
        except Exception as e:
            if not self.is_cancelled:
                self.root.after(0, lambda err=e: messagebox.showerror("İşlem Hatası", f"Motor başlatılamadı:\n{str(err)}"))
                self.root.after(0, self.finish)

    def update_progress(self, msg, y):
        if not self.is_paused:
            self.lbl_status.configure(text=msg)
        self.progress.set(y)

    def finish(self):
        if self.is_cancelled: return
        L = self.langs[self.current_lang]
        self.lbl_status.configure(text=L['done'])
        self.btn_baslat.configure(text=L['start'])
        self.set_ui_state(True)
        self.progress.set(1.0)
        self.is_paused = False
        
        # YENİ: Windows için klasör ve dosya açma komutları
        action = self.after_box.get()
        if action == L['a_opts'][0]: # Klasörde göster
            if self.os_name == "Windows":
                subprocess.run(["explorer", "/select,", os.path.normpath(self.output_path)])
            else:
                subprocess.run(["open", "-R", self.output_path])
        elif action == L['a_opts'][1]: # Dosyayı aç
            if self.os_name == "Windows":
                os.startfile(self.output_path)
            else:
                subprocess.run(["open", self.output_path])

    def setup_drawer(self):
        self.drawer = ctk.CTkFrame(self.screen_frame, fg_color=INPUT_BG, border_color=BORDER_COLOR, border_width=1, corner_radius=8)
        for code, data in self.langs.items():
            ctk.CTkButton(self.drawer, text=data['name'], font=FONT_OPTION, fg_color="transparent", text_color=INK_COLOR, hover_color=SCREEN_COLOR, height=35, command=lambda c=code: self.change_lang(c)).pack(fill="x", padx=5, pady=2)
        self.btn_lang = ctk.CTkLabel(self.bottom_frame, text=f"🌐 {self.langs[self.current_lang]['name']}", font=FONT_SMALL, cursor="hand2", text_color=INK_COLOR)
        self.btn_lang.pack(side="right")
        self.btn_lang.bind("<Button-1>", lambda e: self.toggle_drawer())

    def toggle_drawer(self):
        if self.btn_baslat.cget("state") == "disabled": return
        if not self.is_drawer_open:
            self.drawer.place(relx=0.96, rely=0.94, anchor="se")
            self.drawer.lift()
            self.is_drawer_open = True
        else:
            self.drawer.place_forget()
            self.is_drawer_open = False

    def change_lang(self, code):
        if self.btn_baslat.cget("state") == "disabled": return
        self.capture_state()
        self.current_lang = code
        self.is_drawer_open = False
        self.setup_ui()

if __name__ == "__main__":
    class App(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self):
            super().__init__()
            self.configure(fg_color=BEZEL_COLOR)
            self.TkdndVersion = TkinterDnD._require(self)

    root = App()
    app = KindleizerApp(root)
    root.mainloop()