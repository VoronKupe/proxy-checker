import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QWidget, QFileDialog, QHeaderView, QSlider
)
from PySide6.QtCore import Qt, QThread, Signal, QSemaphore
from PySide6.QtGui import QFont
import sys
from concurrent.futures import ThreadPoolExecutor


class ProxyChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxy Checker - Par Voronkupe")
        self.setGeometry(100, 100, 1000, 700)

        self.proxies = []
        self.results = []
        self.max_latency = 1000  
        self.concurrent_checks = 10


        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E2E;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #2E2E3E;
                border: 1px solid #3E3E5E;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #444466;
            }
            QPushButton:pressed {
                background-color: #555577;
            }
            QTableWidget {
                background-color: #2E2E3E;
                color: #FFFFFF;
                gridline-color: #444466;
                selection-background-color: #444466;
            }
            QHeaderView::section {
                background-color: #3E3E4E;
                color: #FFFFFF;
                padding: 5px;
                border: none;
            }
            QSlider::groove:horizontal {
                background-color: #444466;
                height: 10px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background-color: #3E8EDE;
                border: 1px solid #1E5E9E;
                width: 20px;
                height: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.title_label = QLabel("Proxy Checker")
        self.title_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        self.import_button = self.create_button("Importer Proxies")
        self.import_button.clicked.connect(self.import_proxies)
        self.layout.addWidget(self.import_button)

        self.latency_label = QLabel(f"Latence Maximale : {self.max_latency} ms")
        self.latency_label.setFont(QFont("Arial", 14))
        self.latency_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.latency_label)

        self.latency_slider = QSlider(Qt.Horizontal)
        self.latency_slider.setMinimum(0)
        self.latency_slider.setMaximum(100)
        self.latency_slider.setValue(self.max_latency // 100)
        self.latency_slider.valueChanged.connect(self.update_latency)
        self.layout.addWidget(self.latency_slider)

        self.speed_label = QLabel(f"Vérifications Simultanées : {self.concurrent_checks}")
        self.speed_label.setFont(QFont("Arial", 14))
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(self.concurrent_checks)
        self.speed_slider.valueChanged.connect(self.update_speed)
        self.layout.addWidget(self.speed_slider)

        self.start_button = self.create_button("Start")
        self.start_button.clicked.connect(self.start_checking)
        self.layout.addWidget(self.start_button)

        self.export_button = self.create_button("Exporter les Valides")
        self.export_button.clicked.connect(self.export_valid_proxies)
        self.layout.addWidget(self.export_button)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Proxy", "Statut", "Latence (ms)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setFont(QFont("Arial", 12))
        self.layout.addWidget(self.table)

        self.footer_label = QLabel("Par Voronkupe - 2026")
        self.footer_label.setFont(QFont("Arial", 10))
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet("color: #888888; margin-top: 20px;")
        self.layout.addWidget(self.footer_label)

    def create_button(self, text):
        button = QPushButton(text)
        button.setFont(QFont("Arial", 14))
        return button

    def import_proxies(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Importer Proxies", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "r") as file:
                self.proxies = [line.strip() for line in file.readlines() if line.strip()]
            self.update_status(f"{len(self.proxies)} proxies importés.")

    def update_latency(self, value):
        self.max_latency = value * 100
        self.latency_label.setText(f"Latence Maximale : {self.max_latency} ms")

    def update_speed(self, value):
        self.concurrent_checks = value
        self.speed_label.setText(f"Vérifications Simultanées : {self.concurrent_checks}")

    def update_status(self, message):
        self.title_label.setText(message)

    def start_checking(self):
        if not self.proxies:
            self.update_status("Veuillez importer des proxies d'abord.")
            return

        self.results = []
        self.table.setRowCount(0)
        self.update_status("Vérification en cours...")

        self.thread = ProxyCheckThread(self.proxies, self.max_latency, self.concurrent_checks)
        self.thread.result_ready.connect(self.update_table)
        self.thread.finished.connect(lambda: self.update_status("Vérification terminée."))
        self.thread.start()

    def update_table(self, result):
        self.results.append(result)

        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(result["proxy"]))
        self.table.setItem(row, 1, QTableWidgetItem(result["status"]))
        self.table.setItem(row, 2, QTableWidgetItem(str(result["latency"])))

    def export_valid_proxies(self):
        valid_proxies = [result["proxy"] for result in self.results if result["status"] == "Valide"]
        if not valid_proxies:
            self.update_status("Aucun proxy valide à exporter.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter les Proxies Valides", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "w") as file:
                file.write("\n".join(valid_proxies))
            self.update_status(f"{len(valid_proxies)} proxies valides exportés vers {file_path}.")


class ProxyCheckThread(QThread):
    result_ready = Signal(dict)

    def __init__(self, proxies, max_latency, concurrent_checks):
        super().__init__()
        self.proxies = proxies
        self.max_latency = max_latency
        self.concurrent_checks = concurrent_checks

    def run(self):
        semaphore = QSemaphore(self.concurrent_checks)
        with ThreadPoolExecutor(max_workers=self.concurrent_checks) as executor:
            for proxy in self.proxies:
                semaphore.acquire()
                executor.submit(self.check_proxy, proxy, semaphore)

    def check_proxy(self, proxy, semaphore):
        try:
            proxies = {"http": proxy, "https": proxy}
            response = requests.get("https://www.google.com", proxies=proxies, timeout=self.max_latency / 1000)
            latency = response.elapsed.total_seconds() * 1000
            result = {
                "proxy": proxy,
                "status": "Valide" if latency <= self.max_latency else "Invalide",
                "latency": int(latency),
            }
        except Exception:
            result = {"proxy": proxy, "status": "Invalide", "latency": "N/A"}
        finally:
            self.result_ready.emit(result)
            semaphore.release()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProxyChecker()
    window.show()
    sys.exit(app.exec())
