#!python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
from __future__ import annotations
import os
import sys
import time
import math
import json
import types
import ctypes
import pprint
import random
import datetime
import threading
import traceback
import subprocess
from typing import Any, Callable, Dict, List, Tuple
import util
from bytertcsdk import bytertcsdk as sdk
from PyQt5.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QColor, QContextMenuEvent, QCursor, QFont, QIcon, QIntValidator, QKeyEvent, QMouseEvent, QPainter, QPixmap, QTextCursor, QTextOption
from PyQt5.QtWidgets import QAction, QApplication, QDesktopWidget, QDialog, QInputDialog, QMainWindow, QMenu, QMessageBox, QWidget, qApp
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QListView, QPushButton, QRadioButton, QSlider, QPlainTextEdit, QTextEdit, QToolTip
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QSplitter, QVBoxLayout
from QCodeEditor import QCodeEditor
import pyqt5AsyncTask as astask


DPIScale = 1  # 1.5
ButtonHeight = 30
ComboxItemHeight = 28
EditHeight = 28
DemoTile = 'ByteRtcDemo'
IcoPath = os.path.join(sdk.ExeDir, 'byte.ico')
RtcVideo = None
SDKDllName = 'ByteRTCPythonSDK.dll'
DevelopDllDir = ''
print = util.printx

#QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def dpiSize(size: int) -> int:
    return int(size * DPIScale)


