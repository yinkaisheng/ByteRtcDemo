#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import threading
from typing import Any, Callable, Dict, List, Tuple
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QAction, QMenu, qApp
from PyQt5.QtWidgets import QAbstractItemView, QAction, QApplication, QDesktopWidget, QDialog, QInputDialog, QMainWindow, QMenu, QMessageBox, QWidget
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QListView, QPushButton, QRadioButton, QSlider, QPlainTextEdit, QTextEdit, QToolTip, QTreeView
from PyQt5.QtWidgets import qApp, QGridLayout, QHBoxLayout, QLayout, QSplitter, QVBoxLayout, QSizePolicy, QSystemTrayIcon
from PyQt5.QtGui import QIcon, QFont, QKeyEvent, QMouseEvent, QCloseEvent, QContextMenuEvent
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtMultimedia import QCamera, QCameraInfo, QCameraViewfinderSettings, QVideoFrame, QVideoProbe
from PyQt5.QtMultimediaWidgets import QCameraViewfinder
import pyqt5AsyncTask as astask
import util

UseQtDPIScaling = 0
if UseQtDPIScaling:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    #QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    DPIScale = 1
else:
    DPIScale = util.getDpiScale()
ButtonHeight = 28
ComboxHeight = ButtonHeight - 2
ComboxItemHeight = ComboxHeight - 2
EditHeight = ButtonHeight - 2
DemoTitle = 'CameraDemo'
QPixelFormats = {}
for k, v in QVideoFrame.__dict__.items():
    if k.startswith('Format'):
        QPixelFormats[v] = k[7:]


def dpiSize(size: int) -> int:
    return int(size * DPIScale)


