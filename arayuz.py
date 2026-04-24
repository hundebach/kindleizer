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
COLOR_BG = "#FBF0D9"
COLOR_PRIMARY = "#30281F"
COLOR_SECONDARY = "#F2E3C6"
COLOR_ACCENT = "#D4C4A9"
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
        
        # Sürükle bırak için pencereyi yetkilendir
        self.setAcceptDrops(True)
        
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.k2_name = "k2pdfopt.exe" if self.os_name == "Windows" else "k2pdfopt"
        self.k2_path = os.path.join(self.base_path, self.k2_name)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Kindleizer v1.4")
        self.setFixedSize(650, 900) # Copyright için biraz yer açtık
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 20, 30, 15)
        main_layout.setSpacing(12)

        # 1. ÜST BAR (Ko-fi)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.btn_kofi = QPushButton("☕ Support Kindleizer")
        self.btn_kofi.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_kofi.setFixedSize(160, 35)
        self.btn_kofi.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT}; color: {COLOR_PRIMARY}; border-radius: 17px; font-weight: bold; font-size: 12px; }} QPushButton:hover {{ background-color: #C4B49A; }}")
        self.btn_kofi.clicked.connect(lambda: webbrowser.open("https://ko-fi.com/hundebach")) 
        top_bar.addWidget(self.btn_kofi)
        main_layout.addLayout(top_bar)

        # 2. DROP ALANI
        self.drop_frame = QFrame()
        self.drop_frame.setFixedSize(590, 110)
        self.drop_frame.setStyleSheet(f"border: 2px dashed {COLOR_ACCENT}; border-radius: 15px; background-color: {COLOR_SECONDARY};")
        drop_layout = QVBoxLayout(self.drop_frame)
        self.lbl_drop = QLabel("Drag & Drop PDF File Here\nor click to browse")
        self.lbl_drop.setFont(QFont("Helvetica", 13, QFont.Weight.Bold))
        self.lbl_drop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop.setStyleSheet(f"color: {COLOR_PRIMARY}; border: none;")
        drop_layout.addWidget(self.lbl_drop)
        self.drop_frame.mousePressEvent = lambda e: self.select_pdf()
        main_layout.addWidget(self.drop_frame)

        # 3. SAVE LOCATION
        save_box = QVBoxLayout()
        lbl_save_title = QLabel("SAVE OPTIMIZED PDF TO:")
        lbl_save_title.setFont(QFont("Helvetica", 10, QFont.Weight.Bold))
        lbl_save_title.setStyleSheet(f"color: {COLOR_PRIMARY};")
        save_box.addWidget(lbl_save_title)
        save_row = QHBoxLayout()
        self.lbl_save_path = QLabel("Select a file to set destination...")
        self.lbl_save_path.setFixedHeight(40)
        self.lbl_save_path.setStyleSheet(f"background-color: {COLOR_SECONDARY}; border: 1px solid {COLOR_ACCENT}; border-radius: 8px; padding-left: 10px; color: {COLOR_PRIMARY};")
        btn_save = QPushButton("Browse")
        btn_save.setFixedSize(80, 40)
        btn_save.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: {COLOR_BG}; border-radius: 8px; font-weight: bold;")
        btn_save.clicked.connect(self.select_output_path)
        save_row.addWidget(self.lbl_save_path)
        save_row.addWidget(btn_save)
        save_box.addLayout(save_row)
        main_layout.addLayout(save_box)

        # 4. SETTINGS
        settings_group = QFrame()
        settings_group.setStyleSheet(f"background-color: {COLOR_SECONDARY}; border-radius: 15px; border: 1px solid {COLOR_ACCENT};")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(20, 15, 20, 15)
        settings_layout.setSpacing(12)

        self.ui_model = self.add_detailed_setting(settings_layout, "Select Kindle Device Model:", [
            "Kindle Basic (6\" Screen / 300 PPI)",
            "Kindle Paperwhite (6.8\" Screen / 300 PPI)",
            "Kindle Oasis / Colorsoft (7\" Screen / 300 PPI)",
            "Kindle Scribe (10.2\" Screen / 300 PPI / Large Display)",
            "Legacy Kindle (Older low-resolution models)"
        ])
        self.ui_zoom = self.add_detailed_setting(settings_layout, "Adjust Text Magnification (Zoom %):", [
            "1.00 - Original Size (Smallest)",
            "1.15 - Slight Increase (Better for clear eyesight)",
            "1.30 - Large Text (Recommended for multi-column academic papers)",
            "1.45 - Maximum Zoom (E-book like experience)"
        ], default_idx=2)
        self.ui_layout = self.add_detailed_setting(settings_layout, "Specify PDF Output Layout Strategy:", [
            "Reflow - Smart text flow (Fastest, best for text-only books)",
            "Preserve Layout - Keep original structure (Optimized for graphs and formulae)"
        ])
        main_layout.addWidget(settings_group)

        # 5. OPTIONS
        opt_layout = QHBoxLayout()
        self.cb_color = QCheckBox("Preserve colors (For Colorsoft/Scribe)")
        self.cb_color.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold;")
        self.cb_open = QCheckBox("Open file when finished")
        self.cb_open.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold;")
        opt_layout.addWidget(self.cb_color)
        opt_layout.addWidget(self.cb_open)
        main_layout.addLayout(opt_layout)

        # 6. PROGRESS & LARGE STATUS
        self.progress = QProgressBar()
        self.progress.setFixedHeight(30)
        self.progress.setStyleSheet(f"QProgressBar {{ border: 1px solid {COLOR_ACCENT}; border-radius: 15px; text-align: center; background-color: {COLOR_SECONDARY}; color: {COLOR_PRIMARY}; font-weight: bold; }} QProgressBar::chunk {{ background-color: {COLOR_PRIMARY}; border-radius: 15px; }}")
        main_layout.addWidget(self.progress)

        self.status_lbl = QLabel("Ready to Start Optimization")
        self.status_lbl.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; margin: 5px 0;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setWordWrap(True)
        main_layout.addWidget(self.status_lbl)

        # 7. START BUTTON
        self.btn_start = QPushButton("START OPTIMIZATION")
        self.btn_start.setFixedHeight(75)
        self.btn_start.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.setStyleSheet(f"QPushButton {{ background-color: {COLOR_PRIMARY}; color: {COLOR_BG}; border-radius: 15px; }} QPushButton:hover {{ background-color: #1A1510; }} QPushButton:disabled {{ background-color: #A0A0A0; }}")
        self.btn_start.clicked.connect(self.process_start)
        main_layout.addWidget(self.btn_start)

        # 8. COPYRIGHT FOOTER
        main_layout.addStretch()
        footer_lbl = QLabel("powered by k2pdfopt | created by hundebach")
        footer_lbl.setFont(QFont("Helvetica", 9))
        footer_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_lbl)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files: self.update_paths(files[0])

    def add_detailed_setting(self, parent_layout, label_text, items, default_idx=0):
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; border: none;")
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentIndex(default_idx)
        combo.setFixedHeight(45)
        combo.setStyleSheet(f"QComboBox {{ background-color: {COLOR_BG}; border: 1px solid {COLOR_ACCENT}; border-radius: 8px; padding-left: 10px; color: {COLOR_PRIMARY}; font-size: 13px; }}")
        parent_layout.addWidget(lbl)
        parent_layout.addWidget(combo)
        return combo

    def select_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if file: self.update_paths(file)

    def select_output_path(self):
        if not self.pdf_path: return
        file, _ = QFileDialog.getSaveFileName(self, "Save Optimized PDF", self.output_path, "PDF Files (*.pdf)")
        if file:
            self.output_path = file
            self.lbl_save_path.setText(os.path.basename(file))

    def update_paths(self, path):
        self.pdf_path = path
        self.lbl_drop.setText(f"SELECTED: {os.path.basename(path)}")
        dir_name = os.path.dirname(path)
        base = os.path.splitext(os.path.basename(path))[0]
        self.output_path = os.path.join(dir_name, f"{base}_kindle.pdf")
        self.lbl_save_path.setText(os.path.basename(self.output_path))

    def process_start(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "Error", "Select a PDF file first!")
            return
        if os.path.exists(self.output_path):
            res = QMessageBox.question(self, "Overwrite?", f"The file already exists:\n{os.path.basename(self.output_path)}\n\nOverwrite it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.No: return

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
        self.progress.setFormat(f"%p% Complete - Time: {m:02d}:{s:02d}")
        self.progress.setValue(int(val * 100))

    def on_complete(self):
        self.btn_start.setEnabled(True)
        self.status_lbl.setText("Optimization Complete!")
        if self.cb_open.isChecked():
            if self.os_name == "Windows": os.startfile(self.output_path)
            else: subprocess.run(["open", self.output_path])

    def run_logic(self):
        m_list = [["1072", "1448", "300"], ["1236", "1648", "300"], ["1264", "1680", "300"], ["1860", "2480", "300"], ["758", "1024", "212"]]
        m = m_list[self.ui_model.currentIndex()]
        zoom = self.ui_zoom.currentText().split(" ")[0]
        is_p = "Preserve" in self.ui_layout.currentText()
        color_flag = ["-c"] if self.cb_color.isChecked() else []

        cmd = [self.k2_path, self.pdf_path, "-x", "-w", m[0], "-h", m[1], "-dpi", m[2]]
        if is_p: cmd.extend(["-wrap-", "-ws", "-1", "-bp"])
        else: cmd.extend(["-as", "-bp"])
        cmd.extend(color_flag)
        cmd.extend(["-mag", zoom, "-y", "-o", self.output_path])

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                match = re.search(r"PAGE\s+(\d+)\s+of\s+(\d+)", line)
                if match:
                    c, t = int(match.group(1)), int(match.group(2))
                    self.signals.progress.emit(f"Processing Page {c} of {t}", c/t)
            p.wait()
            self.signals.finished.emit()
        except Exception as e:
            self.signals.progress.emit(f"Error: {str(e)}", 0)
            self.signals.finished.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KindleizerApp()
    window.show()
    sys.exit(app.exec())