class SelectSdkDlg(QDialog):
    def __init__(self, parent: QObject = None, selectCallback: Callable[[str], None] = None):
        super(SelectSdkDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        isX64 = sys.maxsize > 0xFFFFFFFF
        bit = 2 if isX64 else 1
        self.setWindowTitle(f'Select SDK Version')
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(dpiSize(300), dpiSize(200))
        self.selectCallback = selectCallback

        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        tipLabel = QLabel(f'App is {32 * bit} bit, select a SDK:')
        vLayout.addWidget(tipLabel)
        self.radioButtons = []
        self.sdkDirs = {}
        prefix = f'binx{"64" if isX64 else "86"}_'
        for filePath, isDir, fileName in util.listDir((sdk.SdkDirFull, True, None)):
            if isDir and fileName.startswith(prefix):
                sdkVersionStr = fileName[len(prefix):]
                self.sdkDirs[sdkVersionStr] = fileName
                radio = QRadioButton(sdkVersionStr)
                radio.setMinimumHeight(ButtonHeight)
                vLayout.addWidget(radio)
                self.radioButtons.append(radio)
        if len(self.radioButtons) == 1:
            self.radioButtons[0].setChecked(True)

        useButton = QPushButton('Use')
        useButton.setMinimumHeight(ButtonHeight)
        useButton.clicked.connect(self.onClickUse)
        vLayout.addWidget(useButton)

    def onClickUse(self) -> None:
        for radio in self.radioButtons:
            if radio.isChecked():
                break
        else:
            return
        sdkBinDir = self.sdkDirs[radio.text()]
        self.selectCallback(sdkBinDir)
        sdkBinPath = os.path.join(sdk.SdkBinDirFull, SDKDllName)
        if not os.path.exists(sdkBinPath):
            print(f'---- {sdkBinPath} does not exist')
            # load dll in develop code path
            binDirs = util.getFileText(os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.dllpath')).splitlines()
            for binDir in binDirs:
                binPath = os.path.join(binDir, SDKDllName)
                if os.path.exists(binPath):
                    global DevelopDllDir
                    DevelopDllDir = binDir
                    print(f'---- add dll dir: {binDir}')
                    os.environ["PATH"] = binDir + os.pathsep + os.environ["PATH"]
                    if sdk.isPy38OrHigher():
                        os.add_dll_directory(binDir)
                    break
                else:
                    print(f'---- develop dir: {binDir} does not exist')

    def closeEvent(self, event: QCloseEvent) -> None:
        # print('select dlg QCloseEvent')
        pass


class TipDlg(QDialog):
    def __init__(self, parent: QObject = None, tipTime=6):
        super(TipDlg, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)  # Qt.Tool makes no display on taskbar
        self.resize(dpiSize(200), dpiSize(100))
        self.setMaximumWidth(dpiSize(1280))
        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)
        self.tipLabel = QLabel('No Error')
        self.tipLabel.setMaximumWidth(dpiSize(1200))
        self.tipLabel.setWordWrap(True)
        self.tipLabel.setAlignment(Qt.AlignTop)
        self.tipLabel.setStyleSheet('QLabel{color:rgb(255,0,0);font-size:%dpx;font-weight:bold;font-family:Verdana;border: 2px solid #FF0000}' % dpiSize(20))
        self.gridLayout.addWidget(self.tipLabel, 0, 0)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.tipTime = tipTime * 1000

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
        self.timer.start(self.tipTime)
        if msg:
            self.tipLabel.setText(msg)
        self.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.raise_()
        self.activateWindow()


class CodeDlg(QDialog):
    Signal = pyqtSignal(str)

    def __init__(self, parent: QObject = None):
        super(CodeDlg, self).__init__(parent)
        self.mainWindow = parent
        self.threadId = threading.currentThread().ident
        self.setWindowFlags(Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(f"Python {sys.version.split()[0]} Code Executor ")
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(dpiSize(1200), dpiSize(600))
        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.apiCombox = QComboBox()
        self.apiCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(22))
        self.apiCombox.setView(QListView())
        self.apiCombox.setMinimumHeight(dpiSize(24))
        self.apiCombox.currentIndexChanged.connect(self.onComboxApiSelectionChanged)
        hLayout.addWidget(self.apiCombox)

        button = QPushButton('append')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickAppend)
        hLayout.addWidget(button)

        button = QPushButton('replace')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickReplace)
        hLayout.addWidget(button)

        button = QPushButton('e&xec')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickRun)
        hLayout.addWidget(button)

        button = QPushButton('e&val')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickRun)
        hLayout.addWidget(button)

        button = QPushButton('reload')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickReload)
        hLayout.addWidget(button)

        self.saveButton = QPushButton('save')
        self.saveButton.setMinimumHeight(ButtonHeight)
        self.saveButton.clicked.connect(self.onClickSave)
        hLayout.addWidget(self.saveButton)

        button = QPushButton('clearCode')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickClearCode)
        hLayout.addWidget(button)

        button = QPushButton('clearOutput')
        button.setMinimumHeight(ButtonHeight)
        button.clicked.connect(self.onClickClearOutput)
        hLayout.addWidget(button)

        self.checkScrollToEnd = QCheckBox('AutoScrollToEnd')
        self.checkScrollToEnd.setChecked(True)
        hLayout.addWidget(self.checkScrollToEnd)

        self.qsplitter = QSplitter(Qt.Vertical)
        vLayout.addWidget(self.qsplitter)
        self.codeEdit = QCodeEditor()
        self.codeEdit.setStyleSheet('QPlainTextEdit{font-size:%dpx;font-family:Consolas;background-color:rgb(204,232,207);}' % dpiSize(16))
        # self.codeEdit.setPlainText(codeText)
        self.qsplitter.addWidget(self.codeEdit)
        self.outputEdit = QPlainTextEdit()
        self.outputEdit.setStyleSheet('QPlainTextEdit{font-size:%dpx;font-family:Consolas;background-color:rgb(204,232,207);}' % dpiSize(14))
        self.qsplitter.addWidget(self.outputEdit)
        self.qsplitter.setSizes([100, 100])
        self.Signal.connect(self.outputEdit.appendPlainText)
        sdk.GuiStreamObj.setLogHandler(self.logCallbackHandler)

        self.loadApiList()

    def onComboxApiSelectionChanged(self, index: int) -> None:
        self.saveButton.setEnabled(index >= len(self.singleApis))

    def onClickSave(self) -> None:
        code = self.codeEdit.toPlainText().strip()
        if not code:
            return
        self.multiApis[self.apiCombox.currentText()] = code
        self.saveApiList()

    def onClickReload(self) -> None:
        self.loadApiList()

    def onClickAppend(self) -> None:
        index = self.apiCombox.currentIndex()
        if index < 0:
            return
        if index < len(self.singleApis):
            code = self.singleApis[self.apiCombox.currentText()]
            self.codeEdit.appendPlainText(code)
        else:
            code = self.multiApis[self.apiCombox.currentText()]
            self.codeEdit.setPlainText(code)

    def onClickReplace(self) -> None:
        self.onClickClearCode()
        self.onClickAppend()

    def onClickRun(self) -> None:
        button = self.sender()
        if not (button and isinstance(button, QPushButton)):
            return
        self.scrollToEnd()
        try:
            text = self.codeEdit.toPlainText()
            #print(type(text), text)
            if button.text() == 'e&val':
                ret = self.mainWindow.evalCode(text)
                sdk.log.info(f'eval(...) = {ret}\n')
            else:  # exec
                self.mainWindow.execCode(text)
                sdk.log.info(f'exec(...) done\n')
        except Exception as ex:
            self.outputEdit.appendPlainText(f'\n{ex}\n{traceback.format_exc()}\n')
        self.scrollToEnd()

    def onClickClearCode(self) -> None:
        self.codeEdit.clear()

    def onClickClearOutput(self) -> None:
        self.outputEdit.clear()

    def scrollToEnd(self) -> None:
        if self.checkScrollToEnd.isChecked():
            currentCursor = self.outputEdit.textCursor()
            currentCursor.movePosition(QTextCursor.End)
            self.outputEdit.setTextCursor(currentCursor)

    def loadApiList(self) -> None:
        curIndex = self.apiCombox.currentIndex()
        apiPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.code')
        text = util.getFileText(apiPath)
        self.singleApis = {}
        self.multiApis = {}
        self.boundary = '\n----boundary----'
        index = 0
        while True:
            name, found = util.getStrBetween(text, left='name=', right='\n', start=index)
            if found < 0:
                break
            index += len(name) + 1
            editable, found = util.getStrBetween(text, left='editable=', right='\n', start=index)
            if found < 0:
                break
            index += len(editable) + 1
            editable = int(editable)
            code, found = util.getStrBetween(text, left='code=', right=self.boundary, start=index)
            if found < 0:
                break
            index += len(code) + len(self.boundary)
            code = code.strip()
            if editable:
                self.multiApis[name] = code
            else:
                self.singleApis[name] = code
        self.apiCombox.clear()
        names = list(self.singleApis.keys())
        names.sort()
        self.apiCombox.addItems(names)
        self.apiCombox.addItems(self.multiApis.keys())
        if self.apiCombox.count() > curIndex:
            self.apiCombox.setCurrentIndex(curIndex)

    def saveApiList(self) -> None:
        apiPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.code')
        text = '\n'.join(f'name={name}\neditable=0\ncode=\n\n{content}\n{self.boundary}\n' for name, content in self.singleApis.items())
        util.writeTextFile(text, apiPath)
        text = '\n'.join(f'name={name}\neditable=1\ncode=\n\n{content}\n{self.boundary}\n' for name, content in self.multiApis.items())
        util.appendTextFile('\n', apiPath)
        util.appendTextFile(text, apiPath)

    def close(self) -> bool:
        sdk.GuiStreamObj.setLogHandler(None)
        return super(CodeDlg, self).close()

    def logCallbackHandler(self, output: str) -> None:
        if threading.currentThread().ident == self.threadId:
            self.outputEdit.appendPlainText(output)
        else:
            self.Signal.emit(output)


