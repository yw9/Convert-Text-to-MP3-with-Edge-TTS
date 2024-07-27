import sys
import os
import asyncio
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
                             QLineEdit, QLabel, QFileDialog, QComboBox, QProgressBar, QSlider, QSizePolicy)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QPalette

from edge_tts import list_voices, Communicate

class TTSWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, texts, output_dir, base_filename, voice, rate):
        super().__init__()
        self.texts = texts
        self.output_dir = output_dir
        self.base_filename = base_filename
        self.voice = voice
        self.rate = rate

    async def text_to_speech(self, text, output_file):
        communicate = Communicate(text, self.voice, rate=self.rate)
        await communicate.save(output_file)

    async def process_texts(self):
        for i, text in enumerate(self.texts, 1):
            output_file = os.path.join(self.output_dir, f"{self.base_filename}{i:02d}.mp3")
            await self.text_to_speech(text, output_file)
            self.progress.emit(i)

    def run(self):
        asyncio.run(self.process_texts())
        self.finished.emit()

class TTSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 文本输入
        self.textEdit = QTextEdit()
        self.textEdit.setStyleSheet("font-size: 12pt;")
        layout.addWidget(QLabel("输入文本 (每行一条):"))
        layout.addWidget(self.textEdit)

        # 输出目录
        dirLayout = QHBoxLayout()
        self.dirEdit = QLineEdit()
        self.dirEdit.setMinimumWidth(300)
        dirLayout.addWidget(QLabel("输出目录:"))
        dirLayout.addWidget(self.dirEdit)
        dirButton = QPushButton("选择目录")
        dirButton.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        dirButton.clicked.connect(self.chooseDir)
        dirLayout.addWidget(dirButton)
        layout.addLayout(dirLayout)

        # 基础文件名
        self.nameEdit = QLineEdit("output")
        self.nameEdit.setMinimumWidth(400)
        layout.addWidget(QLabel("文件名:"))
        layout.addWidget(self.nameEdit)

        # 语音选择
        self.voiceCombo = QComboBox()
        self.voiceCombo.setMinimumWidth(400)
        self.loadVoices()
        layout.addWidget(QLabel("选择语音:"))
        layout.addWidget(self.voiceCombo)

        # 语速调整
        rateLayout = QHBoxLayout()
        self.rateSlider = QSlider(Qt.Horizontal)
        self.rateSlider.setRange(-100, 200)
        self.rateSlider.setValue(0)
        self.rateSlider.setTickPosition(QSlider.TicksBelow)
        self.rateSlider.setTickInterval(50)
        self.rateLabel = QLabel("语速: 0%")
        self.rateSlider.valueChanged.connect(self.updateRateLabel)
        rateLayout.addWidget(QLabel("减慢"))
        rateLayout.addWidget(self.rateSlider)
        rateLayout.addWidget(QLabel("加快"))
        layout.addLayout(rateLayout)
        layout.addWidget(self.rateLabel)

        # 进度条
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
                margin: 0.5px;
            }
        """)
        layout.addWidget(self.progressBar)

        # 转换按钮
        convertButton = QPushButton("转换为语音")
        convertButton.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14pt;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        convertButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        convertButton.setMinimumHeight(50)
        convertButton.clicked.connect(self.convertToSpeech)
        layout.addWidget(convertButton)

        self.setLayout(layout)
        self.setGeometry(300, 300, 600, 700)
        self.setWindowTitle('Edge TTS 文本到语音转换')
        self.setStyleSheet("""
            QWidget {
                font-family: Arial, sans-serif;
                font-size: 11pt;
            }
            QLabel {
                font-weight: bold;
            }
        """)
        self.show()

    def loadVoices(self):
        voices = asyncio.run(list_voices())
        for voice in voices:
            short_name = voice['ShortName']
            locale = voice['Locale']
            gender = voice['Gender']
            display_name = f"{short_name} ({locale}, {gender})"
            self.voiceCombo.addItem(display_name, short_name)

    def chooseDir(self):
        dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir:
            self.dirEdit.setText(dir)

    def updateRateLabel(self, value):
        self.rateLabel.setText(f"语速: {value}%")

    def convertToSpeech(self):
        texts = self.textEdit.toPlainText().split('\n')
        texts = [text for text in texts if text.strip()]  # 移除空行
        if not texts:
            print("没有输入文本，请输入文本后再试。")
            return

        output_dir = self.dirEdit.text() or "."
        base_filename = self.nameEdit.text() or "output"
        voice = self.voiceCombo.currentData()
        rate = f"{self.rateSlider.value():+d}%"

        self.progressBar.setMaximum(len(texts))
        self.progressBar.setValue(0)

        self.worker = TTSWorker(texts, output_dir, base_filename, voice, rate)
        self.worker.progress.connect(self.updateProgress)
        self.worker.finished.connect(self.onConversionFinished)
        self.worker.start()

    def updateProgress(self, value):
        self.progressBar.setValue(value)

    def onConversionFinished(self):
        print(f"所有音频文件已保存在目录: {self.dirEdit.text() or '当前目录'}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TTSApp()
    sys.exit(app.exec_())