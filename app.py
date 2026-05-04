from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QSize, QPointF, QRectF, QStandardPaths, QTimer
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QIcon, QPainterPath, QPainter, QPen, QColor, QFont, QConicalGradient, QBrush
# import soundfile as sf
from pydub import AudioSegment
import pyqtgraph as pg
import numpy as np
import os, shutil
from pathlib import Path

from styles import *
import denoiser
import metrics_calculator

class GradientDialGauge(pg.GraphicsObject):
    def __init__(self, title, tick_values):
        super().__init__()
        self.title = title
        self.min_val = tick_values[0]
        self.max_val = tick_values[-1]
        self.tick_values = tick_values
        self.total_ticks = len(tick_values)
        self.value = 0.0
        # The main dial area
        self.rect = QRectF(-100, -100, 200, 200)

    def setValue(self, value):
        self.value = max(self.min_val, min(self.max_val, value))
        self.update()

    def paint(self, p:QPainter, *args):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Setup the Multi-Color Gradient Arc (Background)
        start_angle = 135
        total_span = 270
        
        gradient_path = QPainterPath()
        gradient_path.arcMoveTo(self.rect, start_angle)
        gradient_path.arcTo(self.rect, start_angle, total_span)
        
        # Conical gradient needs to be aligned with the new start
        gradient = QConicalGradient(QPointF(0, 0), 90)
        gradient.setColorAt(0, QColor(255, 0, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 0))
        gradient.setColorAt(0.9, QColor(0, 255, 0))
        gradient.setColorAt(1, Qt.GlobalColor.transparent)

        # Draw the main colored track
        pen = QPen(QBrush(gradient), 20)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap) # Keeps the gap edges clean
        p.setPen(pen)
        p.drawPath(gradient_path)

        # Draw Ticks and Labels
        p.setPen(QPen(Qt.GlobalColor.black, 1.5))
        p.setFont(QFont("Arial", 8))
        
        for tick in self.tick_values:
            percentage = (tick - self.min_val) / (self.max_val - self.min_val)
            angle_deg = (start_angle+90) + (total_span * percentage)
            
            p.save()
            p.rotate(-angle_deg)
            p.drawLine(0, 91, 0, 109) # Draw tick at the top of the rotated system
            
            # Position the text
            p.rotate(180)
            p.translate(0, -120)
            p.scale(-1,1)
            text_rect = QRectF(-15, -7, 30, 14)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{tick:.2f}")
            p.restore()

        # 3. Needle Logic (Updated for new angles)
        val_percentage = (self.value - self.min_val) / (self.max_val - self.min_val)
        needle_angle = start_angle + (total_span * val_percentage)
        needle_rad = np.deg2rad(needle_angle)
        
        # Draw Needle
        needle_pen = QPen(QColor(50, 50, 50), 4)
        needle_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(needle_pen)
        needle_end = QPointF(85 * np.cos(needle_rad), -85 * np.sin(needle_rad))
        p.drawLine(QPointF(0, 0), needle_end)

        # Center Pivot (Cover the needle base)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(50, 50, 50))
        p.drawEllipse(QPointF(0,0), 18, 18)

        # Score Text (Centered in the "mouth" of the gauge)
        p.setPen(QColor(50, 50, 50))
        p.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        p.scale(1,-1)
        # Moving it slightly lower so it sits in the gap
        p.drawText(QRectF(-50, 50, 100, 40), Qt.AlignmentFlag.AlignCenter, f"{self.value:.2f}")

    def boundingRect(self):
        return self.rect

class ResponsiveFrame(QFrame):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        return super().mousePressEvent(event)
    
class UploadCard:
    def __init__(self, outer_layout:QLayout, title, remarks, bind_fn):
        self.UPLOAD_IMG = QIcon("./assets/upload-white.png")
        self.outer_layout = outer_layout
        self.sub_title = QLabel(title)
        self.card = ResponsiveFrame()
        self.card.setStyleSheet(UPLOAD_CARD_STYLESHEET)
        card_layout = QHBoxLayout(self.card)
        self.upload_btn = QPushButton("  Upload")
        self.upload_btn.setIcon(self.UPLOAD_IMG)
        self.upload_btn.setIconSize(QSize(20,20))
        desc_label = QLabel(remarks)

        self.card.clicked.connect(bind_fn)
        self.upload_btn.clicked.connect(bind_fn)

        card_layout.addWidget(self.upload_btn, 1)
        card_layout.addWidget(desc_label, 3)

    def pack(self):
        self.outer_layout.addWidget(self.sub_title)
        self.outer_layout.addWidget(self.card)
    
    def setTitle(self, text):
        self.upload_btn.setText(text)