class MainWindow(QMainWindow, astask.AsyncTask):
    CallbackSignal = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        sdk.log.info(f'sys.paltform={sys.platform}, ExePath={sdk.ExePath}, cwd={os.getcwd()}, uithread={threading.get_ident()}')
        self.configPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.config')
        self.configJson = util.jsonFromFile(self.configPath)
        self.videoLabels = []
        self.viewUsingIndex = set()
        self.viewCount = 0
        self.maximizedVideoLabelIndex = -1
        self.menuShowOnVideoLableIndex = -1
        self.mousePressOnVideoLabelIndex = -1
        self.createUI()
        self.initUI()
        self.selectSdkDlg = SelectSdkDlg(self, selectCallback=self.onSelectSdkCallback)
        self.tipDlg = TipDlg(None)
        self.codeDlg = CodeDlg(self)
        self.selectSdkDlg.exec()
        # after exec, console window is active, set MainWindow active in timer
        if sys.stdout:
            self.delayCall(timeMs=100, func=self.activateWindow)

        self.rtcVideo = None  # sdk.RTCVideo(app_id='', event_handler=None, parameters='')
        self.rtcRooms = {}

    def evalCode(self, code: str) -> Any:
        return eval(code)

    def execCode(self, code: str) -> Any:
        return exec(code)

    def createUI(self) -> None:
        self.setWindowTitle(DemoTile)
        self.setWindowIcon(QIcon(IcoPath))
        self.resize(dpiSize(1280), dpiSize(600))
        self.intValidator = QIntValidator()

        mainWg = QWidget()
        self.setCentralWidget(mainWg)
        self.mainLayout = QHBoxLayout()
        mainWg.setLayout(self.mainLayout)

        leftWg = QWidget()
        vLayout = QVBoxLayout()
        vLayout.setSpacing(4)
        vLayout.setContentsMargins(0, 0, 0, 0)
        leftWg.setLayout(vLayout)
        self.mainLayout.addWidget(leftWg)

        # --------
        # left panel

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        scenarioLabel = QLabel("Scenario:")
        hLayout.addWidget(scenarioLabel)
        self.scenerioCombox = QComboBox()
        self.scenerioCombox.setMinimumHeight(ComboxItemHeight)
        self.scenerioCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.scenerioCombox.setView(QListView())
        self.scenerioCombox.currentIndexChanged.connect(self.onComboxScenarioSelectionChanged)
        for scenerioInfo in self.configJson["scenerios"]:
            self.scenerioCombox.addItem(scenerioInfo["name"])
        hLayout.addWidget(self.scenerioCombox)
        runScenerioButton = QPushButton('run')
        runScenerioButton.setMinimumHeight(ButtonHeight)
        runScenerioButton.clicked.connect(self.onClickRunScenerioButton)
        hLayout.addWidget(runScenerioButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        appNameLabel = QLabel('AppName:')
        hLayout.addWidget(appNameLabel)
        self.appNameCombox = QComboBox()
        self.appNameCombox.setMinimumWidth(dpiSize(150))
        self.appNameCombox.setMinimumHeight(ComboxItemHeight)
        self.appNameCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.appNameCombox.setView(QListView())
        self.appNameCombox.setEditable(True)
        self.appNameCombox.currentIndexChanged.connect(self.onComboxAppNameSelectionChanged)
        hLayout.addWidget(self.appNameCombox)  # , stretch=1
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        roomIdLabel = QLabel('RoomId:')
        hLayout.addWidget(roomIdLabel)
        self.roomIdEdit = QLineEdit(self.configJson['roomId'])
        self.roomIdEdit.setMaximumWidth(dpiSize(100))
        self.roomIdEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.roomIdEdit)
        userIdLabel = QLabel('UserId')
        hLayout.addWidget(userIdLabel)
        self.userIdEdit = QLineEdit(self.configJson['userId'])
        self.userIdEdit.setMaximumWidth(dpiSize(100))
        self.userIdEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.userIdEdit)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        createRtcVideoBtn = QPushButton('createRTCVideo')
        createRtcVideoBtn.setMinimumHeight(dpiSize(ButtonHeight))
        createRtcVideoBtn.clicked.connect(self.onClickCreateRtcVideoBtn)
        hLayout.addWidget(createRtcVideoBtn)
        destroyRtcVideoBtn = QPushButton('destroyRTCVideo')
        destroyRtcVideoBtn.setMinimumHeight(dpiSize(ButtonHeight))
        destroyRtcVideoBtn.clicked.connect(self.onClickDestroyRtcVideoBtn)
        hLayout.addWidget(destroyRtcVideoBtn)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        startAudioCaptureBtn = QPushButton('startAudioCapture')
        startAudioCaptureBtn.setMinimumHeight(dpiSize(ButtonHeight))
        startAudioCaptureBtn.clicked.connect(self.onClickStartAudioCaptureBtn)
        hLayout.addWidget(startAudioCaptureBtn)
        stopAudioCaptureBtn = QPushButton('stopAudioCapture')
        stopAudioCaptureBtn.setMinimumHeight(dpiSize(ButtonHeight))
        stopAudioCaptureBtn.clicked.connect(self.onClickStopAudioCaptureBtn)
        hLayout.addWidget(stopAudioCaptureBtn)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        widthLabel = QLabel('Width:')
        hLayout.addWidget(widthLabel)
        self.widthEdit = QLineEdit('640')
        self.widthEdit.setMaximumWidth(dpiSize(50))
        self.widthEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.widthEdit)
        heightLabel = QLabel('Width:')
        hLayout.addWidget(heightLabel)
        self.heightEdit = QLineEdit('360')
        self.heightEdit.setMaximumWidth(dpiSize(50))
        self.heightEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.heightEdit)
        fpsLabel = QLabel('FPS:')
        hLayout.addWidget(fpsLabel)
        self.fpsEdit = QLineEdit('15')
        self.fpsEdit.setMaximumWidth(dpiSize(50))
        self.fpsEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.fpsEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        setVideoEncoderConfigBtn = QPushButton('setVideoEncoderConfig')
        setVideoEncoderConfigBtn.setMinimumHeight(dpiSize(ButtonHeight))
        setVideoEncoderConfigBtn.clicked.connect(self.onClickSetVideoEncoderConfigBtn)
        hLayout.addWidget(setVideoEncoderConfigBtn)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        setLocalVideoCanvasBtn = QPushButton('setLocalVideoCanvas')
        setLocalVideoCanvasBtn.setMinimumHeight(dpiSize(ButtonHeight))
        setLocalVideoCanvasBtn.clicked.connect(self.onClickSetLocalVideoCanvasBtn)
        hLayout.addWidget(setLocalVideoCanvasBtn)
        self.localViewEdit = QLineEdit()
        self.localViewEdit.setMaximumWidth(dpiSize(80))
        self.localViewEdit.setMinimumHeight(dpiSize(ButtonHeight))
        hLayout.addWidget(self.localViewEdit)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        startVideoCaptureBtn = QPushButton('startVideoCapture')
        startVideoCaptureBtn.setMinimumHeight(dpiSize(ButtonHeight))
        startVideoCaptureBtn.clicked.connect(self.onClickStartVideoCaptureBtn)
        hLayout.addWidget(startVideoCaptureBtn)
        stopVideoCaptureBtn = QPushButton('stopVideoCapture')
        stopVideoCaptureBtn.setMinimumHeight(dpiSize(ButtonHeight))
        stopVideoCaptureBtn.clicked.connect(self.onClickStopVideoCaptureBtn)
        hLayout.addWidget(stopVideoCaptureBtn)

        # ----
        vLayout.addStretch(1)

        # --------
        # right layout
        vLayout = QVBoxLayout()
        self.mainLayout.addLayout(vLayout, stretch=1)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        layoutLabel = QLabel('Layout:')
        hLayout.addWidget(layoutLabel, stretch=0)
        self.layoutCombox = QComboBox()
        self.layoutCombox.addItems(['4', '9', '16', '25', '36', '49'])
        self.layoutCombox.setCurrentIndex(0)
        self.layoutCombox.currentIndexChanged.connect(self.onComboxLayoutSelectionChanged)
        hLayout.addWidget(self.layoutCombox, stretch=0)
        tipBtn = QPushButton('LastError')
        tipBtn.setToolTip('show last error')
        tipBtn.clicked.connect(self.onClickLastError)
        hLayout.addWidget(tipBtn)
        codeBtn = QPushButton('RunCode')
        codeBtn.setToolTip('run python code')
        codeBtn.clicked.connect(self.onClickRunCode)
        hLayout.addWidget(codeBtn)
        self.checkAutoSetRemoteStreamVideoCanvas = QCheckBox('AutoSetRemoteStreamVideoCanvas')
        self.checkAutoSetRemoteStreamVideoCanvas.setToolTip('Auto call setRemoteStreamVideoCanvas when a user joins')
        self.checkAutoSetRemoteStreamVideoCanvas.setChecked(True)
        hLayout.addWidget(self.checkAutoSetRemoteStreamVideoCanvas)
        hLayout.addStretch(1)

        self.gridWidget = QWidget()
        vLayout.addWidget(self.gridWidget, stretch=1)
        self.videoGridLayout = None
        self.onComboxLayoutSelectionChanged(self.layoutCombox.currentIndex())

        self.copyViewHandleAction = QAction('Copy View Handle', self)
        self.copyViewHandleAction.triggered.connect(self.onActionCopyViewHandle)

    def initUI(self) -> None:
        for app in self.configJson['appNameList']:
            self.appNameCombox.addItem(app['appName'])
        if self.configJson['appNameIndex'] >= 0 and self.configJson['appNameIndex'] < len(self.configJson['appNameList']):
            self.appNameCombox.setCurrentIndex(self.configJson['appNameIndex'])
        self.localViewEdit.setText(f'0x{int(self.videoLabels[0].winId()):X}')

    def onClickRunScenerioButton(self) -> None:
        scenerioInfo = self.configJson["scenerios"][self.scenerioCombox.currentIndex()]
        self.runScenerio(scenerioInfo)

    def runScenerio(self, scenerioInfo: dict) -> None:
        self.continueRunScenerio = True
        for funcText in scenerioInfo["code"]:
            # if funcText.startswith('util'):
                # print('debug')
            if funcText.startswith('#'):
                continue
            try:
                exec(funcText)
            except Exception as ex:
                sdk.log.error(f'{funcText}\n{ex}')
                exceptInfo = traceback.format_exc()
                sdk.log.error(exceptInfo)
                break
            if not self.continueRunScenerio:
                break

    def onComboxLayoutSelectionChanged(self, index: int) -> None:
        if index < 0:
            return
        if self.videoGridLayout:
            for n in range(self.viewCount):
                self.videoGridLayout.removeWidget(self.videoLabels[n])
                self.videoLabels[n].hide()
            tempWidget = QWidget()
            tempWidget.setLayout(self.videoGridLayout)
        self.videoGridLayout = QGridLayout()
        self.videoGridLayout.setContentsMargins(0, 0, 0, 0)
        self.videoGridLayout.setSpacing(2)
        self.gridWidget.setLayout(self.videoGridLayout)
        count = int(self.layoutCombox.currentText())
        side = int(math.sqrt(count))
        for row in range(side):
            for col in range(side):
                n = row * side + col
                if n < len(self.videoLabels):
                    view = self.videoLabels[n]
                else:
                    view = QLabel()
                    vtext = 'Remote'
                    if row == 0:
                        if col == 0:
                            vtext = 'Local'
                        # elif col == 1:
                            #vtext = 'Local Secondary'
                    view.setText(vtext)
                    view.winId()
                    view.setStyleSheet('QLabel{background:rgb(200,200,200)}')
                    view.mouseDoubleClickEvent = self.onVideoLabelDoubleClick
                    view.mousePressEvent = self.onVideoLabelMousePress
                    view.mouseMoveEvent = self.onVideoLabelMouseMove
                    view.mouseReleaseEvent = self.onVideoLabelMouseRelease
                    self.videoLabels.append(view)
                self.videoGridLayout.addWidget(view, row, col)
                view.show()
        self.viewCount = count

    def onVideoLabelDoubleClick(self, event: QMouseEvent) -> None:
        # sender = self.sender()  # is none
        pos = event.pos()
        gpos = event.globalPos()
        index = -1
        for videoLabel in self.videoLabels:
            index += 1
            gpos2 = videoLabel.mapToGlobal(pos)
            if gpos == gpos2:
                break
        # print('click', index, self.maximizedVideoLabelIndex)
        if self.maximizedVideoLabelIndex >= 0:
            self.onComboxLayoutSelectionChanged(self.layoutCombox.currentIndex())
            self.maximizedVideoLabelIndex = -1
        else:
            self.maximizedVideoLabelIndex = index
            if self.videoGridLayout:
                for n in range(self.viewCount):
                    self.videoGridLayout.removeWidget(self.videoLabels[n])
                    self.videoLabels[n].hide()
                tempWidget = QWidget()
                tempWidget.setLayout(self.videoGridLayout)
            self.videoGridLayout = QGridLayout()
            self.videoGridLayout.setContentsMargins(0, 0, 0, 0)
            self.videoGridLayout.setSpacing(2)
            self.gridWidget.setLayout(self.videoGridLayout)
            self.videoGridLayout.addWidget(self.videoLabels[index], 0, 0)
            self.videoLabels[index].show()

    def onVideoLabelRightMenu(self, index: int) -> None:
        menu = QMenu(self)
        self.copyViewHandleAction.setText(f'Copy view handle 0x{int(self.videoLabels[index].winId()):X}')
        menu.addAction(self.copyViewHandleAction)

        self.menuShowOnVideoLableIndex = index  # must before menu.exec_
        menu.exec_(QCursor.pos())

    def onVideoLabelMousePress(self, event: QMouseEvent) -> None:
        # sender = self.sender()  # is none
        pos = event.pos()
        gpos = event.globalPos()
        # print('onVideoLabelMousePress', pos, gpos)
        index = -1
        self.mousePressOnVideoLabelIndex = -1
        for videoLabel in self.videoLabels:
            index += 1
            gpos2 = videoLabel.mapToGlobal(pos)
            if gpos == gpos2:
                break
        if event.button() == Qt.RightButton:
            self.onVideoLabelRightMenu(index)
            return

    def onVideoLabelMouseMove(self, event: QMouseEvent) -> None:
        pos = event.pos()
        #gpos = event.globalPos()
        # print('onVideoLabelMouseMove', pos, gpos)
        if self.mousePressOnVideoLabelIndex < 0:
            return

    def onVideoLabelMouseRelease(self, event: QMouseEvent) -> None:
        pos = event.pos()
        gpos = event.globalPos()
        #print('onVideoLabelMouseRelease', pos, gpos)
        if event.button() == Qt.RightButton:
            return
        if self.mousePressOnVideoLabelIndex < 0:
            return

    def onActionCopyViewHandle(self) -> None:
        strViewHandle = self.copyViewHandleAction.text().split()[-1]
        QApplication.clipboard().setText(strViewHandle)

    def clearViews(self, index: List[int]) -> None:
        self.clearViewIndexs.extend(index)

    def onClearViewTimeout(self) -> None:
        if self.checkAutoRepaintVideoBackground.isChecked():
            for index in self.clearViewIndexs:
                vtext = 'Remote'
                if index == 0:
                    vtext = 'Local'
                # elif index == 1:
                    #vtext = 'LocalSecondary'
                self.videoLabels[index].setText(vtext)
                self.videoLabels[index].repaint()
        self.clearViewIndexs.clear()

    def getFreeView(self) -> Tuple[int, int]:
        freeView, freeViewIndex = 0, -1
        for i in range(1, self.viewCount):
            if i not in self.viewUsingIndex:
                freeView, freeViewIndex = int(self.videoLabels[i].winId()), i
                break
        return freeView, freeViewIndex

    def onClickLastError(self) -> None:
        self.tipDlg.showTip()

    def threadFuncDemo(self, signal: pyqtSignal, threadId: int, args: Any) -> None:
        count = args  # type: int
        for i in range(count):
            arg = time.time()
            print('thread[{}] sig {} send {} {}'.format(threadId, id(signal), i, arg))
            signal.emit((threadId, 0, i, arg))
            time.sleep(0.01)

    def threadNotifyDemo(self, threadId: int, msgId: int, args: list) -> None:
        print('reveive thread[{}] msg id {}, args: {}'.format(threadId, msgId, args))
        if msgId == astask.MsgIDThreadExit:
            print('thread', threadId, 'exit')

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Escape:
            event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        print('closeEvent')
        # self.onClickRelease()
        self.tipDlg.close()
        self.codeDlg.close()
        event.accept()

    def onSelectSdkCallback(self, sdkBinDir: str) -> None:
        self.selectSdkDlg.close()
        sdk.chooseSdkBinDir(sdkBinDir)

    def onComboxScenarioSelectionChanged(self, currentIndex: int) -> None:
        scenerioInfo = self.configJson["scenerios"][currentIndex]
        self.scenerioCombox.setToolTip('\n'.join(scenerioInfo["code"]))

    def onComboxAppNameSelectionChanged(self, currentIndex: int) -> None:
        pass

    def checkSDKResult(self, code: int) -> None:
        if code != 0 and self.rtcVideo:
            pass
            #errorDesc = self.rtcVideo.getErrorDescription(abs(code))
            #errorInfo = f'{agorasdk.agorasdk.LastAPICall}\n\nerror: {code}\nInfo: {errorDesc}'
            # sdk.log.info(errorInfo)
            #self.tipDlg.resize(200, 100)
            # self.tipDlg.showTip(errorInfo)

    def onClickRunCode(self) -> None:
        self.codeDlg.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.codeDlg.raise_()
        self.codeDlg.activateWindow()

    def onClickCreateRtcVideoBtn(self) -> None:
        if self.rtcVideo and self.rtcVideo.IRTCVideo:
            return
        appInfo = self.configJson['appNameList'][self.configJson['appNameIndex']]
        self.rtcVideo = sdk.RTCVideo(app_id=appInfo['appId'], event_handler=self, parameters='{"key": "value"}')

    def onClickDestroyRtcVideoBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.destroy()
        self.rtcVideo = None

    def onClickStartAudioCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.startAudioCapture()

    def onClickStopAudioCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.stopAudioCapture()

    def onClickSetVideoEncoderConfigBtn(self) -> None:
        if not self.rtcVideo:
            return
        solution = sdk.VideoSolution()
        solution.width = int(self.widthEdit.text())
        solution.height = int(self.heightEdit.text())
        solution.fps = int(self.fpsEdit.text())
        self.rtcVideo.setVideoEncoderConfig(index=sdk.StreamIndex.Main, solutions=[solution])

    def onClickSetLocalVideoCanvasBtn(self) -> None:
        if not self.rtcVideo:
            return
        viewText = self.localViewEdit.text().strip()
        if viewText.startswith('0x') or viewText.startswith('0X'):
            viewHandle = int(viewText, base=16)
        else:
            viewHandle = int(viewText, base=10)
        videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=sdk.RenderMode.Hidden, background_color=0x000000)
        self.rtcVideo.setLocalVideoCanvas(index=sdk.StreamIndex.Main, canvas=videoCanvas)

    def onClickStartVideoCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.startVideoCapture()

    def onClickStopVideoCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.stopVideoCapture()

    def onRTCVideoEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        sdk.log.info(f'{event_name} \n{pprint.pformat(event, indent=2, width=120, compact=True, sort_dicts=False)}')

    def onRTCRoomEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        sdk.log.info(f'{event_name} \n{pprint.pformat(event, indent=2, width=120, compact=True, sort_dicts=False)}')
        pass

    def testFunc(self) -> None:
        pass


