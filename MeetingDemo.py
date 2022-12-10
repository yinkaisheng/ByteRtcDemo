#!python3
# -*- coding: utf-8 -*-
#author: yinkaisheng@foxmail.com
from __future__ import annotations
import os
import sys
import time
import math
import json
import types
import ctypes
import random
import string
import datetime
import threading
import traceback
import subprocess
import collections
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Tuple, Union
from PyQt5.QtCore import QPointF, QObject, QRect, QRegExp, QSortFilterProxyModel, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QContextMenuEvent, QKeyEvent, QMouseEvent, QMoveEvent, QResizeEvent, QWheelEvent
from PyQt5.QtGui import QColor, QCursor, QFont, QIcon, QImage, QIntValidator, QPainter, QPixmap, QRegion, QTextCursor, QTextOption
from PyQt5.QtWidgets import QDesktopWidget, QDialog, QInputDialog, QMainWindow, QMenu, QMessageBox, QWidget
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QListView, QPushButton, QRadioButton, QSlider, QPlainTextEdit, QTextEdit, QToolTip, QTreeView
from PyQt5.QtWidgets import qApp, QAction, QApplication, QGridLayout, QHBoxLayout, QLayout, QScrollArea, QSplitter, QVBoxLayout
#from QCodeEditor import QCodeEditor
import pyqt5AsyncTask as astask
import util
from bytertcsdk import bytertcsdk as sdk

UseQtDPIScaling = 0
if UseQtDPIScaling:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    #QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    DPIScale = 1
else:
    DPIScale = util.getDpiScale()
ButtonHeight = 24
ComboxHeight = ButtonHeight - 2
ComboxItemHeight = ComboxHeight - 2
EditHeight = ButtonHeight - 2
DemoTitle = 'MeetingDemo(sdk:3.48)'
IcoPath = os.path.join(sdk.ExeDir, 'volcengine.ico')
RtcVideo = None
DevelopDllDir = ''
JoinName = '加入房间'
ViewBackground = 0xDDDDDD
ActiveSpeackerIntervalMs = 300
print = util.printx

#QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def dpiSize(size: int) -> int:
    return int(size * DPIScale)


class TipDlg(QDialog):
    def __init__(self, parent: QObject = None, tipSeconds=3):
        super(TipDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)  # Qt.Tool makes no display on taskbar
        self.resize(dpiSize(200), dpiSize(100))
        self.setMaximumWidth(dpiSize(1280))
        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)
        self.tipLabel = QLabel('')
        #self.tipLabel.setMaximumWidth(dpiSize(1200))
        self.tipLabel.setWordWrap(True)
        self.tipLabel.setAlignment(Qt.AlignTop)
        self.tipLabel.setStyleSheet('QLabel{color:rgb(255,0,0);font-size:%dpx;font-weight:bold;font-family:Verdana;border: 2px solid #FF0000}' % dpiSize(20))
        self.gridLayout.addWidget(self.tipLabel, 0, 0)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.tipSeconds = tipSeconds * 1000

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

    def showTip(self, msg: str = '') -> None:
        self.timer.stop()
        self.timer.start(self.tipSeconds)
        if msg:
            if msg != self.tipLabel.text():
                self.tipLabel.resize(dpiSize(200), dpiSize(100))
            self.tipLabel.setText(msg)
        self.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.raise_()
        self.activateWindow()


class QLabelEx(QLabel):
    DoubleClickSignal = pyqtSignal(tuple)

    def __init__(self, text: str = None, parent: QWidget = None):
        super(QLabelEx, self).__init__(text, parent)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        pos = event.pos()
        x, y = pos.x(), pos.y()
        #label = self.sender() #is None
        self.DoubleClickSignal.emit((x, y))


class ScreenShareDlg(QDialog):
    def __init__(self, parent: MainWindow = None):
        super(ScreenShareDlg, self).__init__(parent)
        self.mainWindow = parent
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.scroll = QScrollArea()
        self.widget = QWidget()
        self.vbox = QVBoxLayout()
        self.widget.setLayout(self.vbox)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.widget)
        self.mainLayout.addWidget(self.scroll)

        self.resize(dpiSize(600), dpiSize(800))
        self.setWindowTitle('双击选择共享对象')
        self.nameLabels = []
        self.imageLabels = []

    def selectScreenShare(self, sourceList: List[sdk.ScreenCaptureSourceInfo], imgList: List[QImage]) -> None:
        self.clearContent()
        sourceInfo = sdk.ScreenCaptureSourceInfo()
        self.sourceList = sourceList
        self.imgList = imgList
        for n, sourceInfo in enumerate(sourceList):
            nameLabel = QLabel(sourceInfo.source_name)
            self.vbox.addWidget(nameLabel)
            self.nameLabels.append(nameLabel)
            imageLabel = QLabelEx()
            imageLabel.DoubleClickSignal.connect(self.onLabelDoubleClick)
            qimg = imgList[n]
            if qimg:
                imageLabel.setPixmap(QPixmap.fromImage(qimg))
            else:
                imageLabel.setFixedSize(160, 90)
                imageLabel.setStyleSheet('background_color: #FFFFFF')
            self.vbox.addWidget(imageLabel)
            self.imageLabels.append(imageLabel)
        self.show()

    def onLabelDoubleClick(self, pos: Tuple[int, int]):
        label = self.sender()
        for n, imgLabel in enumerate(self.imageLabels):
            if label == imgLabel:
                break
        else:
            return
        img = self.imgList[n]
        self.mainWindow.onStartScreenCapture(self.sourceList[n], img.width(), img.height())
        self.hide()
        self.clearContent()

    def clearContent(self) -> None:
        for label in self.nameLabels:
            self.vbox.removeWidget(label)
        self.nameLabels.clear()
        for label in self.imageLabels:
            self.vbox.removeWidget(label)
        self.imageLabels.clear()
        self.sourceList = []
        self.imgList = []


