import sys
import os
import subprocess
import threading
import platform
import re
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QFileDialog, QProgressBar, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor

# --- TASARIM SABİTLERİ ---
COLOR_BG = "#FBF0D9"  # Kindle ekran rengi
COLOR_PRIMARY = "#30281F"  # Koyu mürekkep
COLOR_SECONDARY = "#F2E3C6"  # Açık bej giriş alanları
COLOR_ACCENT = "#D4C4A9"  # Kenarlıklar
COLOR_TEXT = "#30281F"
COLOR_WHITE = "#FFFFFF"

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
        self.process = None
        self.is_cancelled = False
        
        # Dosya yolları
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.k2_name = "k2pdfopt.exe" if self.os_name == "Windows" else "k2pdfopt"
        self.k2_path = os.path.join(self.base_path, self.k2_name)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Kindleizer v1.1")
        self.setFixedSize(600, 800)
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        # Ana Widget ve Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Başlık
        title = QLabel("Kindleizer")
        title.setFont(QFont("Georgia", 32, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {COLOR_PRIMARY}; margin-bottom: 10px;")
        layout.addWidget(title)

        # Drop Alanı (Görsel olarak buton şeklinde)
        self.drop_label = QLabel("Drag & Drop PDF Here\nor Click to Browse")
        self.drop_label.setFixedSize(520, 150)
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setFont(QFont("Helvetica", 14))
        self.drop_label.setAcceptDrops(True)
        self.drop_label.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {COLOR_ACCENT};
                border-radius: 15px;
                background-color: {COLOR_SECONDARY};
                color: #8A7B69;
            }}
            QLabel:hover {{
                background-color: #EBD9B4;
            }}
        """)
        self.drop_label.mousePressEvent = lambda e: self.select_pdf()
        layout.addWidget(self.drop_label)

        # Seçenekler Paneli
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)

        self.model_combo = self.create_styled_combo(["6\" Standard", "6.8\" Paperwhite", "7\" Oasis/Colorsoft", "10.2\" Scribe"], "Kindle Model")
        form_layout.addLayout(self.model_combo)

        self.zoom_combo = self.create_styled_combo(["1.00 - Small", "1.15 - Medium", "1.30 - High (Rec.)", "1.45 - Max"], "Text Zoom")
        form_layout.addLayout(self.zoom_combo)

        self.layout_combo = self.create_styled_combo(["Reflow (Text Only)", "Preserve Layout (Academic)"], "Page Layout")
        form_layout.addLayout(self.layout_combo)

        layout.addLayout(form_layout)

        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLOR_ACCENT};
                border-radius: 10px;
                text-align: center;
                height: 20px;
                background-color: {COLOR_SECONDARY};
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_PRIMARY};
                border-radius: 10px;
            }}
        """)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_lbl = QLabel("Ready.")
        self.status_lbl.setFont(QFont("Helvetica", 12))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

        # Başlat Butonu
        self.btn_start = QPushButton("START CONVERSION")
        self.btn_start.setFixedHeight(60)
        self.btn_start.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BG};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: #1A1510;
            }}
            QPushButton:disabled {{
                background-color: #A0A0A0;
            }}
        """)
        self.btn_start.clicked.connect(self.start_conversion)
        layout.addWidget(self.btn_start)

    def create_styled_combo(self, items, label_text):
        container = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {COLOR_PRIMARY};")
        
        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedHeight(45)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_SECONDARY};
                border: 1px solid {COLOR_ACCENT};
                border-radius: 8px;
                padding-left: 10px;
                font-size: 14px;
            }}
            QComboBox::drop-down {{
                border: 0px;
            }}
        """)
        container.addWidget(lbl)
        container.addWidget(combo)
        
        # Combo objesine doğrudan erişim için bir özellik ekleyelim
        if "Model" in label_text: self.ui_model = combo
        elif "Zoom" in label_text: self.ui_zoom = combo
        elif "Layout" in label_text: self.ui_layout = combo
        
        return container

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.set_pdf(files[0])

    def select_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if file:
            self.set_pdf(file)

    def set_pdf(self, path):
        self.pdf_path = path
        self.drop_label.setText(f"Selected: {os.path.basename(path)}")
        self.drop_label.setStyleSheet(f"border: 2px solid {COLOR_PRIMARY}; border-radius: 15px; background-color: {COLOR_SECONDARY}; color: {COLOR_PRIMARY};")
        
        dir_name = os.path.dirname(path)
        base_name = os.path.splitext(os.path.basename(path))[0]
        self.output_path = os.path.join(dir_name, f"{base_name}_kindleized.pdf")

    def start_conversion(self):
        if not self.pdf_path:
            self.status_lbl.setText("Please select a PDF first!")
            return

        self.btn_start.setEnabled(False)
        self.status_lbl.setText("Processing...")
        
        # Thread başlatma
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_ui_progress)
        self.signals.finished.connect(self.conversion_finished)
        
        threading.Thread(target=self.run_logic, daemon=True).start()

    def update_ui_progress(self, msg, val):
        self.status_lbl.setText(msg)
        self.progress.setValue(int(val * 100))

    def conversion_finished(self):
        self.btn_start.setEnabled(True)
        self.status_lbl.setText("Conversion Complete!")
        self.progress.setValue(100)

    def run_logic(self):
        # Ayarların okunması
        model_idx = self.ui_model.currentIndex()
        models = [
            ["1072", "1448", "300"], # Standard
            ["1236", "1648", "300"], # PW 2021
            ["1264", "1680", "300"], # Oasis
            ["1860", "2480", "300"]  # Scribe
        ]
        m = models[model_idx]
        zoom = self.ui_zoom.currentText().split(" ")[0]
        is_preserve = "Preserve" in self.ui_layout.currentText()

        # Komut Hazırlama
        cmd = [self.k2_path, self.pdf_path, "-x", "-w", m[0], "-h", m[1], "-dpi", m[2]]
        
        if is_preserve:
            cmd.extend(["-wrap-", "-ws", "-1", "-bp"]) # Düzeni koru
        else:
            cmd.extend(["-as", "-bp"]) # Reflow
            
        cmd.extend(["-mag", zoom, "-y", "-o", self.output_path])

        try:
            startupinfo = None
            if self.os_name == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                            text=True, startupinfo=startupinfo)
            
            for line in self.process.stdout:
                match = re.search(r"PAGE\s+(\d+)\s+of\s+(\d+)", line)
                if match:
                    curr, total = int(match.group(1)), int(match.group(2))
                    msg = f"Processing Page {curr} / {total}"
                    self.signals.progress.emit(msg, curr/total)
            
            self.process.wait()
            self.signals.finished.emit()
        except Exception as e:
            self.signals.progress.emit(f"Error: {str(e)}", 0)
            self.signals.finished.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.png")) # Varsa ikon
    window = KindleizerApp()
    window.show()
    sys.exit(app.exec())