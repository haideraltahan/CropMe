from PyQt5.QtCore import QDir, Qt, QUrl, QSettings
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QCheckBox,
                             QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget)
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QAction
from PyQt5.QtGui import QIcon

import subprocess
import sys
import os
import cv2
import numpy as np


class VideoWindow(QMainWindow):

    def __init__(self, parent=None):
        super(VideoWindow, self).__init__(parent)
        self.settings = QSettings("CropMe", "CropMe App")
        self.setWindowTitle("CropMe")
        self.directory = self.settings.value("directory", QDir.homePath(), str)
        self.position = 0
        self.frameMovementThreshold = 500
        self.initFrame = -1
        self.finalFrame = -1
        self.latestvideo = ''
        self.autoplay = self.settings.value("autoplay", False, bool)
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        videoWidget = QVideoWidget()

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.initFrameButton = QPushButton()
        self.initFrameButton.setEnabled(False)
        self.initFrameButton.setText('Set Initial Frame')
        self.initFrameButton.clicked.connect(self.setInitFrame)

        self.finalFrameButton = QPushButton()
        self.finalFrameButton.setEnabled(False)
        self.finalFrameButton.setText('Set Final Frame')
        self.finalFrameButton.clicked.connect(self.setFinalFrame)

        self.cropButton = QPushButton()
        self.cropButton.setEnabled(False)
        self.cropButton.setText('Crop Video')
        self.cropButton.clicked.connect(self.crop)

        self.watchnewvid = QPushButton()
        self.watchnewvid.setEnabled(False)
        self.watchnewvid.setText('Watch Cropped Video')
        self.watchnewvid.clicked.connect(self.opencv_playvideo)

        self.deleteButton = QPushButton()
        self.deleteButton.setEnabled(False)
        self.deleteButton.setText('Delete Original Video')
        self.deleteButton.clicked.connect(self.deleteOriginalVideo)

        self.autoplayCheck = QCheckBox("Autoplay after cropping?", self)
        self.autoplayCheck.setChecked(self.settings.value("autoplay", False, bool))
        self.autoplayCheck.stateChanged.connect(self.autoplaySwitch)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.currentTimeLabel = QLabel()
        self.currentTimeLabel.setSizePolicy(QSizePolicy.Preferred,
                                            QSizePolicy.Maximum)
        self.totalTimeLabel = QLabel()
        self.totalTimeLabel.setSizePolicy(QSizePolicy.Preferred,
                                          QSizePolicy.Maximum)

        self.errorLabel = QLabel()
        self.errorLabel.setSizePolicy(QSizePolicy.Preferred,
                                      QSizePolicy.Maximum)

        self.fileName = QLabel()
        self.fileName.setSizePolicy(QSizePolicy.Preferred,
                                      QSizePolicy.Maximum)

        # Create new action
        openAction = QAction(QIcon('open.png'), '&Open', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open movie')
        openAction.triggered.connect(self.openFile)

        # Create exit action
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.exitCall)

        # Create Next Frame action
        fowardAction = QAction(QIcon('SP_ArrowForward'), '&Foward', self)
        fowardAction.setShortcut('.')
        fowardAction.setStatusTip('Next Frame')
        fowardAction.triggered.connect(self.nextFrame)

        # Create Previous Frame action
        backAction = QAction(QIcon('SP_ArrowBack'), '&Back', self)
        backAction.setShortcut(',')
        backAction.setStatusTip('Back Frame')
        backAction.triggered.connect(self.prevFrame)

        # Create Play action
        playAction = QAction(QIcon('space'), '&space', self)
        playAction.setShortcut(' ')
        playAction.setStatusTip('Play/Pause')
        playAction.triggered.connect(self.play)

        # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        editMenu = menuBar.addMenu('&Edit')
        editMenu.addAction(backAction)
        editMenu.addAction(fowardAction)
        editMenu.addAction(playAction)
        # fileMenu.addAction(newAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)

        # Create a widget for window contents
        wid = QWidget(self)
        self.setCentralWidget(wid)

        # Create layouts to place inside widget
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.positionSlider)
        controlLayout.addWidget(self.currentTimeLabel)
        controlLayout.addWidget(self.totalTimeLabel)

        lay = QHBoxLayout()
        lay.addWidget(self.initFrameButton)
        lay.addWidget(self.finalFrameButton)

        watch = QHBoxLayout()
        watch.addWidget(self.watchnewvid)
        watch.addWidget(self.autoplayCheck)

        layout = QVBoxLayout()
        layout.addWidget(self.fileName)
        layout.addWidget(videoWidget)
        layout.addLayout(controlLayout)
        layout.addLayout(lay)
        layout.addWidget(self.cropButton)
        layout.addWidget(self.deleteButton)
        layout.addLayout(watch)
        layout.addWidget(self.errorLabel)

        # Set widget to contain window contents
        wid.setLayout(layout)

        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

    def opencv_playvideo(self):
        video = cv2.VideoCapture(self.latestvideo)
        frames_counter = 1
        #fps = video.get(cv2.CAP_PROP_FPS)
        while True:
            frames_counter = frames_counter + 1
            check, frame = video.read()
            if check:
                cv2.imshow("Capturing", frame)
                key = cv2.waitKey(15)
            else:
                break
        video.release()
        cv2.destroyAllWindows()

    def autoplaySwitch(self):
        self.autoplay = not self.autoplay
        self.settings.setValue("autoplay", self.autoplay)

    def openFile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(parent=self, caption="Open Movie",
                                                  directory=self.directory, options=options)

        if fileName != '':
            self.settings.setValue("directory", fileName)
            self.mediaPlayer.setMedia(
                QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            self.mediaPlayer.setMuted(True)
            self.initFrameButton.setEnabled(True)
            self.finalFrameButton.setEnabled(True)
            self.initFrame = -1
            self.finalFrame = -1
            self.cropButton.setEnabled(False)
            self.deleteButton.setEnabled(True)
            self.watchnewvid.setEnabled(False)
            self.initFrameButton.setText('Set Initial Frame')
            self.finalFrameButton.setText('Set Final Frame')
            self.play()
            self.directory = fileName
            self.fileName.setText(os.path.basename(self.directory))

    def ffmpeg_cut(self, filename, start_time, end_time, outfilename):
        os.chdir(os.path.dirname(filename))
        subprocess.call(['ffmpeg',
                         "-ss", "%.2f"%start_time,
                         "-i", filename,
                         "-t", "%.2f" % end_time,
                         outfilename
                         ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def setInitFrame(self):
        self.initFrameButton.setText("Set Initial Frame: " + self.hhmmss(self.position))
        self.initFrame = self.position
        if self.initFrame >= 0 and self.finalFrame >= 0:
            self.cropButton.setEnabled(True)

    def setFinalFrame(self):
        self.finalFrameButton.setText('Set Final Frame: ' + self.hhmmss(self.position))
        self.finalFrame = self.position
        if self.initFrame >= 0 and self.finalFrame >= 0:
            self.cropButton.setEnabled(True)

    def exitCall(self):
        sys.exit(app.exec_())

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
            self.resize(self.width(), self.height()+1)
        else:
            self.mediaPlayer.play()
            self.resize(self.width(), self.height()-1)

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.setValue(position)
        self.position = position
        if position >= 0:
            self.currentTimeLabel.setText(self.hhmmss(position))

    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)
        if duration >= 0:
            self.totalTimeLabel.setText(self.hhmmss(duration))
            self.finalFrame = duration
            self.finalFrameButton.setText('Set Final Frame: ' + self.hhmmss(duration))

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def hhmmss(self, ms):
        mss = (ms%1000)
        s = (ms / 1000) % 60
        m = (ms / (1000 * 60)) % 60
        h = (ms / (1000 * 60 * 60)) % 24
        return ("%d:%02d:%02d:%d" % (h, m, s, mss)) if h > 0 else ("%d:%02d:%d" % (m, s, mss))

    def handleError(self):
        self.playButton.setEnabled(False)
        self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())

    def nextFrame(self):
        self.setPosition(self.position + self.frameMovementThreshold)

    def prevFrame(self):
        self.setPosition(self.position - 2 * self.frameMovementThreshold)

    def crop(self):
        i = 0
        while True:
            newFileName = os.path.dirname(self.directory) + f"/{i}_" + os.path.basename(
                self.directory)
            if not os.path.isfile(newFileName):
                self.ffmpeg_cut(self.directory, (self.initFrame / 1000), (self.finalFrame / 1000), newFileName)
                self.watchnewvid.setEnabled(True)
                self.latestvideo = newFileName
                if self.autoplay:
                    self.opencv_playvideo()
                break
            i += 1

    def deleteOriginalVideo(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.play()
        buttonReply = QMessageBox.question(self, 'Warning message',
                                           f"Would you like to delete {os.path.basename(self.directory)}?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            os.remove(self.directory)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoWindow()
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec_())