class MediaPlayer(QFrame):
    all_players = []

    def __init__(self, title, outer_layout:QLayout, outer_window:QWidget):
        super().__init__()

        MediaPlayer.all_players.append(self)
        self.outer_layout = outer_layout
        self.outer_window = outer_window
        self.PAUSE_IMG = QIcon("./assets/pause.png")
        self.PLAY_IMG = QIcon("./assets/play.png")

        self.sliderGrabbed = False
        self.last_media_state = None

        self.setStyleSheet(MEDIA_PLAYER_STYLESHEET)
        self.inner_layout = QVBoxLayout(self)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.plot_widget = pg.PlotWidget(title=title)
        self.plot_widget.setBackground("#E3E0FB")
        self.curve = self.plot_widget.plot(pen="#6452E7")
        self.playhead = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen(color=(255,44,103), width=2))
        self.plot_widget.addItem(self.playhead)
        self.plot_widget.setFixedHeight(150)

        self.controls_frame = QFrame()
        controls_layout = QHBoxLayout(self.controls_frame)
        controls_layout.setSpacing(10)
        self.controls_frame.setStyleSheet(CONTROL_FRAME_STYLESHEET)

        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.PAUSE_IMG)
        self.btn_play.setIconSize(QSize(35,30))
        self.btn_play.setEnabled(False)
        
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setEnabled(False)
        self.seek_slider.setMinimumWidth(100)

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.seek_slider)

        self.btn_play.clicked.connect(self.toggle_playback)
        
        # Player signals to update the slider
        self.media_player.durationChanged.connect(self.update_slider_range)
        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.mediaStatusChanged.connect(self.handle_status_change)
        self.seek_slider.sliderPressed.connect(self.set_slider_grabbed)
        self.seek_slider.sliderMoved.connect(self.set_audio_position)
        self.seek_slider.sliderReleased.connect(self.set_audio_position)
        self.seek_slider.sliderReleased.connect(self.reset_slider_grabbed)

    def pack(self):
        self.outer_layout.addWidget(self)
        self.inner_layout.addWidget(self.plot_widget)
        self.inner_layout.addWidget(self.controls_frame)
        self.hide()

    def set_slider_grabbed(self):
        self.sliderGrabbed = True
        self.last_media_state = self.media_player.playbackState()
        self.media_player.pause()
    
    def reset_slider_grabbed(self):
        self.sliderGrabbed = False
        if (self.last_media_state == QMediaPlayer.PlaybackState.PlayingState):
            self.media_player.play()

    def load_audio(self, path=None):
        if (path == None):
            path, _ = QFileDialog.getOpenFileName(self.outer_window, "Open Audio", "", "Audio Files (*.wav *.mp3)")
        if path:
            # Update Audio Player
            self.show()
            self.media_player.setSource(QUrl.fromLocalFile(path))

            audio = AudioSegment.from_file(path)
            if audio.channels>1:
                audio = audio.set_channels(1)
            data = np.array(audio.get_array_of_samples()).astype(np.float32)
            
            # Normalize based on bit depth (usually 16-bit)
            if audio.sample_width == 2:
                data /= 32768.0
            elif audio.sample_width == 4:
                data /= 2147483648.0
            samplerate = audio.frame_rate

            time_secs = np.arange(len(data)) / samplerate
            self.curve.setData(time_secs, data)
            
            self.btn_play.setEnabled(True)
            self.btn_play.setIcon(self.PAUSE_IMG)
            self.seek_slider.setEnabled(True)

            return path

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.btn_play.setIcon(self.PAUSE_IMG)
        else:
            for player in MediaPlayer.all_players:
                if player.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    player.toggle_playback()
            self.media_player.play()
            self.btn_play.setIcon(self.PLAY_IMG)
    
    def update_slider_range(self, duration_ms):
        self.seek_slider.setRange(0, duration_ms)
        self.plot_widget.setXRange(0, duration_ms/1000.0)

    def update_slider_position(self, position_ms):
        if (not self.sliderGrabbed):
            self.playhead.setValue(position_ms/1000.0)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(position_ms)
            self.seek_slider.blockSignals(False)

    def set_audio_position(self, position_ms=None):
        if (position_ms==None):
            position_ms = self.seek_slider.value()
        self.media_player.setPosition(position_ms)
        self.playhead.setValue(position_ms/1000.0)
    
    def handle_status_change(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.btn_play.setIcon(self.PAUSE_IMG)
            self.media_player.setPosition(0)
            self.seek_slider.setValue(0)
            self.playhead.setValue(0)

class MetricPlotGauge(pg.PlotWidget):
    def __init__(self, title, ticks):
        super().__init__(title=f'''<span style="color: #FF2C67; font-size: 16pt; font-weight: bold;">{title} Score</span>''')
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.hideButtons()
        self.setRange(xRange=[-130, 130], yRange=[-120, 120], padding=0.05)
        self.setBackground(None)
        self.setAspectLocked(True)
        self.hideAxis('left')
        self.hideAxis('bottom')
        self.gauge = GradientDialGauge(title, ticks)
        self.addItem(self.gauge)

    def setValue(self, value):
        self.gauge.setValue(value)


class DenoiserFrame(QWidget):
    def __init__(self, panel_frame:QFrame, scroll_area:QScrollArea):
        super().__init__()
        self.scrollArea = scroll_area
        self.audio_path = None
        self.cleaned_audio_path_cache = None
        self.DOWNLOAD_IMG = QIcon("./assets/download-white.png")
        self.TICK_IMG = QIcon("./assets/tick-mark.png")

        layout = QVBoxLayout()
        self.setLayout(layout)
        panel_frame.setStyleSheet(DENOISE_PANEL_STYLESHEET)

        frame1 = QFrame()
        frame1.setStyleSheet(DENOISE_PANEL_SUBFRAME_STYLESHEET)
        layout1 = QVBoxLayout(frame1)

        title = QLabel("Audio Denoiser")
        title.setObjectName("heading")
        self.upload_card = UploadCard(layout1, "Upload Noisy Audio File", "200MB per file • WAV, MP3", self.load_audio)
        self.clean_btn = QPushButton("Clean Audio")
        self.clean_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)

        self.player_original = MediaPlayer("Original Audio", layout1, self)
        self.player_processed = MediaPlayer("Denoised Audio", layout1, self)

        self.download_btn = QPushButton(" Save Cleaned Audio")
        self.download_btn.setIcon(self.DOWNLOAD_IMG)
        self.download_btn.setIconSize(QSize(25,25))
        self.download_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)
        
        self.save_acknowledge = QPushButton(" Saved Successfully!")
        self.save_acknowledge.setIcon(self.TICK_IMG)
        self.save_acknowledge.setIconSize(QSize(25,25))
        self.save_acknowledge.setStyleSheet(SAVE_ACKNOWLEDGE_STYLESHEET)

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(frame1)
        self.upload_card.pack()
        self.player_original.pack()
        layout1.addWidget(self.clean_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.player_processed.pack()
        layout1.addWidget(self.download_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout1.addWidget(self.save_acknowledge, alignment=Qt.AlignmentFlag.AlignCenter)
        layout1.addStretch()

        self.clean_btn.hide()
        self.download_btn.hide()
        self.save_acknowledge.hide()

        self.clean_btn.clicked.connect(self.clean_audio)
        self.download_btn.clicked.connect(self.save_cleaned_audio)
    
    def scroll_to_bottom(self):
        v_bar = self.scrollArea.verticalScrollBar()
        QTimer.singleShot(20, lambda: v_bar.setValue(v_bar.maximum()))
    
    def load_audio(self):
        path = self.player_original.load_audio()
        if path:
            self.clean_btn.show()
            self.download_btn.hide()
            self.save_acknowledge.hide()
            self.player_processed.hide()
            if path.count('/')>=1: delim = '/'
            else: delim = '\\'
            self.upload_card.setTitle("  " + path.split(delim)[-1])
            self.audio_path = path
            self.cleaned_audio_path_cache = None

    def clean_audio(self):
        self.cleaned_audio_path_cache = os.path.abspath(f"./audio-cache/cleaned-audio-cache")
        extension = denoiser.denoise_and_save_audio(self.audio_path, self.cleaned_audio_path_cache)

        self.player_processed.load_audio(f"{self.cleaned_audio_path_cache}.{extension}")
        self.clean_btn.hide()
        self.download_btn.show()
        self.scroll_to_bottom()
    
    def save_cleaned_audio(self):
        desktop_locations = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DesktopLocation)
        if not desktop_locations:
            desktop_path = Path.home()
        else:
            desktop_path = Path(desktop_locations[0])

        original_full_filename = self.audio_path.split('/')[-1] if self.audio_path.count('/')>=1 else self.audio_path.split('\\')[-1]
        original_filename = "".join(original_full_filename.split('.')[:-1])
        original_extension = original_full_filename.split('.')[-1]
        suggested_file_name = f"{original_filename}-cleaned.{original_extension}"
        initial_path = str(desktop_path / suggested_file_name)

        file_destination, _ = QFileDialog.getSaveFileName(
            self, "Save Cleaned Audio",
            initial_path,
            f"{original_extension.upper()} Files (*.{original_extension.lower()});;All Files (*)"
        )

        if file_destination:
            try:
                shutil.copy2(self.cleaned_audio_path_cache, file_destination)
                QMessageBox.information(self, "Success", f"File saved to:\n{file_destination}")
                self.download_btn.hide()
                self.save_acknowledge.show()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

class MetricsFrame(QWidget):
    def __init__(self, panel_frame:QFrame, scroll_area:QScrollArea):
        super().__init__()
        self.scroll_area = scroll_area
        self.audio_paths = [None, None]

        layout = QVBoxLayout()
        self.setLayout(layout)
        panel_frame.setStyleSheet(DENOISE_PANEL_STYLESHEET)

        frame1 = QFrame()
        frame1.setStyleSheet(DENOISE_PANEL_SUBFRAME_STYLESHEET)
        layout1 = QVBoxLayout(frame1)

        title = QLabel("View Processing Metrics")
        title.setObjectName("heading")

        self.metrics_frame = QFrame()
        self.metrics_frame.setStyleSheet(METRICS_FRAME_STYLESHEET)
        self.metrics_frame.setFixedHeight(300)
        self.metrics_layout = QHBoxLayout(self.metrics_frame)

        self.pesq_plot = MetricPlotGauge("PESQ", [1, 2, 2.5, 3, 3.5, 4])
        self.stoi_plot = MetricPlotGauge("STOI", [0, 0.5, 0.75, 1])

        self.metrics_layout.addWidget(self.pesq_plot)
        self.metrics_layout.addWidget(self.stoi_plot)

        self.upload_card_noisy = UploadCard(layout1, "Upload Noisy Audio File", "200MB per file • WAV, MP3", self.load_audio_noisy)
        self.upload_card_clear = UploadCard(layout1, "Upload Clean Reference Audio File", "200MB per file • WAV, MP3", self.load_audio_clear)
        self.player_noisy = MediaPlayer("Denoised Audio", layout1, self)
        self.player_clear = MediaPlayer("Reference Clean Audio", layout1, self)
        self.calculate_btn = QPushButton("Calculate Metrics")
        self.calculate_btn.setMaximumWidth(150)
        self.calculate_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(frame1)
        layout1.addWidget(self.metrics_frame)
        self.upload_card_noisy.pack()
        self.player_noisy.pack()
        self.upload_card_clear.pack()
        self.player_clear.pack()
        layout1.addWidget(self.calculate_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout1.addStretch()

        self.metrics_frame.hide()
        self.calculate_btn.hide()

        self.calculate_btn.clicked.connect(self.calculate_metrics)
    
    def load_audio(self, media_player:MediaPlayer, upload_card:UploadCard, audio_path_var_idx, path=None, alias=None):
        path = media_player.load_audio(path)
        if path:
            if alias==None:
                alias = path
            if alias.count('/')>=1: delim = '/'
            else: delim = '\\'
            upload_card.setTitle("  " + alias.split(delim)[-1])

            self.audio_paths[audio_path_var_idx] = path
            self.metrics_frame.hide()

        for path in self.audio_paths:
            if path==None:
                self.calculate_btn.hide()
                return
        self.calculate_btn.show()
    
    def load_audio_noisy(self, path=None):
        self.load_audio(self.player_noisy, self.upload_card_noisy, 0, path)
        self.cleaned_path = os.path.abspath(f"./audio-cache/cleaned-audio-cache-metrics")
        print(self.cleaned_path)
        self.extension = denoiser.denoise_and_save_audio(self.audio_paths[0], self.cleaned_path)
        self.load_audio(self.player_noisy, self.upload_card_noisy, 0, f"{self.cleaned_path}.{self.extension}", self.audio_paths[0])

    def load_audio_clear(self):
        self.load_audio(self.player_clear, self.upload_card_clear, 1)

    def calculate_metrics(self):
        pesq, stoi = metrics_calculator.get_metrics(self.audio_paths[1], f"{self.cleaned_path}.{self.extension}")
        self.pesq_plot.setValue(pesq)
        self.stoi_plot.setValue(stoi)
        self.metrics_frame.show()
        self.calculate_btn.hide()
        self.scroll_area.verticalScrollBar().setValue(0)

class SettingsFrame(QWidget):
    def __init__(self, panel_frame:QFrame, scroll_area:QScrollArea):
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)
        panel_frame.setStyleSheet(DENOISE_PANEL_STYLESHEET)

        frame1 = QFrame()
        frame1.setStyleSheet(DENOISE_PANEL_SUBFRAME_STYLESHEET)
        layout1 = QVBoxLayout(frame1)

        title = QLabel("Settings")
        title.setObjectName("heading")

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(frame1)
        layout1.addStretch()
        layout1.addWidget(QLabel("Stuff to be added later"), alignment=Qt.AlignmentFlag.AlignCenter)
        layout1.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Denoiser App")
        self.resize(1100, 600)
        self.WINDOWS = (DenoiserFrame, MetricsFrame, SettingsFrame)
        self.createdWindows = [None, None, None]
        self.currentWindow = -1

        main_central_widget = QWidget(self)
        main_central_widget.setStyleSheet(ROOT_LIGHT_STYLESHEET)
        self.setCentralWidget(main_central_widget)
        self.outer_layout = QVBoxLayout(main_central_widget)
        self.outer_layout.setContentsMargins(0,0,0,0)
        self.outer_layout.setSpacing(0)

        self.top_panel_abstract = QVBoxLayout()
        top_panel_frame = QFrame()
        top_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET)
        self.top_panel_abstract.addWidget(top_panel_frame)

        top_panel = QVBoxLayout(top_panel_frame)
        top_panel_frame.setStyleSheet(TITLE_STYLESHEET)
        label = QLabel("Denoise App")
        top_panel.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_frame = QHBoxLayout()
        self.left_panel_abstract = QVBoxLayout()
        left_panel_frame = QFrame()
        left_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET + SIDE_PANEL_STYLESHEET)
        self.left_panel_abstract.addWidget(left_panel_frame)

        left_panel = QVBoxLayout(left_panel_frame)
        denoise = QPushButton("Remove Noise")
        metrics = QPushButton("View Metrics")
        settings = QPushButton("Settings")
        self.window_switch_buttons = (denoise, metrics, settings)

        denoise.clicked.connect(lambda: self.switch_window(0))
        metrics.clicked.connect(lambda: self.switch_window(1))
        settings.clicked.connect(lambda: self.switch_window(2))

        left_panel.addWidget(denoise)
        left_panel.addWidget(metrics)
        left_panel.addWidget(settings)
        left_panel.addStretch(1)
        left_panel.setSpacing(0)
        left_panel.setContentsMargins(0,0,0,0)

        self.right_panel_abstract = QVBoxLayout()
        self.window_frame = QFrame()
        self.window_frame.setStyleSheet(PANEL_BORDER_STYLESHEET)
        self.window_layout = QVBoxLayout(self.window_frame)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.window_frame)
        self.scrollArea.setWidgetResizable(True)

        self.right_panel_abstract.addWidget(self.scrollArea)

        self.main_frame.addLayout(self.left_panel_abstract, 1)
        self.main_frame.addLayout(self.right_panel_abstract, 4)

        self.outer_layout.addLayout(self.top_panel_abstract, 1)
        self.outer_layout.addLayout(self.main_frame, 9)

        self.switch_window(0)
    
    def switch_window(self, window):
        if (self.currentWindow != window):
            if (self.createdWindows[window] == None):
                newCreatedWindow = self.WINDOWS[window](self.window_frame, self.scrollArea) # Create the class object
                self.window_layout.addWidget(newCreatedWindow)
                self.createdWindows[window] = newCreatedWindow
            else:
                self.window_layout.addWidget(self.createdWindows[window])
                self.currentWindow = window
            
            for i in range(3):
                if self.createdWindows[i]:
                    self.createdWindows[i].hide()
                    self.window_switch_buttons[i].setStyleSheet(SIDE_PANEL_STYLESHEET)
            self.createdWindows[window].show()
            self.window_switch_buttons[window].setStyleSheet(SIDE_PANEL_STYLESHEET + SELECTED_WINDOW_BUTTON_STYLESHEET)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()