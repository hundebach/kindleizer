import sys
import os
import subprocess
import threading
import platform
import re
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QFileDialog, QProgressBar, QFrame, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor

# --- TASARIM SABİTLERİ ---
COLOR_BG = "#FBF0D9"  # Kindle Arka Plan
COLOR_PRIMARY = "#30281F"  # Kahverengi Mürekkep
COLOR_SECONDARY = "#F2E3C6"  # Giriş Alanları
COLOR_ACCENT = "#D4C4A9"  # Kenarlıklar
COLOR_TEXT_DIM = "#8A7B69" # Yardımcı Metin

class WorkerSignals(QObject):
    progress = pyqtSignal(str, float)
    finished = pyqtSignal()
    error = pyqtSignal(str)

class KindleizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.os_name = platform.system()
        self.pdf_path = ""
        self.output_path = ""
        self.start_time = 0
        
        # Dosya yolları ayarı
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.k2_name = "k2pdfopt.exe" if self.os_name == "Windows" else "k2pdfopt"
        self.k2_path = os.path.join(self.base_path, self.k2_name)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Kindleizer v1.2")
        self.setFixedSize(600, 850)
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(15)

        # 1. BAŞLIK BÖLÜMÜ
        header_layout = QHBoxLayout()
        title = QLabel("KINDLEIZER")
        title.setFont(QFont("Georgia", 28, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_PRIMARY}; letter-spacing: 2px;")
        header_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(header_layout)

        # 2. DOSYA SEÇİM ALANI (Sürükle-Bırak)
        self.drop_frame = QFrame()
        self.drop_frame.setFixedSize(530, 140)
        self.drop_frame.setAcceptDrops(True)
        self.drop_frame.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {COLOR_ACCENT};
                border-radius: 12px;
                background-color: {COLOR_SECONDARY};
            }}
        """)
        drop_layout = QVBoxLayout(self.drop_frame)
        self.lbl_drop_title = QLabel("📄 Drag & Drop PDF Here")
        self.lbl_drop_title.setFont(QFont("Helvetica", 13, QFont.Weight.Bold))
        self.lbl_drop_title.setStyleSheet(f"color: {COLOR_PRIMARY}; border: none;")
        self.lbl_drop_subtitle = QLabel("or click to browse")
        self.lbl_drop_subtitle.setStyleSheet(f"color: {COLOR_TEXT_DIM}; border: none;")
        drop_layout.addWidget(self.lbl_drop_title, alignment=Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(self.lbl_drop_subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        self.drop_frame.mousePressEvent = lambda e: self.select_pdf()
        layout.addWidget(self.drop_frame)

        # 3. KAYIT KONUMU BÖLÜMÜ
        save_layout = QVBoxLayout()
        lbl_save = QLabel("📁 SAVE LOCATION")
        lbl_save.setFont(QFont("Helvetica", 10, QFont.Weight.Bold))
        lbl_save.setStyleSheet(f"color: {COLOR_PRIMARY};")
        save_layout.addWidget(lbl_save)
        
        save_input_row = QHBoxLayout()
        self.save_path_edit = QLabel("No folder selected...")
        self.save_path_edit.setFixedHeight(40)
        self.save_path_edit.setStyleSheet(f"background-color: {COLOR_SECONDARY}; border: 1px solid {COLOR_ACCENT}; border-radius: 6px; padding-left: 10px; color: {COLOR_PRIMARY};")
        
        btn_browse_save = QPushButton("...")
        btn_browse_save.setFixedSize(40, 40)
        btn_browse_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_browse_save.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: {COLOR_PRIMARY}; border-radius: 6px; font-weight: bold;")
        btn_browse_save.clicked.connect(self.select_output_path)
        
        save_input_row.addWidget(self.save_path_edit)
        save_input_row.addWidget(btn_browse_save)
        save_layout.addLayout(save_input_row)
        layout.addLayout(save_layout)

        # 4. AYARLAR PANELİ
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"background-color: {COLOR_SECONDARY}; border-radius: 10px; padding: 10px;")
        settings_layout = QVBoxLayout(settings_frame)
        
        self.ui_model = self.add_setting(settings_layout, "Kindle Model:", ["6\" Standard", "6.8\" Paperwhite", "7\" Oasis/Colorsoft", "10.2\" Scribe"])
        self.ui_zoom = self.add_setting(settings_layout, "Text Zoom:", ["1.00 - Small", "1.15 - Medium", "1.30 - High (Rec.)", "1.45 - Max"])
        self.ui_layout = self.add_setting(settings_layout, "Page Layout:", ["Reflow (Text Only)", "Preserve Layout (Academic)"])
        
        layout.addWidget(settings_frame)

        # 5. OPSİYONLAR (Checkbox)
        self.cb_open_file = QCheckBox("Open file when finished")
        self.cb_open_file.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold;")
        layout.addWidget(self.cb_open_file)

        # 6. PROGRESS VE DURUM
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLOR_ACCENT};
                border-radius: 8px;
                text-align: center;
                height: 15px;
                background-color: {COLOR_SECONDARY};
                color: {COLOR_PRIMARY};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_PRIMARY};
                border-radius: 8px;
            }}
        """)
        layout.addWidget(self.progress)

        self.status_lbl = QLabel("Ready to start.")
        self.status_lbl.setFont(QFont("Helvetica", 11))
        self.status_lbl.setStyleSheet(f"color: {COLOR_PRIMARY};")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

        # 7. BAŞLAT BUTONU
        self.btn_start = QPushButton("START CONVERSION")
        self.btn_start.setFixedHeight(65)
        self.btn_start.setFont(QFont("Helvetica", 15, QFont.Weight.Bold))
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BG};
                border-radius: 12px;
            }}
            QPushButton:hover {{ background-color: #1A1510; }}
            QPushButton:disabled {{ background-color: #A0A0A0; }}
        """)
        self.btn_start.clicked.connect(self.start_process)
        layout.addWidget(self.btn_start)

    def add_setting(self, parent_layout, label, items):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; border: none;")
        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedWidth(220)
        combo.setStyleSheet(f"background-color: {COLOR_BG}; border: 1px solid {COLOR_ACCENT}; border-radius: 4px; padding: 5px; color: {COLOR_PRIMARY};")
        row.addWidget(lbl)
        row.addWidget(combo)
        parent_layout.addLayout(row)
        return combo

    def select_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if file:
            self.set_pdf_path(file)

    def select_output_path(self):
        if not self.pdf_path: return
        file, _ = QFileDialog.getSaveFileName(self, "Save Optimized PDF As", self.output_path, "PDF Files (*.pdf)")
        if file:
            self.output_path = file
            self.save_path_edit.setText(os.path.basename(file))

    def set_pdf_path(self, path):
        self.pdf_path = path
        self.lbl_drop_title.setText(os.path.basename(path))
        dir_name = os.path.dirname(path)
        base_name = os.path.splitext(os.path.basename(path))[0]
        self.output_path = os.path.join(dir_name, f"{base_name}_kindleized.pdf")
        self.save_path_edit.setText(os.path.basename(self.output_path))

    def start_process(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "Error", "Please select a PDF file first!")
            return

        # Overwrite koruması
        if os.path.exists(self.output_path):
            reply = QMessageBox.question(self, "File Exists", f"The file already exists:\n{os.path.basename(self.output_path)}\n\nDo you want to overwrite it?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        self.btn_start.setEnabled(False)
        self.start_time = time.time()
        
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_progress)
        self.signals.finished.connect(self.on_finished)
        
        threading.Thread(target=self.run_conversion_logic, daemon=True).start()

    def update_progress(self, msg, val):
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"[{mins:02d}:{secs:02d}]"
        self.status_lbl.setText(f"{time_str} {msg}")
        self.progress.setValue(int(val * 100))

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.progress.setValue(100)
        self.status_lbl.setText("Finished!")
        
        if self.cb_open_file.isChecked():
            if self.os_name == "Windows": os.startfile(self.output_path)
            else: subprocess.run(["open", self.output_path])

    def run_conversion_logic(self):
        # Ayarlar
        models = [["1072", "1448", "300"], ["1236", "1648", "300"], ["1264", "1680", "300"], ["1860", "2480", "300"]]
        m = models[self.ui_model.currentIndex()]
        zoom = self.ui_zoom.currentText().split(" ")[0]
        is_preserve = "Preserve" in self.ui_layout.currentText()

        cmd = [self.k2_path, self.pdf_path, "-x", "-w", m[0], "-h", m[1], "-dpi", m[2]]
        if is_preserve: cmd.extend(["-wrap-", "-ws", "-1", "-bp"])
        else: cmd.extend(["-as", "-bp"])
        cmd.extend(["-mag", zoom, "-y", "-o", self.output_path])

        try:
            startupinfo = None
            if self.os_name == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo)
            for line in process.stdout:
                match = re.search(r"PAGE\s+(\d+)\s+of\s+(\d+)", line)
                if match:
                    curr, total = int(match.group(1)), int(match.group(2))
                    self.signals.progress.emit(f"Processing Page {curr}/{total}", curr/total)
            process.wait()
            self.signals.finished.emit()
        except Exception as e:
            self.signals.progress.emit(f"Error: {str(e)}", 0)
            self.signals.finished.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # İkon varsa yükle (icon.png dosyanın adıyla eşleşmeli)
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon.png")))
    window = KindleizerApp()
    window.show()
    sys.exit(app.exec())