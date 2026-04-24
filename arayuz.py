import sys
import os
import subprocess
import threading
import platform
import re
import time
import webbrowser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QFileDialog, QProgressBar, QFrame, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor

# --- TASARIM SABİTLERİ ---
COLOR_BEZEL = "#111111"  # Kindle Kasa Rengi
COLOR_SCREEN = "#FBF0D9" # Kindle Ekran Rengi
COLOR_PRIMARY = "#30281F" # Mürekkep Rengi
COLOR_SECONDARY = "#F2E3C6" # Giriş Alanları
COLOR_ACCENT = "#D4C4A9" # Kenarlıklar
COLOR_TEXT_DIM = "#8A7B69"

class WorkerSignals(QObject):
    progress = pyqtSignal(str, float)
    finished = pyqtSignal()

class KindleizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.os_name = platform.system()
        self.pdf_path = ""
        self.output_path = ""
        self.start_time = 0
        self.setAcceptDrops(True)
        
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.k2_name = "k2pdfopt.exe" if self.os_name == "Windows" else "k2pdfopt"
        self.k2_path = os.path.join(self.base_path, self.k2_name)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Kindleizer")
        self.setFixedSize(650, 850)
        self.setStyleSheet(f"background-color: {COLOR_BEZEL};")

        # ANA KASA (BEZEL)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        bezel_layout = QVBoxLayout(main_widget)
        bezel_layout.setContentsMargins(15, 15, 15, 15)

        # ÜST BAR (Ko-fi)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.btn_kofi = QPushButton("☕ Support")
        self.btn_kofi.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kofi.setFixedSize(100, 30)
        self.btn_kofi.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT}; color: {COLOR_PRIMARY}; border-radius: 15px; font-weight: bold; font-size: 11px; }}")
        self.btn_kofi.clicked.connect(lambda: webbrowser.open("https://ko-fi.com/hundebach")) 
        top_bar.addWidget(self.btn_kofi)
        bezel_layout.addLayout(top_bar)

        # EKRAN ALANI
        screen_frame = QFrame()
        screen_frame.setStyleSheet(f"background-color: {COLOR_SCREEN}; border-radius: 5px;")
        bezel_layout.addWidget(screen_frame)
        
        screen_layout = QVBoxLayout(screen_frame)
        screen_layout.setContentsMargins(25, 20, 25, 20)
        screen_layout.setSpacing(12)

        # 1. DROP ALANI
        self.drop_frame = QFrame()
        self.drop_frame.setFixedHeight(100)
        self.drop_frame.setStyleSheet(f"border: 2px dashed {COLOR_ACCENT}; border-radius: 12px; background-color: {COLOR_SECONDARY};")
        drop_vbox = QVBoxLayout(self.drop_frame)
        self.lbl_drop = QLabel("Drag & Drop PDF File Here")
        self.lbl_drop.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.lbl_drop.setStyleSheet(f"color: {COLOR_PRIMARY}; border: none;")
        drop_vbox.addWidget(self.lbl_drop, alignment=Qt.AlignmentFlag.AlignCenter)
        self.drop_frame.mousePressEvent = lambda e: self.select_pdf()
        screen_layout.addWidget(self.drop_frame)

        # 2. SAVE LOCATION
        save_box = QVBoxLayout()
        lbl_save_title = QLabel("SAVE TO:")
        lbl_save_title.setFont(QFont("Helvetica", 9, QFont.Weight.Bold))
        lbl_save_title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        save_box.addWidget(lbl_save_title)
        save_row = QHBoxLayout()
        self.lbl_save_path = QLabel("Select destination...")
        self.lbl_save_path.setFixedHeight(35)
        self.lbl_save_path.setStyleSheet(f"background-color: {COLOR_SECONDARY}; border: 1px solid {COLOR_ACCENT}; border-radius: 6px; padding-left: 10px; color: {COLOR_PRIMARY};")
        btn_save = QPushButton("...")
        btn_save.setFixedSize(40, 35)
        btn_save.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: {COLOR_SCREEN}; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.select_output_path)
        save_row.addWidget(self.lbl_save_path)
        save_row.addWidget(btn_save)
        save_box.addLayout(save_row)
        screen_layout.addLayout(save_box)

        # 3. SETTINGS
        settings_group = QFrame()
        settings_group.setStyleSheet(f"background-color: {COLOR_SECONDARY}; border-radius: 12px; border: 1px solid {COLOR_ACCENT};")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(15, 10, 15, 10)
        
        self.ui_model = self.add_setting(settings_layout, "Device Model:", ["Basic (6\")", "Paperwhite (6.8\")", "Oasis (7\")", "Scribe (10.2\")"])
        self.ui_zoom = self.add_setting(settings_layout, "Text Zoom:", ["1.00", "1.15", "1.30 (Rec.)", "1.45"], default_idx=2)
        self.ui_layout = self.add_setting(settings_layout, "Layout Strategy:", ["Reflow", "Preserve Layout"])
        screen_layout.addWidget(settings_group)

        # 4. OPTIONS
        opt_layout = QHBoxLayout()
        self.cb_color = QCheckBox("Preserve Colors")
        self.cb_open = QCheckBox("Open When Done")
        for cb in [self.cb_color, self.cb_open]:
            cb.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
            opt_layout.addWidget(cb)
        screen_layout.addLayout(opt_layout)

        # 5. PROGRESS & STATUS
        self.progress = QProgressBar()
        self.progress.setFixedHeight(20)
        self.progress.setStyleSheet(f"QProgressBar {{ border: 1px solid {COLOR_ACCENT}; border-radius: 10px; text-align: center; background-color: {COLOR_SECONDARY}; color: {COLOR_PRIMARY}; font-weight: bold; }} QProgressBar::chunk {{ background-color: {COLOR_PRIMARY}; border-radius: 10px; }}")
        screen_layout.addWidget(self.progress)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet(f"color: {COLOR_PRIMARY};")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen_layout.addWidget(self.status_lbl)

        # 6. START BUTTON
        self.btn_start = QPushButton("START OPTIMIZATION")
        self.btn_start.setFixedHeight(60)
        self.btn_start.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        self.btn_start.setStyleSheet(f"QPushButton {{ background-color: {COLOR_PRIMARY}; color: {COLOR_SCREEN}; border-radius: 10px; }} QPushButton:hover {{ background-color: #1A1510; }}")
        self.btn_start.clicked.connect(self.process_start)
        screen_layout.addWidget(self.btn_start)

        # 7. KINDLE LOGO (Alt Bezel)
        footer_logo = QLabel("kindle")
        footer_logo.setFont(QFont("Georgia", 22, QFont.Weight.Bold))
        footer_logo.setStyleSheet("color: #333333; margin-top: 5px;")
        footer_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bezel_layout.addWidget(footer_logo)

        # COPYRIGHT
        footer_lbl = QLabel("powered by k2pdfopt | hundebach")
        footer_lbl.setFont(QFont("Helvetica", 8))
        footer_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bezel_layout.addWidget(footer_lbl)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files: self.update_paths(files[0])

    def add_setting(self, parent_layout, label_text, items, default_idx=0):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; border: none; font-size: 11px;")
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentIndex(default_idx)
        combo.setStyleSheet(f"QComboBox {{ background-color: {COLOR_SCREEN}; border: 1px solid {COLOR_ACCENT}; border-radius: 5px; color: {COLOR_PRIMARY}; }}")
        row.addWidget(lbl)
        row.addWidget(combo)
        parent_layout.addLayout(row)
        return combo

    def select_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if file: self.update_paths(file)

    def select_output_path(self):
        if not self.pdf_path: return
        file, _ = QFileDialog.getSaveFileName(self, "Save PDF", self.output_path, "PDF Files (*.pdf)")
        if file:
            self.output_path = file
            self.lbl_save_path.setText(os.path.basename(file))

    def update_paths(self, path):
        self.pdf_path = path
        self.lbl_drop.setText(os.path.basename(path))
        dir_name = os.path.dirname(path)
        base = os.path.splitext(os.path.basename(path))[0]
        self.output_path = os.path.join(dir_name, f"{base}_kindle.pdf")
        self.lbl_save_path.setText(os.path.basename(self.output_path))

    def process_start(self):
        if not self.pdf_path: return
        if os.path.exists(self.output_path):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Overwrite?")
            msg_box.setText(f"File exists:\n{os.path.basename(self.output_path)}\n\nOverwrite it?")
            msg_box.setStyleSheet(f"QLabel{{color: {COLOR_PRIMARY}; font-weight: bold;}} QPushButton{{background-color: {COLOR_ACCENT}; color: {COLOR_PRIMARY};}}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msg_box.exec() == QMessageBox.StandardButton.No: return

        self.btn_start.setEnabled(False)
        self.start_time = time.time()
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_ui)
        self.signals.finished.connect(self.on_complete)
        threading.Thread(target=self.run_logic, daemon=True).start()

    def update_ui(self, msg, val):
        elapsed = int(time.time() - self.start_time)
        m, s = divmod(elapsed, 60)
        self.status_lbl.setText(msg)
        self.progress.setFormat(f"%p% - {m:02d}:{s:02d}")
        self.progress.setValue(int(val * 100))

    def on_complete(self):
        self.btn_start.setEnabled(True)
        self.status_lbl.setText("Complete!")
        if self.cb_open.isChecked():
            if self.os_name == "Windows": os.startfile(self.output_path)
            else: subprocess.run(["open", self.output_path])

    def run_logic(self):
        m_list = [["1072", "1448", "300"], ["1236", "1648", "300"], ["1264", "1680", "300"], ["1860", "2480", "300"]]
        m = m_list[self.ui_model.currentIndex()]
        zoom = self.ui_zoom.currentText().split(" ")[0]
        is_p = "Preserve" in self.ui_layout.currentText()
        cmd = [self.k2_path, self.pdf_path, "-x", "-w", m[0], "-h", m[1], "-dpi", m[2]]
        if is_p: cmd.extend(["-wrap-", "-ws", "-1", "-bp"])
        else: cmd.extend(["-as", "-bp"])
        if self.cb_color.isChecked(): cmd.append("-c")
        cmd.extend(["-mag", zoom, "-y", "-o", self.output_path])

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                match = re.search(r"PAGE\s+(\d+)\s+of\s+(\d+)", line)
                if match:
                    c, t = int(match.group(1)), int(match.group(2))
                    self.signals.progress.emit(f"Page {c}/{t}", c/t)
            p.wait()
            self.signals.finished.emit()
        except: self.signals.finished.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KindleizerApp()
    window.show()
    sys.exit(app.exec())