class VideoWidget(QWidget):
    AudioOnIcon = None
    AudioOffIcon = None
    BorderSize = 4
    BottomBarHeight = dpiSize(20)
    BorderColor = QColor(240, 240, 240)
    ActiveBorderColor = QColor(90, 150, 100)
    BackgroundColor = QColor(221, 221, 221)

    def __init__(self, parent: QWidget = None, flags: Union[Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags(),
                 name='', muted: bool = False, showInfo: bool = True):
        super(VideoWidget, self).__init__(parent, flags)
        if VideoWidget.AudioOnIcon is None:
            VideoWidget.AudioOnIcon = QPixmap(os.path.join(sdk.ExeDir, 'icon/audio_on.png'))
            VideoWidget.AudioOffIcon = QPixmap(os.path.join(sdk.ExeDir, 'icon/audio_off.png'))
        self.backgroundColor = VideoWidget.BackgroundColor
        self.borderColor = VideoWidget.BorderColor
        self.muted = muted
        self.showInfo = showInfo
        self.isScreen = False
        self.isActiveColor = False
        self.videoRect = 0, 0, 0, 0
        self.videoLabel = QLabel(self)
        self.videoLabel.winId()
        self.audioLabel = QLabel(self)
        self.audioLabel.setMaximumSize(self.BottomBarHeight, self.BottomBarHeight)
        self.audioLabel.setScaledContents(True)
        self.nameLabel = QLabel(self)
        self.nameLabel.setMaximumHeight(self.BottomBarHeight)
        self.setAudioMuted(self.muted)
        self.setName(name)
        self.setShowInfo(showInfo)

    def viewValue(self) -> int:
        return int(self.videoLabel.winId())  #PyQt5.sip.voidptr

    def setIsActiveColor(self, active: bool) -> None:
        if self.isActiveColor == active:
            return
        self.isActiveColor = active
        self.borderColor = VideoWidget.ActiveBorderColor if active else VideoWidget.BorderColor

        width = self.width()
        height = self.height()

        rect1 = QRect(0, 0, width, self.BorderSize)
        rect2 = QRect(0, height - self.BorderSize, width, self.BorderSize)
        rect3 = QRect(0, self.BorderSize, self.BorderSize, height - self.BorderSize * 2)
        rect4 = QRect(width - self.BorderSize, self.BorderSize, self.BorderSize, height - self.BorderSize * 2)
        #region = QRegion()
        #region.setRects([rect1, rect2, rect3, rect4])
        #self.repaint(region)

        #qp = QPainter()
        #qp.begin(self)
        #qp.setPen(Qt.NoPen)
        #qp.setBrush(self.borderColor)
        #qp.drawRect(0, 0, width, self.BorderSize)
        #qp.drawRect(0, height - self.BorderSize, width, self.BorderSize)
        #qp.drawRect(0, 0, self.BorderSize, height)
        #qp.drawRect(width - self.BorderSize, 0, self.BorderSize, height)
        #qp.end()

        self.repaint(rect1)
        self.repaint(rect2)
        self.repaint(rect3)
        self.repaint(rect4)

    #def setBorderColor(self, color: QColor) -> None:
        #self.borderColor = color
        #self.repaint()

    def setAudioMuted(self, muted: bool) -> None:
        self.muted = muted
        if muted:
            self.audioLabel.setPixmap(self.AudioOffIcon)
        else:
            self.audioLabel.setPixmap(self.AudioOnIcon)

    def setName(self, name: str) -> None:
        self.nameLabel.setText(name)
        self.videoLabel.setToolTip(name)

    def setShowInfo(self, show: bool) -> None:
        self.showInfo = show
        if show:
            self.audioLabel.show()
            self.nameLabel.show()
        else:
            self.audioLabel.hide()
            self.nameLabel.hide()

    def wheelEvent(self, event: QWheelEvent) -> None:
        #print(f'{type(event)}')
        pt = event.angleDelta()
        x, y = pt.x(), pt.y()
        #print(f'{self.__class__.__name__} {x} {y}')
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        #print(f'{self.__class__.__name__} {x} {y}')

    def moveEvent(self, event: QMoveEvent) -> None:
        pos = event.pos()
        x, y = pos.x(), pos.y()
        #print(f'{self.__class__.__name__} {x} {y}')

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        x, y = event.x(), event.y()
        #print(f'{self.__class__.__name__} {x} {y}')
        event.ignore()

    def resizeEvent(self, event: QResizeEvent) -> None:
        size = event.size()
        width, height = size.width(), size.height()
        #print(f'{self.__class__.__name__} {width} {height}')
        if self.showInfo:
            self.videoLabel.setGeometry(self.BorderSize, self.BorderSize, width - self.BorderSize * 2, height - self.BorderSize * 2 - self.BottomBarHeight)
            self.audioLabel.setGeometry(self.BorderSize, height - self.BorderSize - self.BottomBarHeight, self.BottomBarHeight, self.BottomBarHeight)
            self.nameLabel.setGeometry(self.BorderSize + self.BottomBarHeight, height - self.BorderSize - self.BottomBarHeight,
                                       width - self.BorderSize * 2 - self.BottomBarHeight, self.BottomBarHeight)
        else:
            self.videoLabel.setGeometry(self.BorderSize, self.BorderSize, width - self.BorderSize * 2, height - self.BorderSize * 2)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        #qp.setPen(QColor(255, 255, 255))
        qp.setPen(Qt.NoPen)
        qp.setBrush(self.borderColor)
        qp.drawRect(0, 0, w, h)
        qp.setBrush(self.BackgroundColor)
        qp.drawRect(self.BorderSize, self.BorderSize, w - self.BorderSize * 2, h - self.BorderSize * 2)


class MyIntEnum(IntEnum):
    __str__ = IntEnum.__repr__


class VideoLayout(MyIntEnum):
    ManyTopAnd1Big = 0
    ManyTopAnd2Big = 1
    Grid = 2


class VideoManagerWidget(QWidget):
    VideoShowStateChangedSignal = pyqtSignal(tuple)
    VideoViewSizeChagnedSignal = pyqtSignal(tuple)

    def __init__(self, parent: QWidget = None, flags: Union[Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags()):
        super(VideoManagerWidget, self).__init__(parent, flags)
        self.topVideoWidgets = []
        self.gridVideoWidgets = []
        self.freeVideoWidgets = []
        self.showTop = True
        self.videoLayout = VideoLayout.ManyTopAnd1Big
        self.topHeight = 0
        self.activeVideoW = None
        self.showTopStartIndex = 0
        self.showTopCount = 0
        self.lastWheelTick = 0

    def setLayout(self, layout: VideoLayout) -> None:
        self.videoLayout = layout
        self.reLayout()

    def getNewView(self) -> Tuple[int, bool, Tuple[int, int, int, int]]:
        '''return Tuple(view:int, show:bool, rect:Tuple(int,int,int,int))'''
        if self.videoLayout == VideoLayout.Grid:
            pass
        else:
            if self.freeVideoWidgets:
                videoW = self.freeVideoWidgets.pop(-1)
            else:
                videoW = VideoWidget(self)
            self.addVideoWidget(videoW)
            return videoW.viewValue(), not videoW.isHidden(), videoW.videoRect

    def freeView(self, view: int, reLayout: bool = True) -> None:
        #videoW = VideoWidget()
        if self.videoLayout == VideoLayout.Grid:
            pass
        else:
            for n, videoW in enumerate(self.gridVideoWidgets):
                if videoW.viewValue() == view:
                    videoW.hide()
                    videoW.videoRect = (0, 0, 0, 0)
                    videoW.setAudioMuted(True)
                    videoW.setName('')
                    self.gridVideoWidgets.pop(n)
                    self.freeVideoWidgets.append(videoW)
                    if not self.gridVideoWidgets and self.topVideoWidgets:
                        videoW = self.topVideoWidgets.pop(0)
                        videoW.setShowInfo(False)
                        self.gridVideoWidgets.append(videoW)
                    if reLayout:
                        self.reLayout()
                    return
            for n, videoW in enumerate(self.topVideoWidgets):
                if videoW.viewValue() == view:
                    videoW.hide()
                    videoW.videoRect = (0, 0, 0, 0)
                    videoW.setAudioMuted(True)
                    videoW.setName('')
                    self.topVideoWidgets.pop(n)
                    self.freeVideoWidgets.append(videoW)
                    if reLayout or not self.topVideoWidgets:
                        self.reLayout()
                    return

    def setAudioState(self, view: int, muted: bool) -> None:
        viewW = self.getVideoWidget(view)
        if viewW:
            viewW.setAudioMuted(muted)

    def setViewName(self, view: int, name: str) -> None:
        viewW = self.getVideoWidget(view)
        if viewW:
            viewW.setName(name)

    def setViewInfo(self, view: int, name: str, muted: bool) -> None:
        viewW = self.getVideoWidget(view)
        if viewW:
            viewW.setName(name)
            viewW.setAudioMuted(muted)

    def setMaxView(self, view: int) -> None:
        if self.videoLayout == VideoLayout.Grid:
            pass
        else:
            #videoW = VideoWidget()
            for b, videoW in enumerate(self.gridVideoWidgets):
                if videoW.viewValue() == view:
                    return
            bigVideoW = videoW
            for s, videoW in enumerate(self.topVideoWidgets):
                if videoW.viewValue() == view:
                    break
            else:
                return
            bigRect = bigVideoW.videoRect
            smallRect = videoW.videoRect
            smallHidden = videoW.isHidden()
            bigVideoW.setShowInfo(True)
            bigVideoW.setGeometry(*smallRect)
            bigVideoW.videoRect = smallRect
            videoW.setShowInfo(False)
            videoW.setGeometry(*bigRect)
            videoW.videoRect = bigRect
            self.gridVideoWidgets[b] = videoW
            self.topVideoWidgets[s] = bigVideoW
            if smallHidden:
                bigVideoW.hide()
                self.VideoShowStateChangedSignal.emit((bigVideoW.viewValue(), False))
                videoW.show()
                self.VideoShowStateChangedSignal.emit((videoW.viewValue(), True))
                self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), bigRect[2], bigRect[3]))
            else:
                self.VideoViewSizeChagnedSignal.emit((bigVideoW.viewValue(), smallRect[2], smallRect[3]))
                self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), bigRect[2], bigRect[3]))

    def getMaxView(self) -> List[int]:
        if self.videoLayout == VideoLayout.Grid:
            return []
        else:
            return [it.viewValue() for it in self.gridVideoWidgets]

    def isViewMax(self, view: int) -> bool:
        return view in self.getMaxView()

    def getVisibleViewsOnTop(self) -> List[int]:
        views = []
        #videoW = VideoWidget()
        for videoW in self.topVideoWidgets:
            if not videoW.isHidden():
                views.append(videoW.viewValue())
            else:
                break
        return views

    def setViewToPosOnTop(self, view: int, pos: int) -> None:
        #videoW = VideoWidget()
        if pos >= len(self.topVideoWidgets):
            return
        for n, videoW in enumerate(self.topVideoWidgets):
            if videoW.viewValue() == view:
                break
        else:
            return
        if n == pos:
            return
        else:
            popVideoW = self.topVideoWidgets[pos]
            self.topVideoWidgets[pos] = videoW
            self.topVideoWidgets[n] = popVideoW
            self.reLayout()

    def getVideoWidget(self, view: int) -> VideoWidget:
        #videoW = VideoWidget()
        for videoW in self.gridVideoWidgets:
            if videoW.viewValue() == view:
                return videoW
        for videoW in self.topVideoWidgets:
            if videoW.viewValue() == view:
                return videoW

    def addVideoWidget(self, videoW: VideoWidget) -> None:
        if not self.gridVideoWidgets:
            videoW.setShowInfo(False)
            self.gridVideoWidgets.append(videoW)
            self.reLayout()
            return
        if self.videoLayout == VideoLayout.ManyTopAnd2Big and len(self.gridVideoWidgets) == 1:
            videoW.setShowInfo(False)
            self.gridVideoWidgets.append(videoW)
            self.reLayout()
            return
        videoW.setShowInfo(True)
        self.topVideoWidgets.append(videoW)
        self.reLayout()

    def setActiveVideo(self, view: int) -> None:
        #videoW = VideoWidget()
        for videoW in self.gridVideoWidgets:
            if videoW.viewValue() == view:
                self.doSetActiveVideo(videoW)
                return
        for videoW in self.topVideoWidgets:
            if videoW.viewValue() == view:
                self.doSetActiveVideo(videoW)
                return

    def doSetActiveVideo(self, videoW: VideoWidget):
        if self.activeVideoW == videoW:
            return
        if self.activeVideoW:
            self.activeVideoW.setIsActiveColor(False)
        videoW.setIsActiveColor(True)
        self.activeVideoW = videoW

    def setNoActiveVideo(self):
        if self.activeVideoW:
            self.activeVideoW.setIsActiveColor(False)
            self.activeVideoW = None

    def resetVideoBack(self, view: int):
        videoW = self.getVideoWidget(view)
        if videoW:
            videoW.repaint()

    def reLayout(self) -> None:
        width, height = self.width(), self.height()
        if self.videoLayout == VideoLayout.ManyTopAnd1Big:
            smallHeight = 0
            if self.topVideoWidgets:
                #videoW = VideoWidget()
                smallWidth = dpiSize(160) + VideoWidget.BorderSize * 2
                smallHeight = dpiSize(90) + VideoWidget.BorderSize * 2 + VideoWidget.BottomBarHeight
                showCount = width // smallWidth
                n = 0
                for videoW in self.topVideoWidgets:
                    vx = (n - self.showTopStartIndex) * smallWidth
                    vy = 0
                    if vx < width and n >= self.showTopStartIndex:
                        videoW.setGeometry(vx, vy, smallWidth, smallHeight)
                        ox, oy, ow, oh = videoW.videoRect
                        if ow != smallWidth or oh != smallHeight:
                            self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), smallWidth, smallHeight))
                        videoW.videoRect = vx, vy, smallWidth, smallHeight
                        if videoW.isHidden():
                            videoW.show()
                            self.VideoShowStateChangedSignal.emit((videoW.viewValue(), True))
                        #videoW.repaint()
                        self.showTopCount = n + 1
                    else:
                        if not videoW.isHidden():
                            videoW.hide()
                            videoW.videoRect = 0, 0, 0, 0
                            self.VideoShowStateChangedSignal.emit((videoW.viewValue(), False))
                    n += 1
            self.topHeight = smallHeight
            if self.gridVideoWidgets:
                videoW = self.gridVideoWidgets[0]
                #videoW = VideoWidget()
                ox, oy, ow, oh = videoW.videoRect
                bigWidth, bigHeight = width, height - smallHeight
                videoW.setGeometry(0, smallHeight, bigWidth, bigHeight)
                if ow != bigWidth or oh != bigHeight:
                    self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), bigWidth, bigHeight))
                videoW.videoRect = 0, smallHeight, bigWidth, bigHeight
                if videoW.isHidden():
                    videoW.show()
                    self.VideoShowStateChangedSignal.emit((videoW.viewValue(), True))
                #videoW.repaint()
        elif self.videoLayout == VideoLayout.ManyTopAnd2Big:
            smallHeight = 0
            if self.topVideoWidgets:
                #videoW = VideoWidget()
                smallWidth = dpiSize(160) + videoW.BorderSize * 2
                smallHeight = dpiSize(90) + videoW.borderColor * 3
                showCount = width // smallWidth
                n = 0
                for videoW in self.topVideoWidgets:
                    vx = (n - self.showTopStartIndex) * smallWidth
                    vy = 0
                    if vx < width and n >= self.showTopStartIndex:
                        videoW.setGeometry(vx, vy, smallWidth, smallHeight)
                        if ow != smallWidth or oh != smallHeight:
                            self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), smallWidth, smallHeight))
                        videoW.videoRect = vx, vy, smallWidth, smallHeight
                        if videoW.isHidden():
                            videoW.show()
                            self.VideoShowStateChangedSignal.emit((videoW.viewValue(), True))
                        #videoW.repaint()
                        self.showTopCount = n + 1
                    else:
                        if not videoW.isHidden():
                            videoW.hide()
                            videoW.videoRect = 0, 0, 0, 0
                            self.VideoShowStateChangedSignal.emit((videoW.viewValue(), False))
                    n += 1
            self.topHeight = smallHeight
            if len(self.gridVideoWidgets) == 2:
                #videoW = VideoWidget()
                videoW = self.gridVideoWidgets[0]
                ox, oy, ow, oh = videoW.videoRect
                bigWidth, bigHeight = width, height - smallHeight
                videoW.setGeometry(0, smallHeight, bigWidth, bigHeight)
                if ow != bigWidth or oh != bigHeight:
                    self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), bigWidth, bigHeight))
                videoW.videoRect = 0, smallHeight, bigWidth, bigHeight
                if videoW.isHidden():
                    videoW.show()
                    self.VideoShowStateChangedSignal.emit((videoW.viewValue(), True))
                #videoW.repaint()
                videoW = self.gridVideoWidgets[1]
                ox, oy, ow, oh = videoW.videoRect
                bigWidth, bigHeight = width, height - smallHeight
                videoW.setGeometry(0, smallHeight, bigWidth, bigHeight)
                if ow != bigWidth or oh != bigHeight:
                    self.VideoViewSizeChagnedSignal.emit((videoW.viewValue(), bigWidth, bigHeight))
                videoW.videoRect = 0, smallHeight, bigWidth, bigHeight
                if videoW.isHidden():
                    videoW.show()
                    self.VideoShowStateChangedSignal.emit((videoW.viewValue(), True))
                #videoW.repaint()
        elif self.videoLayout == VideoLayout.Grid:
            pass

    def wheelEvent(self, event: QWheelEvent) -> None:
        #print(f'{type(event)}')
        pt = event.pos()
        x, y = pt.x(), pt.y()
        pt = event.angleDelta()
        dx, dy = pt.x(), pt.y()
        print(f'{self.__class__.__name__} {x} {y}')
        if not self.topVideoWidgets:
            return
        width = self.width()
        #videoW = VideoWidget()
        videoW = self.topVideoWidgets[self.showTopStartIndex]
        if y > videoW.height():
            return  #mouse not in top scroll area
        now = time.monotonic()
        if now < self.lastWheelTick + 0.5:
            return
        canShowCount = self.width() // videoW.videoRect[2]
        if dy < 0:
            for n, videoW in enumerate(self.topVideoWidgets):
                if n > self.showTopStartIndex:
                    if videoW.videoRect[0] + videoW.videoRect[2] > width or not videoW.isVisible():
                        break
            else:
                return
            notShowCount = len(self.topVideoWidgets) - n
            if notShowCount >= canShowCount:
                self.showTopStartIndex += canShowCount
            else:
                self.showTopStartIndex = len(self.topVideoWidgets) - canShowCount
            print(f'{self.__class__.__name__} can show {canShowCount}, not full show {notShowCount}, start show {self.showTopStartIndex}')
        elif dy > 0:
            if self.showTopStartIndex == 0:
                return
            notShowCount = self.showTopStartIndex
            if notShowCount < canShowCount:
                self.showTopStartIndex = 0
            else:
                self.showTopStartIndex -= canShowCount
            print(f'{self.__class__.__name__} can show {canShowCount}, not full show {notShowCount}, start show {self.showTopStartIndex}')
        self.reLayout()
        self.lastWheelTick = time.monotonic()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        print(f'{self.__class__.__name__} {x} {y}')

    def moveEvent(self, event: QMoveEvent) -> None:
        pos = event.pos()
        x, y = pos.x(), pos.y()
        print(f'{self.__class__.__name__} {x} {y}')

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        x, y = event.x(), event.y()
        print(f'{self.__class__.__name__} {x} {y}')
        if self.videoLayout == VideoLayout.Grid:
            pass
        else:
            #videoW = VideoWidget()
            n = 0
            for videoW in self.topVideoWidgets:
                vl, vt, vr, vb = videoW.videoRect
                vr = vl + vr
                vb = vt + vb
                if vl <= x <= vr and vt <= y <= vb:
                    break
                n += 1
            if n < len(self.topVideoWidgets):
                bigVideo = self.topVideoWidgets[n]
                self.setMaxView(bigVideo.viewValue())

    def resizeEvent(self, event: QResizeEvent) -> None:
        size = event.size()
        width, height = size.width(), size.height()
        print(f'{self.__class__.__name__}  {width} {height}')
        #self.videoLabel.setGeometry(2, 2, width - 4, height - 4)
        self.reLayout()

    #def paintEvent(self, e):
        #qp = QPainter()
        #qp.begin(self)
        #self.drawWidget(qp)
        #qp.end()

    #def drawWidget(self, qp):
        #size = self.size()
        #w = size.width()
        #h = size.height()

        ##qp.setPen(QColor(255, 255, 255))
        #qp.setPen(Qt.NoPen)
        #qp.setBrush(self.borderColor)
        #qp.drawRect(0, 0, w, h)
        #qp.setBrush(self.BackgroundColor)
        #qp.drawRect(self.BorderSize, self.BorderSize, w - self.BorderSize * 2, h - self.BorderSize * 2)