# def IsUserAnAdmin() -> bool:
    # return bool(ctypes.windll.shell32.IsUserAnAdmin())


# def RunScriptAsAdmin(argv: List[str], workingDirectory: str = None, showFlag: int = 1) -> bool:
    #args = ' '.join('"{}"'.format(arg) for arg in argv)
    # return ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, workingDirectory, showFlag) > 32

def _adjustPos(win: MainWindow):
    if sys.platform == 'win32':
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            desktopRect = QDesktopWidget().availableGeometry()
            selfRect = win.frameGeometry()
            selfTopLeft = selfRect.topLeft()
            selfTopLeft.setY(selfTopLeft.y() // 2)
            win.move(selfTopLeft)
            selfRect.moveTopLeft(selfTopLeft)
            cmdX = selfRect.left() - 100
            if cmdX < 0:
                cmdX = 0
            cmdY = selfRect.top() + selfRect.height()
            cmdWidth = selfRect.width()
            cmdHeight = desktopRect.height() - cmdY
            if cmdHeight < 200:
                cmdY -= 200 - cmdHeight
                cmdHeight = 200
            ctypes.windll.user32.SetWindowPos(hwnd, 0, cmdX, cmdY, cmdWidth, cmdHeight, 4)


def _start():
    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(ctypes.c_wchar_p(
            f'{DemoTile} 不要在命令行界面上点击，否则会使UI线程卡住, ConsoleLog: bytesdklog'))
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    _adjustPos(win)
    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        _start()
    except Exception as ex:
        print(traceback.format_exc())
        input('\nSomething wrong. Please input Enter to exit.')
    sys.exit(0)
    # if sys.platform == 'win32':
        # if IsUserAnAdmin():
            # _start()
        # else:
            #print('not admin, now run as admin')
            # RunScriptAsAdmin(sys.argv)