class MainWindow(QWidget, astask.AsyncTask):
    def __init__(self):
        super().__init__()
        self.createUI()
        self.show()
        self.centerWindow(1280, 800)
        self.delayCall(timeMs=100, func=self.getCameras)
        self.cameraInfos = []
        self.cameras = {}
        self.cameraSettings = {}
        self.cameraStarted = {}

    def createUI(self) -> None:
        #self.setGeometry(300, 300, 300, 220)
        #QToolTip.setFont(QFont('SansSerif', 10))
        #self.setToolTip('This is a <b>QWidget</b> widget')
        self.setWindowTitle('QtCameraDemo')
        #self.setWindowIcon(QIcon('stopwatch.ico'))  # or png
        #self.setMouseTracking(True)  # if not set, only receive mouse move event when pressing

        self.mainVbox = QVBoxLayout()
        self.setLayout(self.mainVbox)

        hbox = QHBoxLayout()
        self.mainVbox.addLayout(hbox)
        labelCameras = QLabel('Cameras:')
        hbox.addWidget(labelCameras)
        self.comboxCameras = QComboBox()
        #self.comboxCameras.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.comboxCameras.setMinimumSize(dpiSize(160), dpiSize(ComboxHeight))
        self.comboxCameras.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.comboxCameras.setView(QListView())
        self.comboxCameras.currentIndexChanged.connect(self.onComboxCameraSelectionChanged)
        hbox.addWidget(self.comboxCameras)
        labelFormats = QLabel('Formats:')
        hbox.addWidget(labelFormats)
        self.comboxFormats = QComboBox()
        self.comboxFormats.setMinimumSize(dpiSize(320), dpiSize(ComboxHeight))
        self.comboxFormats.setStyleSheet('QAbstractItemView::item {height: %dpx; font-family: "Consolas";}' % dpiSize(ComboxItemHeight))
        self.comboxFormats.setView(QListView())
        self.comboxFormats.currentIndexChanged.connect(self.onComboxCameraFormatSelectionChanged)
        hbox.addWidget(self.comboxFormats)
        self.btnStartCapture = QPushButton('StartCapture')
        self.btnStartCapture.setMinimumHeight(dpiSize(ButtonHeight))
        self.btnStartCapture.clicked.connect(self.onClickBtnStartCapture)
        hbox.addWidget(self.btnStartCapture)
        self.btnStopCapture = QPushButton('StopCapture')
        self.btnStopCapture.setEnabled(False)
        self.btnStopCapture.setMinimumHeight(dpiSize(ButtonHeight))
        self.btnStopCapture.clicked.connect(self.onClickBtnStopCapture)
        hbox.addWidget(self.btnStopCapture)
        hbox.addStretch(stretch=1)

        self.cameraViewfinder = QCameraViewfinder()
        self.retainSizeWhenHidden(self.cameraViewfinder)
        self.mainVbox.addWidget(self.cameraViewfinder, stretch=1)

    def centerWindow(self, width=600, height=400) -> None:
        self.resize(width, height)
        rect = self.geometry()
        print('my rect without frame', rect)
        rect = self.frameGeometry()  # must call after window is shown, otherwise frameGeometry equals to geometry
        print('my rect with frame', rect)
        cp = rect.center()
        print('my center', cp)

        desktopRect = QDesktopWidget().availableGeometry()
        print('desktop rect', desktopRect)
        cp = desktopRect.center()
        print('desktop center', cp)

        rect.moveCenter(cp)
        pt = rect.topLeft()
        if pt.x() < 0:
            pt.setX(0)
        if pt.y() < 0:
            pt.setY(0)
        self.move(pt)

    def retainSizeWhenHidden(self, wg: QWidget) -> None:
        sp = wg.sizePolicy()
        if sp:
            sp.setRetainSizeWhenHidden(True)
            wg.setSizePolicy(sp)

    def getCameras(self) -> None:
        self.cameraInfos = QCameraInfo.availableCameras()
        if not self.cameraInfos:
            return
        for n, cameraInfo in enumerate(self.cameraInfos):
            name, deviceId = cameraInfo.description(), cameraInfo.deviceName()
            self.comboxCameras.addItem(name)
        self.comboxCameras.setCurrentIndex(0)
        self.comboxCameras.adjustSize()
        self.onComboxCameraSelectionChanged(self.comboxCameras.currentIndex())

    def onComboxCameraSelectionChanged(self, currentIndex: int) -> None:
        if currentIndex < 0:
            return
        cameraInfo = self.cameraInfos[currentIndex]
        self.comboxFormats.clear()
        if currentIndex not in self.cameraSettings:
            camera = QCamera(cameraInfo)
            camera.load()
            settings = camera.supportedViewfinderSettings()
            self.cameras[currentIndex] = camera
            self.cameraSettings[currentIndex] = settings
        else:
            settings = self.cameraSettings[currentIndex]
        sett = QCameraViewfinderSettings()
        maxSize = 0
        maxSett = None
        formatIndex = -1
        formatStrs = []
        for n, sett in enumerate(settings):
            reso = sett.resolution()
            width, height = reso.width(), reso.height()
            minFps, maxFps = int(sett.minimumFrameRate()), int(sett.maximumFrameRate())
            pixelForamt = sett.pixelFormat()
            formatStr = f'{n:02} Size:{width}x{height}, FPS:[{minFps},{maxFps}], PixelForamt:{QPixelFormats[pixelForamt]}'
            formatStrs.append(formatStr)
            self.comboxFormats.addItem(formatStr)
            if width + height > maxSize:
                maxSize = width + height
                maxSett = sett
                formatIndex = n
        with open('qtCameraFormats.txt', 'wt') as fout:
            fout.write('\n'.join(formatStrs))
        if formatIndex >= 0:
            self.comboxFormats.setCurrentIndex(formatIndex)
            self.comboxFormats.adjustSize()

    def onComboxCameraFormatSelectionChanged(self, currentIndex: int) -> None:
        if currentIndex < 0:
            return
        setting = self.cameraSettings[self.comboxCameras.currentIndex()][currentIndex]
        reso = setting.resolution()
        width, height = reso.width(), reso.height()
        xDiff = self.width() - self.cameraViewfinder.width()
        yDiff = self.height() - self.cameraViewfinder.height()
        self.centerWindow(width + xDiff, height + yDiff)
        print(f'window size:{self.width()},{self.height()}, view size:{self.cameraViewfinder.width()},{self.cameraViewfinder.height()}, selection:{width},{height}')

    def onClickBtnStartCapture(self):
        currentIndex = self.comboxCameras.currentIndex()
        started = self.cameraStarted.get(currentIndex, False)
        if started:
            return
        camera = QCamera()
        camera = self.cameras[currentIndex]
        #camera.load()
        formatIndex = self.comboxFormats.currentIndex()
        setting = self.cameraSettings[currentIndex][formatIndex]
        #reso = setting.resolution()
        #width, height = reso.width(), reso.height()
        camera.setViewfinderSettings(setting)
        camera.setViewfinder(self.cameraViewfinder)
        camera.setCaptureMode(QCamera.CaptureMode.CaptureViewfinder)
        camera.setCaptureMode(QCamera.CaptureMode.CaptureVideo)
        camera.start()
        self.comboxCameras.setEnabled(False)
        self.comboxFormats.setEnabled(False)
        self.btnStartCapture.setEnabled(False)
        self.btnStopCapture.setEnabled(True)
        self.cameraViewfinder.setVisible(True)

    def onClickBtnStopCapture(self) -> None:
        currentIndex = self.comboxCameras.currentIndex()
        camera = self.cameras[currentIndex]
        camera.stop()
        self.comboxCameras.setEnabled(True)
        self.comboxFormats.setEnabled(True)
        self.btnStartCapture.setEnabled(True)
        self.btnStopCapture.setEnabled(False)
        self.cameraViewfinder.setVisible(False)

    def threadFuncDemo(self, signal: pyqtSignal, taskId: int, args: Any) -> None:
        count = args  # type: int
        for i in range(count):
            now = time.monotonic()
            msgId = 1
            anyArg = (i, now)
            print('taskId[{}] signal({:X}) emit msgId: {}, anyArg: {}'.format(taskId, id(signal), msgId, anyArg))
            signal.emit((taskId, msgId, anyArg))
            time.sleep(1.01)

    def threadNotifyDemo(self, taskId: int, msgId: int, args: Any) -> None:
        print('reveive taskId[{}] msgId: {}, args: {}'.format(taskId, msgId, args))
        if msgId == astask.MsgIDThreadExit:
            print('taskId', taskId, 'exit')

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        cmenu = QMenu(self)
        newAct = cmenu.addAction("New")
        opnAct = cmenu.addAction("Open")
        quitAct = cmenu.addAction("Quit")

        exitAct = QAction(QIcon('stopwatch.ico'), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(self.close)  # qApp.quit
        cmenu.addAction(exitAct)

        pt = self.mapToGlobal(event.pos())
        print(event.pos(), pt)
        action = cmenu.exec_(pt)

        if action == quitAct:
            self.close()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        btn = event.buttons()
        print('mouse move', x, y)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        btn = event.button()
        if btn == Qt.LeftButton:
            print('left mouse press', x, y, btn)
        elif btn == Qt.RightButton:
            print('right mouse press', x, y, btn)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        btn = event.button()
        if btn == Qt.LeftButton:
            print('left mouse release', x, y, btn)
        elif btn == Qt.RightButton:
            print('right mouse release', x, y, btn)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        btn = event.button()
        if btn == Qt.LeftButton:
            print('left mouse DoubleClick', x, y, btn)
        elif btn == Qt.RightButton:
            print('right mouse DoubleClick', x, y, btn)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        print('key press', event, key)
        if key == Qt.Key_Escape:
            self.close()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        print('key release', key)
        if key == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        pass
        #reply = QMessageBox.question(self, 'Message', "Are you sure to quit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        #if reply == QMessageBox.Yes:
            #event.accept()
        #else:
            #event.ignore()

    def exit(self) -> None:
        #qApp.quit()
        QApplication.instance().quit()


def main() -> int:
    app = QApplication(sys.argv)
    w = MainWindow()
    ret = app.exec_()
    return ret


if __name__ == '__main__':
    main()