class RTCRoomEventHandler:
    def __init__(self, parent, room_id: str):
        self.parent = parent
        self.room_id = room_id

    def onRTCRoomEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        """
        event_time: micro seconds since epoch
        """
        #print(f'{room_id} {event_name} {event_json}')
        self.parent.onRTCRoomEventHappen(self.room_id, event_time, event_name, event_json, event)


class MainWindow(QMainWindow, astask.AsyncTask):
    RTCVideoEventSignal = pyqtSignal(tuple)
    RTCRoomEventSignal = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        sdk.log.info(f'sys.paltform={sys.platform}, ExePath={sdk.ExePath}, cwd={os.getcwd()}, uithread={threading.get_ident()}')
        self.configPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.config')
        self.configJson = util.jsonFromFile(self.configPath)
        configExJson = util.jsonFromFile(f'{self.configPath}Ex')    #save appid to configex, it's not in git
        self.configJson.update(configExJson)
        self.localViews = {}  # key 0,1
        self.activeRemoteSpeakers = []
        self.captureSourceList = []
        self.createUI()
        self.initUI()
        self.screenShareDlg = ScreenShareDlg(self)
        self.showMsg = False
        self.setMouseTracking(True)
        self.videoEncoderConfig = sdk.VideoEncoderConfig(width=640, height=360, frameRate=15)
        self.pushTaskId = 0
        self.pushUserId = ''
        # after exec, console window is active, set MainWindow active in timer
        if sys.stdout:
            self.delayCall(timeMs=100, func=self.activateWindow)

        self.rtcVideo = None  # sdk.RTCVideo(app_id='', event_handler=None, parameters='')
        self.videoEffect = None
        self.audioDeviceManager = None
        self.videoDeviceManager = None
        self.userId = ''
        self.rtcRooms = {}
        self.rtcRoomEventHandlers = {}
        self.rtcRoomJoined = {}
        self.roomUsers = {} #key userId
        self.roomUserViews = {} #key userId
        self.screenShareStarted = False
        self.currentEventRoomId = ''  # only use in room event handler
        self.RTCVideoEventSignal.connect(self.onRTCVideoEvent)
        self.RTCRoomEventSignal.connect(self.onRTCRoomEvent)
        self.RTCVideoEventHandler = {}
        self.RTCRoomEventHandler = {}
        self.initializeEventHandlers()

        self.delayCall(timeMs=100, func=self.initSDK)
        self.lastCancelActiveColorTimer = QTimer()
        self.roomTimer = QTimer()
        self.roomTimer.timeout.connect(self.onRoomTimer)
        self.roomStartTick = 0

    def createUI(self) -> None:
        self.setWindowTitle(DemoTitle)
        self.setWindowIcon(QIcon(IcoPath))
        #self.resize(dpiSize(1400), dpiSize(800))
        self.setMinimumSize(dpiSize(1280), dpiSize(720))
        self.intValidator = QIntValidator()
        self.tipDlg = TipDlg(self)

        mainWg = QWidget(self)
        self.setCentralWidget(mainWg)
        self.mainLayout = QVBoxLayout()
        mainWg.setLayout(self.mainLayout)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)

        self.hLayoutVideo = QHBoxLayout()
        self.mainLayout.addLayout(self.hLayoutVideo, stretch=1)

        self.videoManagerW = VideoManagerWidget(mainWg)
        self.videoManagerW.VideoShowStateChangedSignal.connect(self.onRemoteVideoViewShowStateChanged)
        self.videoManagerW.VideoViewSizeChagnedSignal.connect(self.onRemoteVideoViewSizeChanged)
        self.hLayoutVideo.addWidget(self.videoManagerW, stretch=1)

        self.msgWidget = QWidget(self)
        self.msgWidget.hide()
        self.vlayoutMsg = QVBoxLayout()
        self.vlayoutMsg.setContentsMargins(2, 2, 2, 2)
        self.msgWidget.setLayout(self.vlayoutMsg)
        self.hLayoutVideo.addWidget(self.msgWidget)

        historyLabel = QLabel('历史消息:')
        self.vlayoutMsg.addWidget(historyLabel)

        self.historyMsgEdit = QTextEdit()
        self.historyMsgEdit.setReadOnly(True)
        self.vlayoutMsg.addWidget(self.historyMsgEdit, stretch=3)
        self.msgEdit = QTextEdit()
        self.vlayoutMsg.addWidget(self.msgEdit, stretch=1)

        self.sendMsgBtn = QPushButton('发送(Ctrl+Enter)')
        self.sendMsgBtn.clicked.connect(self.onClickSendMsgBtn)
        self.vlayoutMsg.addWidget(self.sendMsgBtn)

        self.hLayoutBar = QHBoxLayout()
        self.hLayoutBar.setContentsMargins(2, 2, 2, 2)
        self.mainLayout.addLayout(self.hLayoutBar)

        roomLabel = QLabel('房间:')
        self.hLayoutBar.addWidget(roomLabel)
        self.roomIdEdit = QLineEdit(self.configJson['roomId'])
        self.roomIdEdit.setMaximumWidth(dpiSize(80))
        self.hLayoutBar.addWidget(self.roomIdEdit)
        nameLabel = QLabel('昵称:')
        self.hLayoutBar.addWidget(nameLabel)
        self.nameEdit = QLineEdit(self.configJson['nickName'])
        self.nameEdit.setMaximumWidth(dpiSize(80))
        self.hLayoutBar.addWidget(self.nameEdit)
        self.hLayoutBar.addStretch(1)
        self.enableAudioCheck = QCheckBox('发送音频')
        self.enableAudioCheck.setChecked(self.configJson['enableAudio'])
        self.enableAudioCheck.clicked.connect(self.onClickEnableAudioCheck)
        self.hLayoutBar.addWidget(self.enableAudioCheck)
        self.labelRecoders = QLabel('>>  ')
        self.retainSizeWhenHidden(self.labelRecoders)
        self.labelRecoders.show() if self.configJson['enableAudio'] else self.labelRecoders.hide()
        self.labelRecoders.mouseReleaseEvent = self.onLabelRecordersMouseRleaseEvent
        self.hLayoutBar.addWidget(self.labelRecoders)
        self.enableVideoCheck = QCheckBox('发送视频')
        self.enableVideoCheck.setChecked(self.configJson['enableVideo'])
        self.enableVideoCheck.clicked.connect(self.onClickEnableVideoCheck)
        self.hLayoutBar.addWidget(self.enableVideoCheck)
        self.labelCamera = QLabel('>>  ')
        self.retainSizeWhenHidden(self.labelCamera)
        self.labelCamera.show() if self.configJson['enableVideo'] else self.labelCamera.hide()
        self.labelCamera.mouseReleaseEvent = self.onLabelCamerasMouseRleaseEvent
        self.hLayoutBar.addWidget(self.labelCamera)
        self.virtualBackgroundCheck = QCheckBox('虚拟背景')
        self.retainSizeWhenHidden(self.virtualBackgroundCheck)
        self.virtualBackgroundCheck.show() if self.configJson['enableVideo'] else self.virtualBackgroundCheck.hide()
        self.virtualBackgroundCheck.setChecked(self.configJson['enableVirtualBackground'])
        self.virtualBackgroundCheck.clicked.connect(self.onClickVirtualBackgroundCheck)
        self.hLayoutBar.addWidget(self.virtualBackgroundCheck)
        self.labelBackgrounds = QLabel('>>  ')
        self.retainSizeWhenHidden(self.labelBackgrounds)
        self.labelBackgrounds.show() if self.configJson['enableVirtualBackground'] else self.labelBackgrounds.hide()
        self.labelBackgrounds.mouseReleaseEvent = self.onLabelBackgroundsMouseRleaseEvent
        self.hLayoutBar.addWidget(self.labelBackgrounds)
        self.joinBtn = QPushButton(JoinName)
        self.joinBtn.clicked.connect(self.onClickJoinRoomBtn)
        self.hLayoutBar.addWidget(self.joinBtn)
        self.screenShareBtn = QPushButton('屏幕分享')
        self.retainSizeWhenHidden(self.screenShareBtn)
        self.screenShareBtn.hide()
        self.screenShareBtn.clicked.connect(self.onClickScreenShareBtn)
        self.hLayoutBar.addWidget(self.screenShareBtn)
        self.enableScreenAudioCheck = QCheckBox('分享屏幕音频')
        self.retainSizeWhenHidden(self.enableScreenAudioCheck)
        self.enableScreenAudioCheck.hide()
        self.enableScreenAudioCheck.clicked.connect(self.onClickEnableScreenAudioCheck)
        self.hLayoutBar.addWidget(self.enableScreenAudioCheck)
        self.hLayoutBar.addStretch(1)
        self.msgShowStateLabel = QLabel('<<消息')
        self.retainSizeWhenHidden(self.msgShowStateLabel)
        self.msgShowStateLabel.hide()
        self.msgShowStateLabel.mouseReleaseEvent = self.onLabelMsgMouseRleaseEvent
        self.hLayoutBar.addWidget(self.msgShowStateLabel)

    def initUI(self) -> None:
        pass

    def retainSizeWhenHidden(self, wg: QWidget) -> None:
        sp = wg.sizePolicy()
        if sp:
            sp.setRetainSizeWhenHidden(True)
            wg.setSizePolicy(sp)

    def initSDK(self) -> None:
        sdk.selectSdkBinDir('binx86_3.48')
        self.rtcVideo = sdk.RTCVideo(app_id='5a7451222679214f668e7085', event_handler=self, parameters='{"testKey": "testValue"}')
        self.rtcVideo.enableSimulcastMode(True)
        self.audioDeviceManager = self.rtcVideo.getAudioDeviceManager()
        self.videoDeviceManager = self.rtcVideo.getVideoDeviceManager()
        devices = self.videoDeviceManager.enumerateVideoCaptureDevices2()
        if devices:
            self.videoDeviceManager.setVideoCaptureDevice(devices[0].device_id)

        videoCaptureConfig = sdk.VideoCaptureConfig()
        #videoCaptureConfig.capturePreference = sdk.CapturePreference.Auto #0
        videoCaptureConfig.capturePreference = sdk.CapturePreference.Manual #1
        #videoCaptureConfig.capturePreference = sdk.CapturePreference.AutoPerformance    #2
        videoCaptureConfig.width = 1280
        videoCaptureConfig.height = 720
        videoCaptureConfig.frameRate = 25
        self.rtcVideo.setVideoCaptureConfig(videoCaptureConfig)

        videoEncoderConfig = sdk.VideoEncoderConfig()
        videoEncoderConfig.width = 1280
        videoEncoderConfig.height = 720
        videoEncoderConfig.frameRate = 25
        videoEncoderConfig.maxBitrate = -1
        #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Disabled #0
        videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Framerate #1
        #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Quality #2
        #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Balance #3
        self.videoEncoderConfig = videoEncoderConfig

        videoEncoderConfig1 = sdk.VideoEncoderConfig()
        videoEncoderConfig1.width = videoEncoderConfig.width // 2
        videoEncoderConfig1.height = videoEncoderConfig.height // 2
        videoEncoderConfig1.frameRate = 15
        videoEncoderConfig1.maxBitrate = -1
        videoEncoderConfig1.encoderPreference = sdk.VideoEncodePreference.Framerate

        self.rtcVideo.setVideoEncoderConfig(videoEncoderConfig)
        #self.rtcVideo.setVideoEncoderConfig([videoEncoderConfig, videoEncoderConfig1])

        viewHandle, isShow, videoRect = self.videoManagerW.getNewView()
        self.videoManagerW.setViewName(viewHandle, '(我)')
        #renderMode = sdk.RenderMode.Hidden  #1
        renderMode = sdk.RenderMode.Fit     #2
        #renderMode = sdk.RenderMode.Fill    #3
        videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=renderMode, background_color=ViewBackground)
        index = sdk.StreamIndex.Main    #0
        #index = sdk.StreamIndex.Screen #1
        self.rtcVideo.setLocalVideoCanvas(index, videoCanvas)

        self.localViews[sdk.StreamIndex.Main] = viewHandle
        mute = not self.configJson['enableAudio']
        self.videoManagerW.setAudioState(viewHandle, mute)

        if self.configJson['enableAudio']:
            self.labelRecoders.show()
            self.enableAudioCheck.setChecked(True)
            self.rtcVideo.startAudioCapture()
        if self.configJson['enableVideo']:
            self.labelCamera.show()
            self.virtualBackgroundCheck.show()
            self.enableVideoCheck.setChecked(True)
            self.rtcVideo.startVideoCapture()
        if self.configJson['enableVirtualBackground']:
            self.onClickVirtualBackgroundCheck()

        testAddVideo = 0
        if testAddVideo:
            self.testAddVideos()

    def testAddVideos(self) -> None:
        for i in range(22):
            videoWidget = VideoWidget(self.videoManagerW, name=f'video{i}')
            self.videoManagerW.topVideoWidgets.append(videoWidget)
            if i == 0:
                videoWidget.setIsActiveColor(True)
            else:
                videoWidget.setAudioMuted(True)
        videoWidget = VideoWidget(self.videoManagerW, name=f'video', showInfo=False)
        self.videoManagerW.gridVideoWidgets.append(videoWidget)
        self.videoManagerW.reLayout()

    def destroySDK(self) -> None:
        if not self.rtcVideo:
            return
        if self.configJson['enableAudio']:
            self.rtcVideo.stopAudioCapture()
        if self.configJson['enableVideo']:
            self.rtcVideo.stopVideoCapture()
        self.videoEffect = None
        self.audioDeviceManager = None
        self.videoDeviceManager = None
        self.rtcVideo.destroy()
        self.rtcVideo = None

    def onClickSendMsgBtn(self) -> None:
        message = self.msgEdit.toPlainText().strip()
        if message:
            roomId = self.roomIdEdit.text().strip()
            #rtcRoom = sdk.RTCRoom()
            rtcRoom = self.rtcRooms[roomId]
            rtcRoom.sendRoomMessage(message)
            t = datetime.datetime.now()
            timeStr = f'{t.year}-{t.month:02}-{t.day:02} {t.hour:02}:{t.minute:02}:{t.second:02}'
            self.historyMsgEdit.append(f'<font color=#7C7CFC>{timeStr}    我(uid:{self.userId}):</font><br>{message}<br>')
            currentCursor = self.historyMsgEdit.textCursor()
            currentCursor.movePosition(QTextCursor.End)
            self.historyMsgEdit.setTextCursor(currentCursor)
            self.msgEdit.clear()
            self.msgEdit.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        print(f'{self.__class__.__name__} {type(event)}')
        self.destroySDK()

    def onClickEnableAudioCheck(self) -> None:
        self.configJson['enableAudio'] = self.enableAudioCheck.isChecked()
        util.jsonToFile(self.configJson, self.configPath)
        roomId = self.roomIdEdit.text().strip()
        if self.configJson['enableAudio']:
            self.labelRecoders.show()
            self.rtcVideo.startAudioCapture()
            mute = False
            self.videoManagerW.setAudioState(self.localViews[sdk.StreamIndex.Main], mute)
            if self.rtcRoomJoined.get(roomId, False):
                #rtcRoom = sdk.RTCRoom()
                rtcRoom = self.rtcRooms[roomId]
                rtcRoom.publishStream(sdk.MediaStreamType.Audio)
        else:
            self.labelRecoders.hide()
            self.rtcVideo.stopAudioCapture()
            mute = True
            self.videoManagerW.setAudioState(self.localViews[sdk.StreamIndex.Main], mute)
            if self.rtcRoomJoined.get(roomId, False):
                #rtcRoom = sdk.RTCRoom()
                rtcRoom = self.rtcRooms[roomId]
                rtcRoom.unpublishStream(sdk.MediaStreamType.Audio)

    def onClickEnableVideoCheck(self) -> None:
        self.configJson['enableVideo'] = self.enableVideoCheck.isChecked()
        util.jsonToFile(self.configJson, self.configPath)
        if self.configJson['enableVideo']:
            self.labelCamera.show()
            self.virtualBackgroundCheck.show()
            if self.configJson['enableVirtualBackground']:
                self.labelBackgrounds.show()
            self.rtcVideo.startVideoCapture()
        else:
            self.labelCamera.hide()
            self.virtualBackgroundCheck.hide()
            self.labelBackgrounds.hide()
            self.rtcVideo.stopVideoCapture()
            self.delayCall(timeMs=200, func=self.videoManagerW.resetVideoBack, view=self.localViews[sdk.StreamIndex.Main])

    def onClickVirtualBackgroundCheck(self) -> None:
        self.configJson['enableVirtualBackground'] = self.virtualBackgroundCheck.isChecked()
        util.jsonToFile(self.configJson, self.configPath)
        if not self.videoEffect:
            self.videoEffect = self.rtcVideo.getVideoEffectInterface()
            licensePath = os.path.join(sdk.SdkBinDirFull, '../effect.lic')
            modelPath = os.path.join(sdk.SdkBinDirFull, '../cvlab/model')
            ret = self.videoEffect.initCVResource(licensePath, modelPath)
        if not self.videoEffect:
            return
        imagePath = os.path.join(sdk.ExeDir, 'VirtualBackgroundImages', self.configJson['backgroundImage'])
        stickerPath = os.path.join(sdk.SdkBinDirFull, '../cvlab/ComposeMakeup/matting_bg')
        if self.virtualBackgroundCheck.isChecked():
            self.labelBackgrounds.show()
            ret = self.videoEffect.enableVideoEffect()
            virtualSource = sdk.VirtualBackgroundSource(source_type=sdk.VirtualBackgroundSourceType.Image,
                                                        source_color=0xFFFFFFFF, source_path=imagePath)
            ret = self.videoEffect.enableVirtualBackground(stickerPath, virtualSource)
        else:
            self.labelBackgrounds.hide()
            self.videoEffect.disableVirtualBackground()
            self.videoEffect.disableVideoEffect()

    def onLabelRecordersMouseRleaseEvent(self, event: QMouseEvent) -> None:
        #pt = event.pos()
        #x, y = pt.x(), pt.y()
        #print(f'{self.__class__.__name__} {type(event)} {x} {y}')
        if not self.audioDeviceManager:
            return
        deviceList = self.audioDeviceManager.enumerateAudioCaptureDevices2()
        if not deviceList:
            return
        curDeviceId, ret = self.audioDeviceManager.getAudioCaptureDevice()
        print(f'cur audio device id: {curDeviceId}')
        self.admActions = []
        menu = QMenu(self)
        for deviceInfo in deviceList:
            action = QAction(deviceInfo.device_name, checkable=True)
            action.setChecked(curDeviceId == deviceInfo.device_id)
            action.setData(deviceInfo.device_id)
            action.triggered.connect(self.onActionSetAudioCaptureDevice)
            self.admActions.append(action)
            menu.addAction(action)
        menu.exec_(QCursor.pos())

    def onActionSetAudioCaptureDevice(self) -> None:
        if not self.audioDeviceManager:
            return
        action = self.sender()
        if action and self.audioDeviceManager:
            self.audioDeviceManager.setAudioCaptureDevice(action.data())

    def onLabelCamerasMouseRleaseEvent(self, event: QMouseEvent) -> None:
        if not self.videoDeviceManager:
            return
        deviceList = self.videoDeviceManager.enumerateVideoCaptureDevices2()
        if not deviceList:
            return
        curDeviceId, ret = self.videoDeviceManager.getVideoCaptureDevice()
        print(f'cur video device id: {curDeviceId}')
        self.vdmActions = []
        menu = QMenu(self)
        for deviceInfo in deviceList:
            action = QAction(deviceInfo.device_name, checkable=True)
            action.setChecked(curDeviceId == deviceInfo.device_id)
            action.setData(deviceInfo.device_id)
            action.triggered.connect(self.onActionSetVideoDevice)
            self.vdmActions.append(action)
            menu.addAction(action)
        menu.exec_(QCursor.pos())

    def onLabelBackgroundsMouseRleaseEvent(self, event: QMouseEvent) -> None:
        self.backgroundActions = []
        menu = QMenu(self)
        bgDir = os.path.join(sdk.ExeDir, 'VirtualBackgroundImages')
        for filePath, fileName, isDir, depth, remainCount in util.walkDir(bgDir, maxDepth=1):
            if fileName.endswith('.jpg') or fileName.endswith('.png'):
                action = QAction(f'背景({fileName})', checkable=True)
                action.setChecked(fileName == self.configJson['backgroundImage'])
                action.setData(filePath)
                action.triggered.connect(self.onActionSetVirtualBackground)
                self.backgroundActions.append(action)
                menu.addAction(action)
        menu.exec_(QCursor.pos())

    def onActionSetVideoDevice(self) -> None:
        if not self.videoDeviceManager:
            return
        action = self.sender()
        if action and self.videoDeviceManager:
            self.videoDeviceManager.setVideoCaptureDevice(action.data())

    def onActionSetVirtualBackground(self) -> None:
        action = self.sender()
        if action and self.videoEffect:
            imagePath = action.data()
            stickerPath = os.path.join(sdk.SdkBinDirFull, '../cvlab/ComposeMakeup/matting_bg')
            virtualSource = sdk.VirtualBackgroundSource(source_type=sdk.VirtualBackgroundSourceType.Image,
                                                        source_color=0xFFFFFFFF, source_path=imagePath)
            ret = self.videoEffect.enableVirtualBackground(stickerPath, virtualSource)
            bgDir, bgName = os.path.split(imagePath)
            self.configJson['backgroundImage'] = bgName
            util.jsonToFile(self.configJson, self.configPath)

    def onLabelMsgMouseRleaseEvent(self, event: QMouseEvent) -> None:
        self.showMsg = not self.showMsg
        if self.showMsg:
            self.msgShowStateLabel.setText('>>消息')
            self.msgWidget.show()
        else:
            self.msgShowStateLabel.setText('<<消息')
            self.msgWidget.hide()

    def onClickJoinRoomBtn(self) -> None:
        roomId = self.roomIdEdit.text().strip()
        nickName = self.nameEdit.text().strip()
        if self.joinBtn.text() == JoinName:
            if not roomId:
                self.tipDlg.showTip('房间名不能为空')
                return
            if not nickName:
                self.tipDlg.showTip('昵称不能为空')
                return
            self.configJson['roomId'] = roomId
            self.configJson['nickName'] = nickName
            util.jsonToFile(self.configJson, self.configPath)
            token = ''
            while 1:
                self.userId = ''.join(random.choices(string.ascii_lowercase, k=3)) + str(random.randint(1, 10000))
                if 'sb' not in self.userId:
                    break
            userInfo = sdk.UserInfo(uid=self.userId, extra_info='{"nickName":"%s"}' % nickName)
            roomConfig = sdk.RTCRoomConfig(room_profile_type=sdk.RoomProfileType.LiveBroadcasting)
            roomConfig.is_auto_publish = False
            roomConfig.is_auto_subscribe_audio = True
            roomConfig.is_auto_subscribe_video = False
            if roomId in self.rtcRooms:
                rtcRoom = self.rtcRooms[roomId]
            else:
                rtcRoom = self.rtcVideo.createRTCRoom(roomId)
                rtcRoomEventHandler = RTCRoomEventHandler(self, roomId)
                rtcRoom.setRTCRoomEventHandler(rtcRoomEventHandler)
                self.rtcRooms[roomId] = rtcRoom
                self.rtcRoomEventHandlers[roomId] = rtcRoomEventHandler
                self.roomUsers = {}
                self.roomUserViews = {}
                self.activeRemoteSpeakers = []
            apConfig = sdk.AudioPropertiesConfig(interval=ActiveSpeackerIntervalMs, enable_spectrum=False, enable_vad=False)
            self.rtcVideo.enableAudioPropertiesReport(apConfig)
            rtcRoom.joinRoom(token, user_info=userInfo, room_config=roomConfig)
            self.rtcRoomJoined[roomId] = False
            self.roomIdEdit.setReadOnly(True)
            self.nameEdit.setReadOnly(True)
            self.joinBtn.setEnabled(False)

            if self.configJson['enableAudio']:
                rtcRoom.publishStream(sdk.MediaStreamType.Audio)
            mute = not self.configJson['enableAudio']
            self.videoManagerW.setAudioState(self.localViews[sdk.StreamIndex.Main], mute)
            if self.configJson['enableVideo']:
                rtcRoom.publishStream(sdk.MediaStreamType.Video)

        else:#leaveRoom
            self.onClickLeaveRoomBtn(roomId)

    def onClickLeaveRoomBtn(self, roomId: str) -> None:
        if self.screenShareStarted:
            self.onClickScreenShareBtn()
        rtcRoom = self.rtcRooms.pop(roomId)
        rtcRoom.leaveRoom()
        rtcRoom.destroy()
        self.rtcRoomJoined[roomId] = False
        self.roomUsers.clear()
        self.roomIdEdit.setReadOnly(False)
        self.nameEdit.setReadOnly(False)
        self.joinBtn.setEnabled(True)
        self.joinBtn.setText(JoinName)
        self.screenShareBtn.hide()
        self.enableScreenAudioCheck.hide()
        self.sendMsgBtn.setEnabled(False)
        #self.msgShowStateLabel.hide()
        #if self.showMsg:
            #self.msgShowStateLabel.setText('<<消息')
            #self.msgWidget.hide()
            #self.showMsg = False
        self.videoManagerW.setMaxView(self.localViews[sdk.StreamIndex.Main])
        for (userId, streamIndex), view in self.roomUserViews.items():
            self.videoManagerW.freeView(view, False)
        self.videoManagerW.reLayout()
        self.roomUserViews.clear()
        self.activeRemoteSpeakers.clear()
        self.roomTimer.stop()
        self.setWindowTitle(DemoTitle)

    def onClickScreenShareBtn(self) -> None:
        if self.screenShareStarted:
            #stop screen share
            roomId = self.roomIdEdit.text().strip()
            #rtcRoom = sdk.RTCRoom()
            rtcRoom = self.rtcRooms[roomId]
            rtcRoom.unpublishScreen(sdk.MediaStreamType.Video)
            self.rtcVideo.stopScreenVideoCapture()
            self.screenShareStarted = False
            view = self.localViews.pop(sdk.StreamIndex.Screen)
            self.videoManagerW.freeView(view, reLayout=True)
            self.screenShareBtn.setText('屏幕分享')
            if self.enableScreenAudioCheck.isChecked():
                self.enableScreenAudioCheck.setChecked(False)
                self.onClickEnableScreenAudioCheck()
            self.enableScreenAudioCheck.hide()
        else:
            #start screen share
            sourceList = self.rtcVideo.getScreenCaptureSourceList()
            if sourceList:
                imageList = []
                for n, sourceInfo in enumerate(sourceList):
                    videoFrame = self.rtcVideo.getThumbnail(sourceInfo.type, sourceInfo.source_id, 320, 180)
                    qimg = None
                    if videoFrame:
                        width, height = videoFrame.width(), videoFrame.height()
                        arrayType = (ctypes.c_uint8 * (videoFrame.getPlaneStride(0) * height))
                        frameBuf = arrayType.from_address(videoFrame.getPlaneData(0).value)
                        imagaBytes = bytes(frameBuf)    #need to copy the buffer before calling videoFrame.release
                        qimg = QImage(imagaBytes, width, height, width * 4, QImage.Format_ARGB32)
                        #qimg.save(f'share{n}.bmp')
                        videoFrame.release()
                    imageList.append(qimg)
                self.screenShareDlg.selectScreenShare(sourceList, imageList)

    def onClickEnableScreenAudioCheck(self) -> None:
        roomId = self.roomIdEdit.text().strip()
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        if self.enableScreenAudioCheck.isChecked():
            self.rtcVideo.startScreenAudioCapture(None)
            rtcRoom.publishScreen(sdk.MediaStreamType.Audio)
            mute = False
        else:
            self.rtcVideo.stopScreenAudioCapture()
            rtcRoom.unpublishScreen(sdk.MediaStreamType.Audio)
            mute = True
        view = self.localViews.get(sdk.StreamIndex.Screen, None)
        if view:
            self.videoManagerW.setAudioState(view, mute)

    def onStartScreenCapture(self, source_info: sdk.ScreenCaptureSourceInfo, thumbWidth: int, thumbHeight: int) -> None:
        width, height = 1280, 720
        if source_info.source_name.startswith(r'\\.\DISPLAY') or source_info.source_name == 'VirtualDesktop':
            width = 1920
            height = width * thumbHeight // thumbWidth
            height -= height % 2
        if sdk.SdkVersion >= '3.48':
            videoEncoderConfig = sdk.ScreenVideoEncoderConfig()
            videoEncoderConfig.minBitrate = 0
        else:
            videoEncoderConfig = sdk.VideoEncoderConfig()
        videoEncoderConfig.width = width
        videoEncoderConfig.height = height
        videoEncoderConfig.frameRate = 15
        videoEncoderConfig.maxBitrate = -1
        videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Quality
        self.rtcVideo.setScreenVideoEncoderConfig(videoEncoderConfig)

        viewHandle, isShow, videoSize = self.videoManagerW.getNewView()
        self.videoManagerW.setViewInfo(viewHandle, '(我)', True)
        videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=sdk.RenderMode.Fit, background_color=0xDDDDDD)
        index = sdk.StreamIndex.Screen
        self.rtcVideo.setLocalVideoCanvas(index, videoCanvas)

        self.localViews[sdk.StreamIndex.Screen] = viewHandle

        captureParam = sdk.ScreenCaptureParameters()
        captureParam.capture_mouse_cursor = True
        captureParam.content_hint = sdk.ContentHint.Details
        captureParam.filter_config = sdk.ScreenFilterConfig()
        captureParam.filter_config.excluded_window_list = []    #[0x13143, 0x31434]
        captureParam.highlight_config = sdk.HighlightConfig()
        captureParam.highlight_config.border_color = 0xFF29CCA3
        captureParam.highlight_config.enable_highlight = True
        captureParam.highlight_config.border_width = 4
        #captureParam.region_rect = sdk.Rectangle(x=0, y=0, width=1920, height=1080)

        self.rtcVideo.startScreenVideoCapture(source_info, captureParam)
        roomId = self.roomIdEdit.text().strip()
        rtcRoom = self.rtcRooms[roomId]
        rtcRoom.publishScreen(sdk.MediaStreamType.Video)
        self.screenShareStarted = True
        self.screenShareBtn.setText('停止分享')
        self.enableScreenAudioCheck.show()

    def onRemoteVideoViewShowStateChanged(self, args: Tuple[int, bool]) -> None:
        view, isShow = args
        for (userId, streamIndex), viewHandle in self.roomUserViews.items():
            if viewHandle == view:
                break
        else:
            return
        roomId = self.roomIdEdit.text().strip()
        if not roomId in self.rtcRooms:
            return
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        if isShow:
            rtcRoom.subscribeStream(userId, sdk.MediaStreamType.Video)
        else:
            rtcRoom.unsubscribeStream(userId, sdk.MediaStreamType.Video)

    def onRemoteVideoViewSizeChanged(self, args: Tuple[int, int, int]) -> None:
        view, width, height = args
        for (userId, streamIndex), viewHandle in self.roomUserViews.items():
            if viewHandle == view:
                break
        else:
            return
        #if streamIndex == sdk.StreamIndex.Screen:
            #return #todo
        roomId = self.roomIdEdit.text().strip()
        if not roomId in self.rtcRooms:
            return
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        if width * height > 1120 * 630:
            videoConfig = sdk.RemoteVideoConfig(25, 1280, 720)
        elif width * height > 800 * 450:
            videoConfig = sdk.RemoteVideoConfig(25, 960, 640)
        elif width * height > 480 * 270:
            videoConfig = sdk.RemoteVideoConfig(25, 640, 360)
        elif width * height > 240 * 135:
            videoConfig = sdk.RemoteVideoConfig(25, 320, 180)
        else:
            videoConfig = sdk.RemoteVideoConfig(25, 160, 90)
        rtcRoom.setRemoteVideoConfig(userId, videoConfig)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.x(), event.y()
        print(f'{x} {y}')

    def moveEvent(self, event: QMoveEvent) -> None:
        pos = event.pos()
        x, y = pos.x(), pos.y()
        print(f'{x} {y}')

    def resizeEvent(self, event: QResizeEvent) -> None:
        size = event.size()
        width, height = size.width(), size.height()
        print(f'{width} {height}')

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Return:
            event.accept()
            self.onClickSendMsgBtn()

    def onRoomTimer(self) -> None:
        elapsed = int(time.monotonic() - self.roomStartTick)
        hours = elapsed // 3600
        minutes = elapsed % 3600 // 60
        seconds = elapsed % 60
        if hours > 0:
            self.setWindowTitle(f'{DemoTitle}  {hours:02}{minutes:02}:{seconds:02}')
        else:
            self.setWindowTitle(f'{DemoTitle}  {minutes:02}:{seconds:02}')

    def onRTCVideoEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        '''not run in UI thread'''
        eventStr = util.prettyDict(event, indent=1, indentStr="\t")
        if event_name != 'onRemoteAudioPropertiesReport' and event_name != 'onLocalAudioPropertiesReport':
            sdk.log.info(f'{event_name} {event_time}\n{eventStr}')
        self.RTCVideoEventSignal.emit((event_time, event_name, event_json, event))

    def onRTCRoomEventHappen(self, room_id: str, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        '''not run in UI thread'''
        eventStr = util.prettyDict(event, indent=1, indentStr="\t")
        sdk.log.info(f'room_id: {room_id} {event_name} {event_time}\n{eventStr}')
        self.RTCRoomEventSignal.emit((room_id, event_time, event_name, event_json, event))

    def onRTCVideoEvent(self, args: Tuple[int, int, str, dict]):
        '''runs in UI thread'''
        self.handleRTCEvent('RTCVideo', self.RTCVideoEventHandler, args)

    def onRTCRoomEvent(self, args: Tuple[str, int, int, str, dict]):
        '''runs in UI thread'''
        self.currentEventRoomId = args[0]
        self.handleRTCEvent('RTCRoom', self.RTCRoomEventHandler, args[1:])

    def handleRTCEvent(self, eventType: str, eventHandler: dict, args: Tuple[int, int, str, dict]):
        event_time, event_name, event_json, event = args
        func = eventHandler.get(event_name, None)
        if func:
            func(event_time, event_name, event_json, event)
        else:
            #sdk.log.info(f'cannot get handler for {event_name}')
            pass

    def initializeEventHandlers(self) -> None:
        self.RTCVideoEventHandler = {
            # 'onError': self.onError,
            # 'onWarning': self.onWarning,
            'onConnectionStateChanged': self.onConnectionStateChanged,
            'onTakeLocalSnapshotResult': self.onTakeLocalSnapshotResult,
            'onActiveSpeaker': self.onActiveSpeaker,
        }

        self.RTCRoomEventHandler = {
            'onRoomStateChanged': self.onRoomStateChanged,
            'onUserJoined': self.onUserJoined,
            'onUserLeave': self.onUserLeave,
            'onUserPublishStream': self.onUserPublishStream,
            'onUserUnpublishStream': self.onUserUnpublishStream,
            'onUserPublishScreen': self.onUserPublishScreen,
            'onUserUnpublishScreen': self.onUserUnpublishScreen,
            'onRoomMessageReceived': self.onRoomMessageReceived,
        }
    # RTCVideo Event Handler

    def onConnectionStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        pass

    def onTakeLocalSnapshotResult(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        videoFrame = sdk.IVideoFrame(event['video_frame'])
        try:
            from PIL import Image
            arrayType = (ctypes.c_uint8 * (videoFrame.getPlaneStride(0) * videoFrame.height()))
            frameBuf = arrayType.from_address(videoFrame.getPlaneData(0).value)
            image = Image.frombytes('RGBA', (videoFrame.width(), videoFrame.height()), frameBuf, 'raw', 'BGRA')
            image.save('localSnapshot.bmp')
        except Exception as ex:
            pass
        videoFrame.release()

    def onTakeRemoteSnapshotResult(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        videoFrame = sdk.IVideoFrame(event['video_frame'])
        try:
            from PIL import Image
            arrayType = (ctypes.c_uint8 * (videoFrame.getPlaneStride(0) * videoFrame.height()))
            frameBuf = arrayType.from_address(videoFrame.getPlaneData(0).value)
            image = Image.frombytes('RGBA', (videoFrame.width(), videoFrame.height()), frameBuf, 'raw', 'BGRA')
            image.save('remoteSnapshot.bmp')
        except Exception as ex:
            pass
        videoFrame.release()

    # RTCRoom Event Handler
    def onRoomStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        state = event['state']
        if state != 0:
            errorInfo = sdk.getErrorDescription(state)
            sdk.log.info(f'error desc: {errorInfo}')
            self.tipDlg.showTip(errorInfo)
        else:
            roomId = event["room_id"]
            self.rtcRoomJoined[roomId] = True
            self.joinBtn.setText('离开房间')
            self.screenShareBtn.show()
            #self.enableScreenAudioCheck.show()
            self.msgShowStateLabel.show()
            self.sendMsgBtn.setEnabled(True)
            self.setWindowTitle(f'{DemoTitle}  00:00')
            self.roomStartTick = time.monotonic()
            self.roomTimer.start(1000)
        self.joinBtn.setEnabled(True)

    def onUserJoined(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRooms:
            return
        roomId = self.currentEventRoomId
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        userId = event['user_info']['uid']
        nickName = event['user_info']['extra_info'].get('nickName', 'Unknown')
        self.roomUsers[userId] = nickName
        viewHandle, isShow, videoRect = self.videoManagerW.getNewView()
        self.roomUserViews[(userId, sdk.StreamIndex.Main)] = viewHandle
        self.videoManagerW.setViewInfo(viewHandle, nickName, True)
        if isShow:
            width, height = videoRect[2], videoRect[3]
            if width * height > 1120 * 630:
                videoConfig = sdk.RemoteVideoConfig(25, 1280, 720)
            elif width * height > 800 * 450:
                videoConfig = sdk.RemoteVideoConfig(25, 960, 640)
            elif width * height > 480 * 270:
                videoConfig = sdk.RemoteVideoConfig(25, 640, 360)
            elif width * height > 240 * 135:
                videoConfig = sdk.RemoteVideoConfig(25, 320, 180)
            else:
                videoConfig = sdk.RemoteVideoConfig(25, 160, 90)
            rtcRoom.setRemoteVideoConfig(userId, videoConfig)
            rtcRoom.subscribeStream(userId, sdk.MediaStreamType.Video)
        remoteStreamKey = sdk.RemoteStreamKey(room_id=roomId, user_id=userId, stream_index=sdk.StreamIndex.Main)
        videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=sdk.RenderMode.Fit, background_color=ViewBackground)
        if sdk.SdkVersion >= '3.47':
            self.rtcVideo.setRemoteVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        else:
            self.rtcVideo.setRemoteStreamVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)

    def onUserLeave(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRooms:
            return
        roomId = self.currentEventRoomId
        userId = event['user_id']
        #reason=event['reason']
        self.roomUsers.pop(userId)
        view = self.roomUserViews.pop((userId, sdk.StreamIndex.Main))
        self.videoManagerW.freeView(view)
        if (userId, sdk.StreamIndex.Screen) in self.roomUserViews:
            view = self.roomUserViews.pop((userId, sdk.StreamIndex.Screen))
            self.videoManagerW.freeView(view)
        if not self.roomUserViews:
            self.videoManagerW.setMaxView(self.localViews[sdk.StreamIndex.Main])
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        rtcRoom.unsubscribeStream(userId, sdk.MediaStreamType.Video)
        if userId in self.activeRemoteSpeakers:
            self.activeRemoteSpeakers.remove(userId)

    def onUserPublishStream(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRooms:
            return
        roomId = self.currentEventRoomId
        userId = event['user_id']
        changeAudio = event['type'] & sdk.MediaStreamType.Audio
        changeVideo = event['type'] & sdk.MediaStreamType.Video
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        if changeAudio:
            mute = False
            self.videoManagerW.setAudioState(self.roomUserViews[(userId, sdk.StreamIndex.Main)], mute)
            #rtcRoom.subscribeStream(userId, sdk.MediaStreamType.Audio)
        if changeVideo:
            if self.localViews[sdk.StreamIndex.Main] in self.videoManagerW.getMaxView():
                self.videoManagerW.setMaxView(self.roomUserViews[(userId, sdk.StreamIndex.Main)])

    def onUserUnpublishStream(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRooms:
            return
        roomId = self.currentEventRoomId
        userId = event['user_id']
        changeAudio = event['type'] & sdk.MediaStreamType.Audio
        changeVideo = event['type'] & sdk.MediaStreamType.Video
        if changeAudio:
            mute = True
            self.videoManagerW.setAudioState(self.roomUserViews[(userId, sdk.StreamIndex.Main)], mute)
        if changeVideo:
            self.videoManagerW.resetVideoBack(self.roomUserViews[(userId, sdk.StreamIndex.Main)])

    def onUserPublishScreen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRooms:
            return
        roomId = self.currentEventRoomId
        userId = event['user_id']
        #rtcRoom = sdk.RTCRoom()
        rtcRoom = self.rtcRooms[roomId]
        changeAudio = event['type'] & sdk.MediaStreamType.Audio
        changeVideo = event['type'] & sdk.MediaStreamType.Video
        if changeVideo:
            nickName = self.roomUsers[userId]
            viewHandle, isShow, videoRect = self.videoManagerW.getNewView()
            for maxView in self.videoManagerW.getMaxView():
                if not self.isViewScreen(maxView):
                    self.videoManagerW.setMaxView(viewHandle)
                    isShow = True
                    break
            self.videoManagerW.setViewInfo(viewHandle, nickName, True)
            self.roomUserViews[(userId, sdk.StreamIndex.Screen)] = viewHandle
            if isShow:
                rtcRoom.subscribeScreen(userId, sdk.MediaStreamType.Video)
            remoteStreamKey = sdk.RemoteStreamKey(room_id=roomId, user_id=userId, stream_index=sdk.StreamIndex.Screen)
            videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=sdk.RenderMode.Fit, background_color=ViewBackground)
            if sdk.SdkVersion >= '3.47':
                self.rtcVideo.setRemoteVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
            else:
                self.rtcVideo.setRemoteStreamVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        if changeAudio:
            rtcRoom.subscribeScreen(userId, sdk.MediaStreamType.Audio)
            view = self.roomUserViews.get((userId, sdk.StreamIndex.Screen), None)
            if view:
                mute = False
                self.videoManagerW.setAudioState(view, mute)

    def onUserUnpublishScreen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRooms:
            return
        roomId = self.currentEventRoomId
        userId = event['user_id']
        changeAudio = event['type'] & sdk.MediaStreamType.Audio
        changeVideo = event['type'] & sdk.MediaStreamType.Video
        if changeAudio:
            view = self.roomUserViews.get((userId, sdk.StreamIndex.Screen), None)
            if view:
                mute = True
                self.videoManagerW.setAudioState(view, mute)
        if changeVideo:
            view = self.roomUserViews.pop((userId, sdk.StreamIndex.Screen))
            self.videoManagerW.freeView(view, reLayout=True)

    def isViewScreen(self, view) -> bool:
        for (userId, streamIndex), viewHandle in self.roomUserViews.items():
            if view == viewHandle:
                return streamIndex == sdk.StreamIndex.Screen
        return False

    def onActiveSpeaker(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        roomId = event['room_id']
        userId = event['user_id']
        if roomId not in self.rtcRooms:
            return
        if userId == self.userId:
            view = self.localViews[sdk.StreamIndex.Main]
        else:
            view = self.roomUserViews.get((userId, sdk.StreamIndex.Main), 0)
            if not view:
                return
        self.videoManagerW.setActiveVideo(view)
        if self.lastCancelActiveColorTimer:
            self.lastCancelActiveColorTimer.stop()
        self.lastCancelActiveColorTimer = self.delayCall(timeMs=ActiveSpeackerIntervalMs + 100, func=self.videoManagerW.setNoActiveVideo)
        if userId == self.userId:
            return
        if userId in self.activeRemoteSpeakers:
            self.activeRemoteSpeakers.remove(userId)
        self.activeRemoteSpeakers.append(userId)
        if len(self.activeRemoteSpeakers) > 5:
            self.activeRemoteSpeakers.pop(0)
        vViews = self.videoManagerW.getVisibleViewsOnTop()
        if view not in vViews:
            activeViews = [self.roomUserViews[(uid, sdk.StreamIndex.Main)] for uid in self.activeRemoteSpeakers]
            for n in range(len(vViews) - 1, -1, -1):
                if vViews[n] not in activeViews:
                    self.videoManagerW.setViewToPosOnTop(view, n)
                    break

    def onRoomMessageReceived(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        roomId = self.currentEventRoomId
        userId = event['user_id']
        message = event['message']
        if roomId not in self.rtcRooms:
            return
        nickName = self.roomUsers[userId]
        t = datetime.datetime.now()
        timeStr = f'{t.year}-{t.month:02}-{t.day:02} {t.hour:02}:{t.minute:02}:{t.second:02}'
        self.historyMsgEdit.append(f'<font color=green>{timeStr}    {nickName}(uid:{userId}):</font><br>{message}<br>')
        currentCursor = self.historyMsgEdit.textCursor()
        currentCursor.movePosition(QTextCursor.End)
        self.historyMsgEdit.setTextCursor(currentCursor)


def _start():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        _start()
    except Exception as ex:
        logstr = traceback.format_exc()
        sdk.log.error(logstr)
        print(logstr)
        input('\nSomething wrong. Please input Enter to exit.')
    sys.exit(0)
