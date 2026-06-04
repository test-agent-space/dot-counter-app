import sys
import os
import cv2
import numpy as np
from PIL import Image
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QSlider, QColorDialog,
    QFormLayout, QGroupBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush

from detector import count_dots

class DetectionWorker(QObject):
    finished = Signal(int, list, np.ndarray)
    
    def __init__(self, image_path, params):
        super().__init__()
        self.image_path = image_path
        self.params = params
        
    def run(self):
        count, contours, mask = count_dots(**self.params)
        self.finished.emit(count, contours, mask)

class DotCounterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dot Counter App")
        self.resize(1000, 700)
        
        self.image_path = None
        self.original_pixmap = None
        self.overlay_pixmap = None
        
        self.params = {
            "image_path": "",
            "target_color_bgr": (217, 83, 42),  # Default blue BGR
            "color_tolerance": 15,
            "min_area": 3.0,
            "area_ratio_min": 0.5,
            "area_ratio_max": 2.0,
            "circularity_thresh": 0.7
        }
        
        self.worker_thread = QThread()
        self.worker = None
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left: Image View
        image_layout = QVBoxLayout()
        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_label.setMinimumSize(600, 500)
        image_layout.addWidget(self.image_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self.update_overlay)
        image_layout.addWidget(QLabel("Overlay Opacity:"))
        image_layout.addWidget(self.opacity_slider)
        
        main_layout.addLayout(image_layout, stretch=3)
        
        # Right: Controls
        controls_layout = QVBoxLayout()
        
        self.btn_load = QPushButton("Load Image")
        self.btn_load.clicked.connect(self.load_image)
        controls_layout.addWidget(self.btn_load)
        
        self.lbl_count = QLabel("Count: 0")
        self.lbl_count.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        self.lbl_count.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(self.lbl_count)
        
        # Parameter Group
        param_group = QGroupBox("Parameters")
        param_layout = QFormLayout()
        
        # Color Picker
        self.btn_color = QPushButton("Choose Target Color")
        self.btn_color.setStyleSheet(f"background-color: rgb({self.params['target_color_bgr'][2]}, {self.params['target_color_bgr'][1]}, {self.params['target_color_bgr'][0]}); color: white; font-weight: bold;")
        self.btn_color.clicked.connect(self.choose_color)
        param_layout.addRow("Target Color:", self.btn_color)
        
        self.slider_tol = QSlider(Qt.Horizontal)
        self.slider_tol.setRange(1, 50)
        self.slider_tol.setValue(self.params["color_tolerance"])
        self.slider_tol.valueChanged.connect(lambda v: self.update_param("color_tolerance", v))
        param_layout.addRow("Color Tolerance (Hue):", self.slider_tol)
        
        self.spin_area_min = QDoubleSpinBox()
        self.spin_area_min.setRange(0.1, 10.0)
        self.spin_area_min.setValue(3.0)
        self.spin_area_min.setSingleStep(0.5)
        self.spin_area_min.valueChanged.connect(lambda v: self.update_param("min_area", v))
        param_layout.addRow("Min Area (px):", self.spin_area_min)
        
        self.spin_area_ratio_min = QDoubleSpinBox()
        self.spin_area_ratio_min.setRange(0.1, 1.0)
        self.spin_area_ratio_min.setValue(0.5)
        self.spin_area_ratio_min.setSingleStep(0.1)
        self.spin_area_ratio_min.valueChanged.connect(lambda v: self.update_param("area_ratio_min", v))
        param_layout.addRow("Area Ratio Min:", self.spin_area_ratio_min)
        
        self.spin_area_ratio_max = QDoubleSpinBox()
        self.spin_area_ratio_max.setRange(1.0, 5.0)
        self.spin_area_ratio_max.setValue(2.0)
        self.spin_area_ratio_max.setSingleStep(0.1)
        self.spin_area_ratio_max.valueChanged.connect(lambda v: self.update_param("area_ratio_max", v))
        param_layout.addRow("Area Ratio Max:", self.spin_area_ratio_max)
        
        self.spin_circularity = QDoubleSpinBox()
        self.spin_circularity.setRange(0.1, 1.0)
        self.spin_circularity.setValue(0.7)
        self.spin_circularity.setSingleStep(0.05)
        self.spin_circularity.valueChanged.connect(lambda v: self.update_param("circularity_thresh", v))
        param_layout.addRow("Circularity Thresh:", self.spin_circularity)
        
        param_group.setLayout(param_layout)
        controls_layout.addWidget(param_group)
        
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout, stretch=1)
        
    def choose_color(self):
        initial_rgb = (
            self.params["target_color_bgr"][2], 
            self.params["target_color_bgr"][1], 
            self.params["target_color_bgr"][0]
        )
        color = QColorDialog.getColor(QColor(*initial_rgb), self, "Select Target Dot Color")
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            self.params["target_color_bgr"] = (b, g, r)
            self.btn_color.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); color: white; font-weight: bold;")
            self.schedule_update()
            
    def update_param(self, name, value):
        self.params[name] = value
        self.schedule_update()
        
    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self.image_path = path
            self.params["image_path"] = path
            
            # Load pixmap
            self.original_pixmap = QPixmap(path)
            
            # Scale pixmap to fit label while keeping aspect ratio
            scaled_pixmap = self.original_pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            
            self.schedule_update()
            
    def schedule_update(self):
        if not self.image_path:
            return
            
        # Debounce updates
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()
        else:
            self._update_timer = QTimer(self)
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self.run_detection)
            
        self._update_timer.start(100) # 100ms debounce
        
    def run_detection(self):
        self.lbl_count.setText("Count: Processing...")
        
        # Clean up old worker if any
        if self.worker:
            self.worker.finished.disconnect()
            self.worker.deleteLater()
            self.worker = None
            
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
            
        self.worker = DetectionWorker(self.image_path, self.params)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_detection_finished)
        
        self.worker_thread.start()
        
    def on_detection_finished(self, count, contours, mask):
        self.lbl_count.setText(f"Count: {count}")
        
        # Generate overlay pixmap
        self.generate_overlay(count, contours, mask)
        self.update_overlay()
        
    def generate_overlay(self, count, contours, mask):
        if self.original_pixmap is None:
            return
            
        # Create a QImage from the mask or draw contours
        # We want to draw the contours on a transparent background
        width = self.original_pixmap.width()
        height = self.original_pixmap.height()
        
        # We need to map the original image size to the mask size
        pil_img = Image.open(self.image_path).convert('RGB')
        orig_w, orig_h = pil_img.size
        
        overlay_img = QImage(orig_w, orig_h, QImage.Format_ARGB32)
        overlay_img.fill(Qt.transparent)
        
        painter = QPainter(overlay_img)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw contours
        pen = QPen(QColor(255, 0, 0, 200), 2)
        painter.setPen(pen)
        brush = QBrush(QColor(255, 0, 0, 80))
        painter.setBrush(brush)
        
        for cnt in contours:
            # cnt is in image coordinates
            points = [ (int(p[0][0]), int(p[0][1])) for p in cnt ]
            painter.drawPolygon(points)
            
        painter.end()
        
        self.overlay_pixmap = QPixmap.fromImage(overlay_img)
        
    def update_overlay(self):
        if self.original_pixmap is None or self.overlay_pixmap is None:
            return
            
        # Create a combined image based on opacity slider
        opacity = self.opacity_slider.value() / 100.0
        
        combined = self.original_pixmap.copy()
        painter = QPainter(combined)
        painter.setOpacity(opacity)
        painter.drawPixmap(0, 0, self.overlay_pixmap.scaled(
            combined.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        painter.end()
        
        # Scale to fit label
        scaled = combined.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap:
            scaled = self.original_pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            # Re-trigger overlay update to match new scale if needed, 
            # but update_overlay handles scaling the overlay to the label.
            self.update_overlay()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DotCounterApp()
    window.show()
    sys.exit(app.exec())