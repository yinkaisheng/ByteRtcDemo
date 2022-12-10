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
from typing import Any, Callable, Dict, List, Tuple
from PyQt5.QtCore import QItemSelection, QModelIndex, QPointF, QObject, QRect, QRegExp, QSortFilterProxyModel, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QColor, QCursor, QFont, QIcon, QImage, QIntValidator, QPainter, QPen, QPixmap
from PyQt5.QtGui import QContextMenuEvent, QKeyEvent, QMouseEvent, QStandardItem, QStandardItemModel, QTextCursor, QTextOption
from PyQt5.QtWidgets import QAbstractItemView, QAction, QApplication, QDesktopWidget, QDialog, QInputDialog, QMainWindow, QMenu, QMessageBox, QWidget
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QListView, QPushButton, QRadioButton, QSlider, QPlainTextEdit, QTextEdit, QToolTip, QTreeView
from PyQt5.QtWidgets import qApp, QGridLayout, QHBoxLayout, QLayout, QSplitter, QVBoxLayout, QSystemTrayIcon
from QCodeEditor import QCodeEditor
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
ButtonHeight = 28
ComboxHeight = ButtonHeight - 2
ComboxItemHeight = ComboxHeight - 2
EditHeight = ButtonHeight - 2
DemoTitle = 'ByteRtcDemo'
IcoPath = os.path.join(sdk.ExeDir, 'volcengine.ico')
RtcVideo = None
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
        for filePath, fileName, isDir, includeFiles in util.listDir((sdk.SdkDirFull, None, True, True)):
            if isDir and fileName.startswith(prefix):
                sdkVersionStr = fileName[len(prefix):]
                self.sdkDirs[sdkVersionStr] = fileName
                radio = QRadioButton(sdkVersionStr)
                radio.setMinimumHeight(dpiSize(ButtonHeight))
                vLayout.addWidget(radio)
                self.radioButtons.append(radio)
        if len(self.radioButtons) == 1:
            self.radioButtons[0].setChecked(True)

        useButton = QPushButton('Use')
        useButton.setMinimumHeight(dpiSize(ButtonHeight))
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

        sdkBinPath = os.path.join(sdk.SdkBinDirFull, sdk.SdkDllName)
        if not os.path.exists(sdkBinPath):
            print(f'---- {sdkBinPath} does not exist')
            # load dll in develop code path
            binDirs = util.getFileText(os.path.join(sdk.SdkBinDirFull, '.dllpath')).splitlines()
            binDirs.extend(util.getFileText(os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.dllpath')).splitlines())
            for binDir in binDirs:
                binPath = os.path.join(binDir, sdk.SdkDllName)
                if os.path.exists(binPath):
                    global DevelopDllDir
                    DevelopDllDir = binDir
                    sdk.log.info(f'---- {binPath} exists, use this dll')
                    os.environ["PATH"] = binDir + os.pathsep + os.environ["PATH"]
                    if sdk.isPy38OrHigher():
                        os.add_dll_directory(binDir)
                    break
                else:
                    print(f'---- develop dir: {binDir} does not exist')

    def closeEvent(self, event: QCloseEvent) -> None:
        #print('select dlg QCloseEvent')
        pass


class TipDlg(QDialog):
    def __init__(self, parent: QObject = None, tipSeconds=6):
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


class CodeDlg(QDialog):
    Signal = pyqtSignal(str)

    def __init__(self, parent: QObject = None):
        super(CodeDlg, self).__init__()
        self.mainWindow = parent
        self.threadId = threading.currentThread().ident
        self.setWindowFlags(Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(f"Python {sys.version.split()[0]} Code Executor")
        self.setWindowIcon(QIcon(IcoPath))
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(dpiSize(1200), dpiSize(600))
        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.apiCombox = QComboBox()
        self.apiCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.apiCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.apiCombox.setView(QListView())
        self.apiCombox.currentIndexChanged.connect(self.onComboxApiSelectionChanged)
        hLayout.addWidget(self.apiCombox)

        button = QPushButton('append')
        button.setMinimumHeight(dpiSize(ButtonHeight))
        button.clicked.connect(self.onClickAppend)
        hLayout.addWidget(button)

        button = QPushButton('replace')
        button.setMinimumHeight(dpiSize(ButtonHeight))
        button.clicked.connect(self.onClickReplace)
        hLayout.addWidget(button)

        button = QPushButton('e&xec')
        button.setMinimumHeight(dpiSize(ButtonHeight))
        button.clicked.connect(self.onClickRun)
        hLayout.addWidget(button)

        button = QPushButton('e&val')
        button.setMinimumHeight(dpiSize(ButtonHeight))
        button.clicked.connect(self.onClickRun)
        hLayout.addWidget(button)

        button = QPushButton('reload')
        button.setMinimumHeight(dpiSize(ButtonHeight))
        button.clicked.connect(self.onClickReload)
        hLayout.addWidget(button)

        self.saveButton = QPushButton('save')
        self.saveButton.setMinimumHeight(dpiSize(ButtonHeight))
        self.saveButton.clicked.connect(self.onClickSave)
        hLayout.addWidget(self.saveButton)

        button = QPushButton('clearCode')
        button.setMinimumHeight(dpiSize(ButtonHeight))
        button.clicked.connect(self.onClickClearCode)
        hLayout.addWidget(button)

        button = QPushButton('clearOutput')
        button.setMinimumHeight(dpiSize(ButtonHeight))
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

        self.loadApiCode()

    def onComboxApiSelectionChanged(self, index: int) -> None:
        pass

    def onClickSave(self) -> None:
        code = self.codeEdit.toPlainText().strip()
        if not code:
            return
        self.saveApiCode(self.apiCombox.currentText(), code)

    def onClickReload(self) -> None:
        self.loadApiCode()

    def onClickAppend(self) -> None:
        index = self.apiCombox.currentIndex()
        if index < 0:
            return
        name = self.apiCombox.currentText()
        code = self.apiExDict.get(name, None)
        if not code:
            code = self.apiDict.get(name, '')
        remoteUserId = self.mainWindow.subscribeStreamUserCombox.currentText()
        if remoteUserId:
            code = code.replace('RemoteUserIdToBeReplaced', remoteUserId)
        self.codeEdit.appendPlainText(code)

    def onClickReplace(self) -> None:
        self.onClickClearCode()
        self.onClickAppend()

    def onClickRun(self) -> None:
        button = self.sender()
        if not (button and isinstance(button, QPushButton)):
            return
        self.scrollToEnd()
        text = self.codeEdit.toPlainText()
        #print(type(text), text)
        if button.text() == 'e&val':
            ret = self.mainWindow.evalCode(text)
            output = f'eval(...)={ret}\n'
            self.outputEdit.appendPlainText(output)
            sdk.log.info(output)
        else:  # exec
            self.mainWindow.execCode(text)
            sdk.log.info(f'exec(...) done\n')
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

    def loadApiToDict(self, codePath: str) -> dict:
        self.boundary = '\n----boundary----'
        text = util.getFileText(codePath)
        index = 0
        apiDict = {}
        while True:
            name, found = util.getStrBetween(text, left='name=', right='\n', start=index)
            if found < 0:
                break
            index += len(name) + 1
            code, found = util.getStrBetween(text, left='code=', right=self.boundary, start=index)
            if found < 0:
                break
            index += len(code) + len(self.boundary)
            code = code.strip()
            apiDict[name] = code
        return apiDict

    def loadApiCode(self) -> None:
        curIndex = self.apiCombox.currentIndex()
        apiPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.code')
        self.apiDict = self.loadApiToDict(apiPath)
        self.apiExDict = self.loadApiToDict(f'{apiPath}Ex')
        self.apiDict.update(self.apiExDict)
        self.apiCombox.clear()
        names = set(self.apiDict.keys())
        names.update(self.apiExDict.keys())
        names = list(names)
        names.sort()
        self.apiCombox.addItems(names)
        if self.apiCombox.count() > curIndex:
            self.apiCombox.setCurrentIndex(curIndex)

    def saveApiCode(self, name: str, code: str) -> None:
        if name in self.apiExDict:
            apiDict = self.apiExDict
            apiPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.codeEx')
        else:
            apiDict = self.apiDict
            apiPath = os.path.join(sdk.ExeDir, sdk.ExeNameNoExt + '.code')
        apiDict[name] = code
        text = '\n'.join(f'name={name}\ncode=\n\n{content}\n{self.boundary}\n' for name, content in apiDict.items())
        util.writeTextFile(apiPath, text)

    def close(self) -> bool:
        sdk.GuiStreamObj.setLogHandler(None)
        return super(CodeDlg, self).close()

    def logCallbackHandler(self, output: str) -> None:
        if threading.currentThread().ident == self.threadId:
            self.outputEdit.appendPlainText(output)
        else:
            self.Signal.emit(output)


ColumnEventType, ColumnEventName, ColumnEventTime, ColumnEventContent = range(4)


class SortFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, sourceRow, sourceParent):
        # Do we filter for the date column?
        if self.filterKeyColumn() == ColumnEventName:
            index = self.sourceModel().index(sourceRow, ColumnEventName, sourceParent)
            text = self.sourceModel().data(index)
            return self.filterRegExp().indexIn(text) >= 0
        return super(SortFilterProxyModel, self).filterAcceptsRow(sourceRow, sourceParent)


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
        self.videoLabels = []
        self.viewUsingIndex = set()
        self.viewCount = 0
        self.uid2ViewIndex = {}  # does not have key 0, local uid is the real uid when join successfully
        self.clearViewIndexs = []
        self.maximizedVideoLabelIndex = -1
        self.menuShowOnVideoLableIndex = -1
        self.mousePressOnVideoLabelIndex = -1
        self.remoteViewStartIndex = 1
        self.captureSourceList = []
        self.createUI()
        self.initUI()
        self.selectSdkDlg = SelectSdkDlg(self, selectCallback=self.onSelectSdkCallback)
        self.tipDlg = TipDlg(None)
        self.codeDlg = CodeDlg(self)
        self.selectSdkDlg.exec()
        self.videoEncoderConfig = sdk.VideoEncoderConfig(width=640, height=360, frameRate=15)
        self.pushTaskId = 0
        self.pushUserId = ''
        # after exec, console window is active, set MainWindow active in timer
        if sys.stdout:
            self.delayCall(timeMs=100, func=self.activateWindow)

        self.rtcVideo = None  # sdk.RTCVideo(app_id='', event_handler=None, parameters='')
        self.vdm = None
        self.videoEffect = None
        #self.rtcRoom = None
        self.rtcRooms = {}
        self.rtcRoomEventHandlers = {}
        self.rtcRoomUsers = {}
        self.currentEventRoomId = ''  # only use in room event handler
        self.RTCVideoEventSignal.connect(self.onRTCVideoEvent)
        self.RTCRoomEventSignal.connect(self.onRTCRoomEvent)
        self.RTCVideoEventHandler = {}
        self.RTCRoomEventHandler = {}
        self.initializeEventHandlers()
        code = util.getFileText(self.configJson['startupScriptFile'])
        if code:
            self.execCode(code)

    def evalCode(self, code: str) -> Any:
        try:
            ret = eval(code)
            return ret
        except Exception as ex:
            self.appendOutputEditText(f'\n{ex}\n{traceback.format_exc()}\n')

    def execCode(self, code: str) -> Any:
        try:
            ret = exec(code)
            return ret
        except Exception as ex:
            self.appendOutputEditText(f'\n{ex}\n{traceback.format_exc()}\n')

    def createUI(self) -> None:
        self.setWindowTitle(DemoTitle)
        self.setWindowIcon(QIcon(IcoPath))
        self.resize(dpiSize(1400), dpiSize(800))
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
        self.scenerioCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.scenerioCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.scenerioCombox.setView(QListView())
        self.scenerioCombox.currentIndexChanged.connect(self.onComboxScenarioSelectionChanged)
        for scenerioInfo in self.configJson["scenerios"]:
            self.scenerioCombox.addItem(scenerioInfo["name"])
        if self.configJson["sceneriosIndex"] < self.scenerioCombox.count():
            self.scenerioCombox.setCurrentIndex(self.configJson["sceneriosIndex"])
        hLayout.addWidget(self.scenerioCombox)
        runScenerioButton = QPushButton('run')
        runScenerioButton.setMinimumHeight(dpiSize(ButtonHeight))
        runScenerioButton.clicked.connect(self.onClickRunScenerioButton)
        hLayout.addWidget(runScenerioButton)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        appNameLabel = QLabel('AppName:')
        hLayout.addWidget(appNameLabel)
        self.appNameCombox = QComboBox()
        # self.appNameCombox.setMinimumWidth(dpiSize(120))
        self.appNameCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.appNameCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.appNameCombox.setView(QListView())
        self.appNameCombox.setEditable(True)
        self.appNameCombox.currentIndexChanged.connect(self.onComboxAppNameSelectionChanged)
        hLayout.addWidget(self.appNameCombox)  # , stretch=1
        self.cloudProxyCheck = QCheckBox('CloudProxy')
        self.cloudProxyCheck.setMinimumHeight(dpiSize(ButtonHeight))
        self.cloudProxyCheck.setChecked(self.configJson['cloudProxyChecked'])
        self.cloudProxyCheck.clicked.connect(self.onClickCloudProxyCheck)
        hLayout.addWidget(self.cloudProxyCheck)
        self.cloudProxyEdit = QLineEdit(self.configJson['cloudProxy'])
        self.cloudProxyEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.cloudProxyEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        roomIdLabel = QLabel('RoomId:')
        hLayout.addWidget(roomIdLabel)
        self.roomIdCombox = QComboBox()
        self.roomIdCombox.setEditable(True)
        self.roomIdCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.roomIdCombox.setMinimumWidth(dpiSize(120))
        self.roomIdCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.roomIdCombox.setView(QListView())
        self.roomIdCombox.setCurrentText(self.configJson['roomId'])
        self.roomIdCombox.currentIndexChanged.connect(self.onComboxRoomIdSelectionChanged)
        hLayout.addWidget(self.roomIdCombox)
        userIdLabel = QLabel('UserId')
        hLayout.addWidget(userIdLabel)
        self.userIdEdit = QLineEdit(eval(self.configJson['userId']))
        self.userIdEdit.setMaximumWidth(dpiSize(100))
        self.userIdEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.userIdEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        tokenLabel = QLabel('Token:')
        hLayout.addWidget(tokenLabel)
        self.tokenEdit = QLineEdit()
        # self.tokenEdit.setMaximumWidth(dpiSize(120))
        self.tokenEdit.setMinimumHeight(dpiSize(EditHeight))
        hLayout.addWidget(self.tokenEdit)
        self.externalVideoSourceCheck = QCheckBox('ExternalVideoSource')
        self.externalVideoSourceCheck.setMaximumHeight(dpiSize(ButtonHeight))
        self.externalVideoSourceCheck.clicked.connect(self.onClickExternalVideoSourceCheck)
        hLayout.addWidget(self.externalVideoSourceCheck)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        setEnvBtn = QPushButton('setEnv')
        setEnvBtn.setMinimumHeight(dpiSize(ButtonHeight))
        setEnvBtn.clicked.connect(self.onClickSetEnvBtn)
        hLayout.addWidget(setEnvBtn)
        self.envCombox = QComboBox()
        self.envCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.envCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.envCombox.setView(QListView())
        self.envCombox.addItems(f'{it.name} {it.value}' for it in sdk.Env)
        self.envCombox.setCurrentIndex(self.configJson['env'])
        hLayout.addWidget(self.envCombox)
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
        self.resolutionCombox = QComboBox()
        self.resolutionCombox.setMinimumWidth(dpiSize(130))
        self.resolutionCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.resolutionCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.resolutionCombox.setView(QListView())
        self.resolutionCombox.addItems(self.configJson["resolutionList"])
        defaultIndex = 3   # 720P 15FPS
        if self.configJson['defaultResolutionComboxIndex'] < self.resolutionCombox.count():
            defaultIndex = self.configJson['defaultResolutionComboxIndex']
        self.resolutionCombox.setCurrentIndex(defaultIndex)
        self.resolutionCombox.currentIndexChanged.connect(self.onComboxResolutionSelectionChanged)
        hLayout.addWidget(self.resolutionCombox)
        self.capturePreferenceCombox = QComboBox()
        self.capturePreferenceCombox.setToolTip('VideoCaptureConfig::CapturePreference')
        self.capturePreferenceCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.capturePreferenceCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.capturePreferenceCombox.setView(QListView())
        self.capturePreferenceCombox.addItems(f'{it.name} {it.value}' for it in sdk.CapturePreference)
        hLayout.addWidget(self.capturePreferenceCombox)
        vdmBtn = QPushButton('VDM')
        vdmBtn.setMaximumWidth(dpiSize(50))
        vdmBtn.setMinimumHeight(dpiSize(ButtonHeight))
        vdmBtn.clicked.connect(self.onClickVDMBtn)
        vdmBtn.setToolTip('VideoDeviceManager enumerateVideoCaptureDevices')
        hLayout.addWidget(vdmBtn)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        widthLabel = QLabel('Width:')
        hLayout.addWidget(widthLabel)
        self.widthEdit = QLineEdit('640')
        self.widthEdit.setMaximumWidth(dpiSize(40))
        self.widthEdit.setMinimumHeight(dpiSize(EditHeight))
        self.widthEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.widthEdit)
        heightLabel = QLabel('Width:')
        hLayout.addWidget(heightLabel)
        self.heightEdit = QLineEdit('360')
        self.heightEdit.setMaximumWidth(dpiSize(40))
        self.heightEdit.setMinimumHeight(dpiSize(EditHeight))
        self.heightEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.heightEdit)
        fpsLabel = QLabel('FPS:')
        hLayout.addWidget(fpsLabel)
        self.fpsEdit = QLineEdit('15')
        self.fpsEdit.setMaximumWidth(dpiSize(30))
        self.fpsEdit.setMinimumHeight(dpiSize(EditHeight))
        self.fpsEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.fpsEdit)
        bitrateLabel = QLabel('Bitrate:')
        hLayout.addWidget(bitrateLabel)
        self.bitrateEdit = QLineEdit('-1')
        self.bitrateEdit.setMaximumWidth(dpiSize(40))
        self.bitrateEdit.setMinimumHeight(dpiSize(EditHeight))
        self.bitrateEdit.setValidator(self.intValidator)
        hLayout.addWidget(self.bitrateEdit)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        setVideoCaptureConfigBtn = QPushButton('setVideoCaptureConfig')
        setVideoCaptureConfigBtn.setMinimumHeight(dpiSize(ButtonHeight))
        setVideoCaptureConfigBtn.clicked.connect(self.onClickSetVideoCaptureConfigBtn)
        hLayout.addWidget(setVideoCaptureConfigBtn)
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
        self.localStreamIndexCombox = QComboBox()
        self.localStreamIndexCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.localStreamIndexCombox.setToolTip('StreamIndex')
        self.localStreamIndexCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.localStreamIndexCombox.setView(QListView())
        self.localStreamIndexCombox.addItems(f'{it.name} {it.value}' for it in sdk.StreamIndex)
        self.localStreamIndexCombox.setCurrentIndex(0)
        hLayout.addWidget(self.localStreamIndexCombox)
        self.localViewEdit = QLineEdit()
        self.localViewEdit.setMaximumWidth(dpiSize(120))
        self.localViewEdit.setMinimumHeight(dpiSize(ButtonHeight))
        self.localViewEdit.setToolTip('Local View Handle')
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
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        getScreenCaptureSourceListBtn = QPushButton('getScreenCaptureSourceList')
        getScreenCaptureSourceListBtn.setMinimumHeight(dpiSize(ButtonHeight))
        getScreenCaptureSourceListBtn.clicked.connect(self.onClickGetScreenCaptureSourceListBtn)
        hLayout.addWidget(getScreenCaptureSourceListBtn)
        self.captureSourceListCombox = QComboBox()
        self.captureSourceListCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.captureSourceListCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.captureSourceListCombox.setView(QListView())
        hLayout.addWidget(self.captureSourceListCombox, stretch=1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        startScreenVideoCaptureBtn = QPushButton('startScreenVideoCapture')
        startScreenVideoCaptureBtn.setMinimumHeight(dpiSize(ButtonHeight))
        startScreenVideoCaptureBtn.clicked.connect(self.onClickStartScreenVideoCaptureBtn)
        hLayout.addWidget(startScreenVideoCaptureBtn)
        stopScreenVideoCaptureBtn = QPushButton('stopScreenVideoCapture')
        stopScreenVideoCaptureBtn.setMinimumHeight(dpiSize(ButtonHeight))
        stopScreenVideoCaptureBtn.clicked.connect(self.onClickStopScreenVideoCaptureBtn)
        hLayout.addWidget(stopScreenVideoCaptureBtn)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        createRTCRoomBtn = QPushButton('createRTCRoom')
        createRTCRoomBtn.setMinimumHeight(dpiSize(ButtonHeight))
        createRTCRoomBtn.clicked.connect(self.onClickCreateRTCRoomBtn)
        hLayout.addWidget(createRTCRoomBtn, stretch=1)
        joinRoomBtn = QPushButton('joinRoom')
        joinRoomBtn.setMinimumHeight(dpiSize(ButtonHeight))
        joinRoomBtn.clicked.connect(self.onClickJoinRoomBtn)
        hLayout.addWidget(joinRoomBtn, stretch=1)
        self.autoPublishCheck = QCheckBox('1')
        self.autoPublishCheck.setMinimumHeight(dpiSize(ButtonHeight))
        self.autoPublishCheck.setToolTip('is_auto_publish')
        self.autoPublishCheck.setChecked(True)
        hLayout.addWidget(self.autoPublishCheck)
        self.autoSubscribeAudioCheck = QCheckBox('1')
        self.autoSubscribeAudioCheck.setMinimumHeight(dpiSize(ButtonHeight))
        self.autoSubscribeAudioCheck.setToolTip('is_auto_subscribe_audio')
        self.autoSubscribeAudioCheck.setChecked(True)
        hLayout.addWidget(self.autoSubscribeAudioCheck)
        self.autoSubscribeVideoCheck = QCheckBox('1')
        self.autoSubscribeVideoCheck.setMinimumHeight(dpiSize(ButtonHeight))
        self.autoSubscribeVideoCheck.setToolTip('is_auto_subscribe_video')
        self.autoSubscribeVideoCheck.setChecked(True)
        hLayout.addWidget(self.autoSubscribeVideoCheck)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        leaveRoomBtn = QPushButton('leaveRoom')
        leaveRoomBtn.setMinimumHeight(dpiSize(ButtonHeight))
        leaveRoomBtn.clicked.connect(self.onClickLeaveRoomBtn)
        hLayout.addWidget(leaveRoomBtn)
        destroyRoomBtn = QPushButton('destroyRoom')
        destroyRoomBtn.setMinimumHeight(dpiSize(ButtonHeight))
        destroyRoomBtn.clicked.connect(self.onClickDestroyRoomBtn)
        hLayout.addWidget(destroyRoomBtn)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        publishStreamBtn = QPushButton('publishStream')
        publishStreamBtn.setMinimumHeight(dpiSize(ButtonHeight))
        publishStreamBtn.clicked.connect(self.onClickPublishStreamBtnBtn)
        hLayout.addWidget(publishStreamBtn)
        unpublishStreamBtn = QPushButton('unpublishStream')
        unpublishStreamBtn.setMinimumHeight(dpiSize(ButtonHeight))
        unpublishStreamBtn.clicked.connect(self.onClickUnpublishStreamBtnBtn)
        hLayout.addWidget(unpublishStreamBtn)
        self.streamMediaStreamTypeCombox = QComboBox()
        self.streamMediaStreamTypeCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.streamMediaStreamTypeCombox.setToolTip("MediaStreamType")
        self.streamMediaStreamTypeCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.streamMediaStreamTypeCombox.setView(QListView())
        self.streamMediaStreamTypeCombox.addItems(f'{it.name} {it.value}' for it in sdk.MediaStreamType)
        self.streamMediaStreamTypeCombox.setCurrentIndex(2)
        hLayout.addWidget(self.streamMediaStreamTypeCombox)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        publishScreenBtn = QPushButton('publishScreen')
        publishScreenBtn.setMinimumHeight(dpiSize(ButtonHeight))
        publishScreenBtn.clicked.connect(self.onClickPublishScreenBtnBtn)
        hLayout.addWidget(publishScreenBtn)
        unpublishScreenBtn = QPushButton('unpublishScreen')
        unpublishScreenBtn.setMinimumHeight(dpiSize(ButtonHeight))
        unpublishScreenBtn.clicked.connect(self.onClickUnpublishScreenBtnBtn)
        hLayout.addWidget(unpublishScreenBtn)
        self.screenMediaStreamTypeCombox = QComboBox()
        self.screenMediaStreamTypeCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.screenMediaStreamTypeCombox.setToolTip("MediaStreamType")
        self.screenMediaStreamTypeCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.screenMediaStreamTypeCombox.setView(QListView())
        self.screenMediaStreamTypeCombox.addItems(f'{it.name} {it.value}' for it in sdk.MediaStreamType)
        self.screenMediaStreamTypeCombox.setCurrentIndex(2)
        hLayout.addWidget(self.screenMediaStreamTypeCombox)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        subscribeStreamBtn = QPushButton('subscribeStream')
        subscribeStreamBtn.setMinimumHeight(dpiSize(ButtonHeight))
        subscribeStreamBtn.clicked.connect(self.onClickSubscribeStreamBtn)
        hLayout.addWidget(subscribeStreamBtn)
        unsubscribeStreamBtn = QPushButton('unsubscribeStream')
        unsubscribeStreamBtn.setMinimumHeight(dpiSize(ButtonHeight))
        unsubscribeStreamBtn.clicked.connect(self.onClickUnsubscribeStreamBtn)
        hLayout.addWidget(unsubscribeStreamBtn)
        self.subscribeStreamUserCombox = QComboBox()
        self.subscribeStreamUserCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.subscribeStreamUserCombox.setToolTip("Remote Users")
        self.subscribeStreamUserCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.subscribeStreamUserCombox.setView(QListView())
        self.subscribeStreamUserCombox.setEditable(True)
        hLayout.addWidget(self.subscribeStreamUserCombox)
        self.subscribeStreamMediaStreamTypeCombox = QComboBox()
        self.subscribeStreamMediaStreamTypeCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.subscribeStreamMediaStreamTypeCombox.setToolTip("MediaStreamType")
        self.subscribeStreamMediaStreamTypeCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.subscribeStreamMediaStreamTypeCombox.setView(QListView())
        self.subscribeStreamMediaStreamTypeCombox.addItems(f'{it.name} {it.value}' for it in sdk.MediaStreamType)
        self.subscribeStreamMediaStreamTypeCombox.setCurrentIndex(2)
        hLayout.addWidget(self.subscribeStreamMediaStreamTypeCombox)
        # hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        subscribeScreenBtn = QPushButton('subscribeScreen')
        subscribeScreenBtn.setMinimumHeight(dpiSize(ButtonHeight))
        subscribeScreenBtn.clicked.connect(self.onClickSubscribeScreenBtn)
        hLayout.addWidget(subscribeScreenBtn)
        unsubscribeScreenBtn = QPushButton('unsubscribeScreen')
        unsubscribeScreenBtn.setMinimumHeight(dpiSize(ButtonHeight))
        unsubscribeScreenBtn.clicked.connect(self.onClickUnsubscribeScreenBtn)
        hLayout.addWidget(unsubscribeScreenBtn)
        self.subscribeScreenUserCombox = QComboBox()
        self.subscribeScreenUserCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.subscribeScreenUserCombox.setToolTip("Remote Users")
        self.subscribeScreenUserCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.subscribeScreenUserCombox.setView(QListView())
        self.subscribeScreenUserCombox.setEditable(True)
        hLayout.addWidget(self.subscribeScreenUserCombox)
        self.subscribeScreenMediaStreamTypeCombox = QComboBox()
        self.subscribeScreenMediaStreamTypeCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.subscribeScreenMediaStreamTypeCombox.setToolTip("MediaStreamType")
        self.subscribeScreenMediaStreamTypeCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.subscribeScreenMediaStreamTypeCombox.setView(QListView())
        self.subscribeScreenMediaStreamTypeCombox.addItems(f'{it.name} {it.value}' for it in sdk.MediaStreamType)
        self.subscribeScreenMediaStreamTypeCombox.setCurrentIndex(2)
        hLayout.addWidget(self.subscribeScreenMediaStreamTypeCombox)
        # hLayout.addStretch(1)

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
        self.layoutCombox.setMinimumHeight(dpiSize(ComboxHeight))
        self.layoutCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        self.layoutCombox.setView(QListView())
        self.layoutCombox.addItems(['4', '9', '16', '25', '36', '49'])
        self.layoutCombox.setCurrentIndex(0)
        self.layoutCombox.currentIndexChanged.connect(self.onComboxLayoutSelectionChanged)
        hLayout.addWidget(self.layoutCombox, stretch=0)
        tipBtn = QPushButton('LastError')
        tipBtn.setMinimumHeight(dpiSize(ButtonHeight))
        tipBtn.setToolTip('show last error')
        tipBtn.clicked.connect(self.onClickLastError)
        hLayout.addWidget(tipBtn)
        codeBtn = QPushButton('RunCode')
        codeBtn.setMinimumHeight(dpiSize(ButtonHeight))
        codeBtn.setToolTip('run python code')
        codeBtn.clicked.connect(self.onClickRunCode)
        hLayout.addWidget(codeBtn)
        self.checkAutoSetRemoteStreamVideoCanvas = QCheckBox('AutoSetRemoteStreamVideoCanvas')
        self.checkAutoSetRemoteStreamVideoCanvas.setMinimumHeight(dpiSize(ButtonHeight))
        self.checkAutoSetRemoteStreamVideoCanvas.setToolTip('Auto call setRemoteStreamVideoCanvas when a user joins')
        self.checkAutoSetRemoteStreamVideoCanvas.setChecked(True)
        hLayout.addWidget(self.checkAutoSetRemoteStreamVideoCanvas)
        hLayout.addStretch(1)

        vSplitter = QSplitter(Qt.Vertical)
        #vSplitter.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vSplitter, stretch=1)

        self.gridWidget = QWidget()
        vSplitter.addWidget(self.gridWidget)
        self.videoGridLayout = None
        self.onComboxLayoutSelectionChanged(self.layoutCombox.currentIndex())

        self.copyViewHandleAction = QAction('Copy View Handle', self)
        self.copyViewHandleAction.triggered.connect(self.onActionCopyViewHandle)

        # ----
        eventWidget = QWidget()
        vSplitter.addWidget(eventWidget)
        vSplitter.setSizes([250, 100])
        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        eventWidget.setLayout(vLayout)

        # ----
        #hLayout = QHBoxLayout()
        # vLayout.addLayout(hLayout)

        #eventTypeLabel = QLabel('EventFilter Type:')
        # hLayout.addWidget(eventTypeLabel)
        #self.eventTypeCombox = QComboBox()
        # self.eventTypeCombox.setMinimumHeight(dpiSize(ComboxHeight))
        #self.eventTypeCombox.setStyleSheet('QAbstractItemView::item {height: %dpx;}' % dpiSize(ComboxItemHeight))
        # self.eventTypeCombox.setView(QListView())
        #self.eventTypeCombox.addItems(['All', 'RTCVideoEvent', 'RTCRoomEvent'])
        # self.eventTypeCombox.setCurrentIndex(0)
        # self.eventTypeCombox.currentIndexChanged.connect(self.onComboxEventTypeSelectionChanged)
        # hLayout.addWidget(self.eventTypeCombox)
        eventNameLabel = QLabel('EventNameFilter:')
        hLayout.addWidget(eventNameLabel)
        self.eventNameFilterEdit = QLineEdit('')
        self.eventNameFilterEdit.setMinimumHeight(dpiSize(EditHeight))
        self.eventNameFilterEdit.textChanged.connect(self.onEventNameFilterEditTextChanged)
        hLayout.addWidget(self.eventNameFilterEdit)
        self.eventTipCheck = QCheckBox('EventTip')
        self.eventTipCheck.setMinimumHeight(dpiSize(ButtonHeight))
        self.eventTipCheck.setChecked(False)
        hLayout.addWidget(self.eventTipCheck)
        self.eventScrollEndCheck = QCheckBox('AutoScrollToEnd')
        self.eventScrollEndCheck.setMinimumHeight(dpiSize(ButtonHeight))
        self.eventScrollEndCheck.setChecked(True)
        hLayout.addWidget(self.eventScrollEndCheck)
        hLayout.addStretch(1)

        # ----
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        self.itemModel = QStandardItemModel(0, 4)
        self.itemModel.setHeaderData(ColumnEventType, Qt.Horizontal, "Type")
        self.itemModel.setHeaderData(ColumnEventName, Qt.Horizontal, "Name")
        self.itemModel.setHeaderData(ColumnEventTime, Qt.Horizontal, "Time")
        self.itemModel.setHeaderData(ColumnEventContent, Qt.Horizontal, "Content")

        self.proxyModel = SortFilterProxyModel()
        self.proxyModel.setSourceModel(self.itemModel)
        self.proxyModel.setFilterKeyColumn(ColumnEventName)
        self.eventView = QTreeView()
        self.eventView.setModel(self.proxyModel)
        self.eventView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.eventView.setRootIsDecorated(False)
        self.eventView.setAlternatingRowColors(True)
        # self.eventView.setSortingEnabled(True)
        self.eventView.setColumnWidth(0, dpiSize(70))
        self.eventView.setColumnWidth(1, dpiSize(204))
        self.eventView.setColumnWidth(2, dpiSize(180))
        self.eventView.setMouseTracking(True)
        self.eventView.entered.connect(self.onMouseEnterEventView)
        self.eventView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.eventView.customContextMenuRequested.connect(self.onEventViewContextMenu)
        self.eventView.selectionModel().selectionChanged.connect(self.onEventViewSelectionChanged)
        self.prevShowEventName = ''
        hLayout.addWidget(self.eventView)
        self.eventEdit = QPlainTextEdit()
        self.eventEdit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.eventEdit.setStyleSheet('QPlainTextEdit{font-size:%dpx;font-family:Consolas;background-color:rgb(250,250,250);}' % dpiSize(14))
        hLayout.addWidget(self.eventEdit)

        self.prevToolTipIndex = None

    def appendOutputEditText(self, text: str) -> None:
        self.codeDlg.outputEdit.appendPlainText(text)

    def onMouseEnterEventView(self, index: QModelIndex) -> None:
        if not self.eventTipCheck.isChecked():
            return
        if not self.isActiveWindow():
            return
        if not index.isValid():
            return
        index = index.siblingAtColumn(ColumnEventType)
        roomId = index.data(Qt.ItemDataRole.UserRole)
        index = index.siblingAtColumn(ColumnEventContent)
        if index == self.prevToolTipIndex:
            return
        self.prevToolTipIndex = index
        event = index.data(Qt.ItemDataRole.UserRole)
        QToolTip.hideText()
        if roomId:  # RTCRoom
            QToolTip.showText(QCursor.pos(), f'room_id: {roomId}\n{util.prettyDict(event)}')
        else:  # RTCVideo
            QToolTip.showText(QCursor.pos(), util.prettyDict(event))
        #QToolTip.showText(QCursor.pos(), util.prettyDict(event), self.eventView, QRect(), 300000)

    def onEventViewContextMenu(self, pos) -> None:
        menu = QMenu(self)
        action = menu.addAction('Clear')
        action.triggered.connect(self.onActionClearEventView)
        menu.exec_(QCursor.pos())

    def onActionClearEventView(self) -> None:
        self.itemModel.removeRows(0, self.itemModel.rowCount())
        self.eventEdit.clear()

    def onEventViewSelectionChanged(self, selection: QItemSelection) -> None:
        #print(type(selection), selection)
        index = self.eventView.currentIndex()
        if index.isValid():
            index = index.siblingAtColumn(ColumnEventType)
            roomId = index.data(Qt.ItemDataRole.UserRole)
            index = self.eventView.currentIndex().siblingAtColumn(ColumnEventName)
            eventName = index.data(Qt.ItemDataRole.DisplayRole)
            index = self.eventView.currentIndex().siblingAtColumn(ColumnEventContent)
            event = index.data(Qt.ItemDataRole.UserRole)
            curPos = self.eventEdit.verticalScrollBar().value()
            if roomId:  # RTCRoom
                self.eventEdit.setPlainText(f'room_id: {roomId}\n{util.prettyDict(event)}')
            else:  # RTCVideo
                self.eventEdit.setPlainText(util.prettyDict(event))
            if self.prevShowEventName == eventName:
                self.eventEdit.verticalScrollBar().setValue(curPos)
            self.prevShowEventName = eventName
        else:
            self.eventEdit.clear()

    def onEventNameFilterEditTextChanged(self):
        syntax = QRegExp.PatternSyntax(QRegExp.RegExp)
        regExp = QRegExp(self.eventNameFilterEdit.text(), Qt.CaseInsensitive, syntax)
        self.proxyModel.setFilterRegExp(regExp)

    def initUI(self) -> None:
        for app in self.configJson['appNameList']:
            self.appNameCombox.addItem(app['appName'])
        if self.configJson['appNameIndex'] >= 0 and self.configJson['appNameIndex'] < len(self.configJson['appNameList']):
            self.appNameCombox.setCurrentIndex(self.configJson['appNameIndex'])
        self.localViewEdit.setText(f'0x{int(self.videoLabels[0].winId()):X}')
        self.onComboxResolutionSelectionChanged()

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
                self.codeDlg.outputEdit.appendPlainText(f'\nexec(...): {ex}\n{exceptInfo}\n')
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

    def onComboxEventTypeSelectionChanged(self, index: int) -> None:
        pass

    def onVideoLabelDoubleClick(self, event: QMouseEvent) -> None:
        # sender = self.sender()  #is none
        pos = event.pos()
        gpos = event.globalPos()
        index = -1
        for videoLabel in self.videoLabels:
            index += 1
            gpos2 = videoLabel.mapToGlobal(pos)
            if gpos == gpos2:
                break
        #print('click', index, self.maximizedVideoLabelIndex)
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
        # sender = self.sender()  #is none
        pos = event.pos()
        gpos = event.globalPos()
        #print('onVideoLabelMousePress', pos, gpos)
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
        #print('onVideoLabelMouseMove', pos, gpos)
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

    def resetViewsBackground(self, index: List[int]) -> None:
        self.clearViewIndexs.extend(index)
        # if sdk don't reset view background when video stops, repaint view
        self.delayCall(timeMs=100, func=self.onRepaintViewBackground)

    def onRepaintViewBackground(self) -> None:
        if 1:  # self.checkAutoRepaintVideoBackground.isChecked():
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
        for i in range(self.remoteViewStartIndex, self.viewCount):
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
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        print('closeEvent')
        self.onClickDestroyRtcVideoBtn()
        self.tipDlg.close()
        self.codeDlg.close()
        event.accept()

    def onSelectSdkCallback(self, sdkBinDir: str) -> None:
        self.selectSdkDlg.close()
        sdk.selectSdkBinDir(sdkBinDir)
        self.setWindowTitle(f'{DemoTitle}, {sdk.SdkVersion}')

    def onComboxScenarioSelectionChanged(self, currentIndex: int) -> None:
        scenerioInfo = self.configJson["scenerios"][currentIndex]
        self.scenerioCombox.setToolTip('\n'.join(scenerioInfo["code"]))

    def onComboxAppNameSelectionChanged(self, currentIndex: int) -> None:
        pass

    def checkSDKResult(self, code: int) -> None:
        if code != 0:
            errorDesc = sdk.getErrorDescription(code)
            errorInfo = f'{sdk.LastAPICall}\n\nerror: {code}\nInfo: {errorDesc}'
            sdk.log.info(f'error {code}, error desc: {errorDesc}')
            self.tipDlg.showTip(errorInfo)

    def onClickRunCode(self) -> None:
        self.codeDlg.show()
        # need raise_ and activateWindow if dialog is already shown, otherwise codeDlg won't active
        self.codeDlg.raise_()
        self.codeDlg.activateWindow()

    def onClickCloudProxyCheck(self) -> None:
        if not self.rtcVideo:
            return
        if self.cloudProxyCheck.isChecked():
            proxyList = self.cloudProxyEdit.text().split(';')
            proxyList = [proxy.split(':') for proxy in proxyList if ':' in proxy]
            proxyList = [(proxy[0], int(proxy[1])) for proxy in proxyList]
            self.rtcVideo.startCloudProxy(proxyList)
        else:
            self.rtcVideo.stopCloudProxy()

    def onComboxRoomIdSelectionChanged(self, index: int) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if roomId in self.rtcRoomUsers:
            users = self.rtcRoomUsers[roomId]
            self.subscribeScreenUserCombox.clear()
            self.subscribeScreenUserCombox.addItems(users)
            self.subscribeStreamUserCombox.clear()
            self.subscribeStreamUserCombox.addItems(users)

    def onClickExternalVideoSourceCheck(self) -> None:
        if not self.rtcVideo:
            return
        if self.externalVideoSourceCheck.isChecked():
            self.rtcVideo.stopVideoCapture()    # don't need
            self.rtcVideo.setVideoSourceType(stream_index=sdk.StreamIndex.Main, source_type=sdk.VideoSourceType.External)
            self.startPushFrames()
        else:
            self.stopPushFrames()
            self.rtcVideo.setVideoSourceType(stream_index=sdk.StreamIndex.Main, source_type=sdk.VideoSourceType.Internal)
            self.rtcVideo.startVideoCapture()  # must need
        # self.onClickSetLocalVideoCanvasBtn()

    def onClickSetEnvBtn(self) -> None:
        index = self.envCombox.currentIndex()
        if index < 0:
            return
        env = sdk.Env(index)
        sdk.setEnv(env)

    def onClickCreateRtcVideoBtn(self) -> None:
        if self.rtcVideo and self.rtcVideo.IRTCVideo:
            return
        appInfo = self.configJson['appNameList'][self.appNameCombox.currentIndex()]
        self.rtcVideo = sdk.RTCVideo(app_id=appInfo['appId'], event_handler=self, parameters='{"testKey": "testValue"}')
        self.setWindowTitle(f'{DemoTitle}, {sdk.SdkVersion}, version: {sdk.getVersion()}, APILog: bytesdklog/{sdk.APILogPath}')
        if self.cloudProxyCheck.isChecked():
            self.onClickCloudProxyCheck()

    def onClickDestroyRtcVideoBtn(self) -> None:
        self.stopPushFrames()
        self.externalVideoSourceCheck.setChecked(False)
        self.captureSourceList = []
        self.captureSourceListCombox.clear()
        while self.roomIdCombox.count() > 0:
            self.onClickLeaveRoomBtn()
            self.onClickDestroyRoomBtn()
        if self.rtcVideo:
            self.vdm = None
            self.videoEffect = None
            self.rtcVideo.destroy()
            self.rtcVideo = None
            self.setWindowTitle(f'{DemoTitle}, {sdk.SdkVersion}')

    def onClickStartAudioCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.startAudioCapture()

    def onClickStopAudioCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.stopAudioCapture()

    def onComboxResolutionSelectionChanged(self) -> None:
        curText = self.resolutionCombox.currentText()
        size, fps = curText.split()
        width, height = size.split('*')
        fps = fps[:-3]
        self.widthEdit.setText(width)
        self.heightEdit.setText(height)
        self.fpsEdit.setText(fps)

    def onClickSetVideoCaptureConfigBtn(self) -> None:
        if not self.rtcVideo:
            return
        videoCaptureConfig = sdk.VideoCaptureConfig()
        videoCaptureConfig.capturePreference = sdk.CapturePreference(self.capturePreferenceCombox.currentIndex())
        videoCaptureConfig.width = int(self.widthEdit.text())
        videoCaptureConfig.height = int(self.heightEdit.text())
        videoCaptureConfig.frameRate = int(self.fpsEdit.text())
        self.rtcVideo.setVideoCaptureConfig(videoCaptureConfig)

    def onClickSetVideoEncoderConfigBtn(self) -> None:
        if not self.rtcVideo:
            return
        videoEncoderConfig = sdk.VideoEncoderConfig()
        videoEncoderConfig.width = int(self.widthEdit.text())
        videoEncoderConfig.height = int(self.heightEdit.text())
        videoEncoderConfig.frameRate = int(self.fpsEdit.text())
        videoEncoderConfig.maxBitrate = int(self.bitrateEdit.text())
        videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Framerate
        self.videoEncoderConfig = videoEncoderConfig
        self.rtcVideo.setVideoEncoderConfig(videoEncoderConfig)
        #todo notify pushvideoframe thread to changed video size

    def onClickSetLocalVideoCanvasBtn(self) -> None:
        if not self.rtcVideo:
            return
        viewText = self.localViewEdit.text().strip()
        if viewText.startswith('0x') or viewText.startswith('0X'):
            viewHandle = int(viewText, base=16)
        else:
            viewHandle = int(viewText, base=10)
        videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=sdk.RenderMode.Fit, background_color=0x000000)
        streamIndex = sdk.StreamIndex(int(self.localStreamIndexCombox.currentText()[-1]))
        self.rtcVideo.setLocalVideoCanvas(index=streamIndex, canvas=videoCanvas)

    def onClickVDMBtn(self) -> None:
        if not self.rtcVideo:
            return
        self.vdm = self.rtcVideo.getVideoDeviceManager()
        if not self.vdm:
            return
        deviceList = self.vdm.enumerateVideoCaptureDevices2()
        self.vdmActions = []
        menu = QMenu(self)
        for deviceInfo in deviceList:
            action = QAction(deviceInfo.device_name)
            action.setData(deviceInfo.device_id)
            action.triggered.connect(self.onActionSetVideoDevice)
            self.vdmActions.append(action)
            menu.addAction(action)
        menu.exec_(QCursor.pos())

    def onActionSetVideoDevice(self) -> None:
        action = self.sender()
        if action and self.vdm:
            self.vdm.setVideoCaptureDevice(action.data())

    def onClickStartVideoCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.startVideoCapture()

    def onClickStopVideoCaptureBtn(self) -> None:
        if self.rtcVideo:
            self.rtcVideo.stopVideoCapture()

    def onClickGetScreenCaptureSourceListBtn(self) -> None:
        if not self.rtcVideo:
            return
        self.captureSourceList = self.rtcVideo.getScreenCaptureSourceList()
        self.captureSourceListCombox.clear()
        for source in self.captureSourceList:
            self.captureSourceListCombox.addItem(source.source_name)

    def onClickStartScreenVideoCaptureBtn(self) -> None:
        if not self.rtcVideo or not self.captureSourceList:
            return
        captureParam = sdk.ScreenCaptureParameters()
        captureParam.capture_mouse_cursor = True
        #captureParam.capture_mouse_cursor = False
        captureParam.content_hint = sdk.ContentHint.Details  # 0
        # captureParam.content_hint = sdk.ContentHint.Motion  #1
        captureParam.filter_config = sdk.ScreenFilterConfig()
        captureParam.filter_config.excluded_window_list = []  # [0x13143, 0x31434]
        captureParam.highlight_config = sdk.HighlightConfig()
        captureParam.highlight_config.border_color = 0xFF29CCA3
        captureParam.highlight_config.enable_highlight = True
        #captureParam.highlight_config.enable_highlight = False
        captureParam.highlight_config.border_width = 4
        captureParam.region_rect = sdk.Rectangle(x=0, y=0, width=1920, height=1080)
        sourceInfo = self.captureSourceList[self.captureSourceListCombox.currentIndex()]
        self.rtcVideo.startScreenVideoCapture(sourceInfo, captureParam)

    def onClickStopScreenVideoCaptureBtn(self) -> None:
        if not self.rtcVideo:
            return
        self.rtcVideo.stopScreenVideoCapture()

    def onClickCreateRTCRoomBtn(self) -> None:
        if self.rtcVideo:
            roomId = self.roomIdCombox.currentText().strip()
            if roomId in self.rtcRooms:
                return
            rtcRoom = self.rtcVideo.createRTCRoom(roomId)
            rtcRoomEventHandler = RTCRoomEventHandler(self, roomId)
            rtcRoom.setRTCRoomEventHandler(rtcRoomEventHandler)
            self.rtcRooms[roomId] = rtcRoom
            self.rtcRoomEventHandlers[roomId] = rtcRoomEventHandler
            self.rtcRoomUsers[roomId] = set()
            self.roomIdCombox.addItem(roomId)
            self.roomIdCombox.setCurrentIndex(self.roomIdCombox.count() - 1)

    def onClickJoinRoomBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        userId = self.userIdEdit.text().strip()
        token = self.tokenEdit.text().strip()
        if not token:
            userTokens = self.configJson['appNameList'][self.configJson['appNameIndex']].get(roomId, None)
            if userTokens:
                token = userTokens.get(userId, '')
        userInfo = sdk.UserInfo(uid=userId, extra_info='{"nickName":"yks"}')
        roomConfig = sdk.RTCRoomConfig(room_profile_type=sdk.RoomProfileType.LiveBroadcasting)
        roomConfig.is_auto_publish = self.autoPublishCheck.isChecked()
        roomConfig.is_auto_subscribe_audio = self.autoSubscribeAudioCheck.isChecked()
        roomConfig.is_auto_subscribe_video = self.autoSubscribeVideoCheck.isChecked()
        self.rtcRooms[roomId].joinRoom(token, user_info=userInfo, room_config=roomConfig)

    def onClickPublishStreamBtnBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        streamType = sdk.MediaStreamType(int(self.streamMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].publishStream(streamType)

    def onClickUnpublishStreamBtnBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        streamType = sdk.MediaStreamType(int(self.streamMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].unpublishStream(streamType)

    def onClickPublishScreenBtnBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        streamType = sdk.MediaStreamType(int(self.screenMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].publishScreen(streamType)

    def onClickUnpublishScreenBtnBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        streamType = sdk.MediaStreamType(int(self.screenMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].unpublishScreen(streamType)

    def onClickSubscribeStreamBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        userId = self.subscribeStreamUserCombox.currentText().strip()
        if not userId:
            return
        streamType = sdk.MediaStreamType(int(self.subscribeStreamMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].subscribeStream(userId, streamType)

    def onClickUnsubscribeStreamBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        userId = self.subscribeStreamUserCombox.currentText().strip()
        if not userId:
            return
        streamType = sdk.MediaStreamType(int(self.subscribeStreamMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].unsubscribeStream(userId, streamType)

    def onClickSubscribeScreenBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        userId = self.subscribeScreenUserCombox.currentText().strip()
        if not userId:
            return
        streamType = sdk.MediaStreamType(int(self.subscribeScreenMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].subscribeScreen(userId, streamType)

    def onClickUnsubscribeScreenBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        userId = self.subscribeScreenUserCombox.currentText().strip()
        if not userId:
            return
        streamType = sdk.MediaStreamType(int(self.subscribeScreenMediaStreamTypeCombox.currentText()[-1]))
        self.rtcRooms[roomId].unsubscribeScreen(userId, streamType)

    def onClickLeaveRoomBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        self.rtcRooms[roomId].leaveRoom()
        self.rtcRoomUsers[roomId].clear()
        self.resetViewsBackground(range(self.viewCount))    # todo
        self.uid2ViewIndex.clear()
        self.viewUsingIndex.clear()
        self.subscribeStreamUserCombox.clear()
        self.subscribeScreenUserCombox.clear()

    def onClickDestroyRoomBtn(self) -> None:
        roomId = self.roomIdCombox.currentText().strip()
        if not roomId in self.rtcRooms:
            return
        self.rtcRooms[roomId].destroy()
        self.rtcRooms.pop(roomId)
        self.rtcRoomEventHandlers.pop(roomId)
        self.rtcRoomUsers.pop(roomId)
        self.roomIdCombox.removeItem(self.roomIdCombox.currentIndex())
        if self.roomIdCombox.count() == 0:
            self.roomIdCombox.setCurrentText(roomId)

    def startPushFrames(self) -> None:
        if self.pushTaskId > 0:
            return
        self.stopEvent = threading.Event()
        self.pushUserId = self.userIdEdit.text().strip()
        self.pushTaskId = self.runTaskInThread(self.pushThreadFunc, (self.rtcVideo, self.videoEncoderConfig.width, self.videoEncoderConfig.height,
                                                                     self.videoEncoderConfig.frameRate, self.pushUserId, self.stopEvent), self.onPushThreadExit)

    def stopPushFrames(self) -> None:
        if self.pushTaskId == 0:
            return
        self.stopEvent.set()
        self.waitTask(self.pushTaskId)
        self.pushTaskId = 0

    def onPushThreadExit(self, taskId: int, msgId: int, args: Any) -> None:
        pass

    def pushThreadFunc(self, signal: pyqtSignal, taskId: int, args: Any) -> None:
        rtcVideo, videoWidth, videoHeight, fps, pushUserId, stopEvent = args
        pushText = 'hello'
        pushPixelFormat = 'RGBA'
        pushFrameCount = 0
        rawData = 0
        videoFormat = sdk.VideoPixelFormat.RGBA
        waitTime = 1000 / fps / 1000 * 0.95
        pixmap = QPixmap(videoWidth, videoHeight)
        #pixmap.fill(QColor(204, 232, 207))
        painter = QPainter()   # QPainter(pixmap)

        circleCount = 1
        radius = [videoHeight // random.randint(15, 25) for i in range(circleCount)]
        circleX = [random.randint(radius[i], videoWidth - radius[i]) for i in range(circleCount)]
        circleY = [random.randint(radius[i], videoHeight - radius[i]) for i in range(circleCount)]
        rightX = [videoWidth - radius[i] for i in range(circleCount)]
        rightY = [videoHeight - radius[i] for i in range(circleCount)]
        xSpeed = [videoWidth // random.randint(4, 16) for i in range(circleCount)]
        ySpeed = [videoHeight // random.randint(4, 16) for i in range(circleCount)]
        prevDrawTick = time.monotonic()
        cx = [0] * circleCount
        cy = [0] * circleCount

        now = time.monotonic()
        pushStartTick = now

        while 1:
            stopEvent.wait(waitTime)
            if stopEvent.is_set():
                break
            now = time.monotonic()
            elapsed = now - prevDrawTick
            prevDrawTick = now
            painter.begin(pixmap)
            font = painter.font()
            font.setFamilies(['微软雅黑', '黑体', 'Sans-Serif'])
            font.setBold(True)
            font.setPointSize(int(font.pointSize() * videoWidth / 360))
            painter.setFont(font)
            painter.fillRect(0, 0, videoWidth, videoHeight, QColor(204, 232, 207))
            qpen = QPen(QColor(255, 0, 0), 4, Qt.SolidLine)
            painter.setPen(qpen)

            cx = cx
            cy = cy
            for i in range(circleCount):
                cx[i] = circleX[i] + elapsed * xSpeed[i]
                if cx[i] > rightX[i]:
                    cx[i] = rightX[i] - (cx[i] - rightX[i])
                    xSpeed[i] = -xSpeed[i]
                elif cx[i] < radius[i]:
                    cx[i] = radius[i] + radius[i] - cx[i]
                    xSpeed[i] = -xSpeed[i]
                cy[i] = circleY[i] + elapsed * ySpeed[i]
                if cy[i] > rightY[i]:
                    cy[i] = rightY[i] - (cy[i] - rightY[i])
                    ySpeed[i] = -ySpeed[i]
                elif cy[i] < radius[i]:
                    cy[i] = radius[i] + radius[i] - cy[i]
                    ySpeed[i] = -ySpeed[i]
                #print('circle', cx[i], cy[i], radius)
                painter.drawEllipse(QPointF(circleX[i], circleY[i]), radius[i], radius[i])
            circleX[:], circleY[:] = cx, cy
            qpen = QPen(QColor(0, 0, 0), 1, Qt.SolidLine)
            painter.setPen(qpen)

            x, y = 10, 10
            fm = painter.fontMetrics()
            text = f"""user id:{pushUserId} SrcSize: {videoWidth}*{videoHeight} {pushPixelFormat}
{datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')}"""
            painter.drawText(x, y, videoWidth - x, videoHeight - y, Qt.TextWordWrap, text)
            y += (text.count('\n') + 1) * fm.height() + font.pointSize() // 2
            #print('font height, width, pointSize', fm.height(), fm.width(text[:text.find('\n')]), font.pointSize())
            if pushText:
                painter.drawText(x, y, videoWidth - x, videoHeight - y, Qt.TextWordWrap, pushText)
            painter.end()
            image = pixmap.toImage()
            # if not os.path.exists('agorapush.bmp'):
                # image.save('agorapush.bmp')
            bits = image.constBits()    # type(bits) == PyQt5.sip.voidptr
            bits.setsize(image.byteCount())
            rawData = ctypes.c_void_p(int(bits))

            if not rawData:
                print('wrong arguments, can not pushVideoFrame')
                continue
            frameBuilder = sdk.StructVideoFrameBuilder()
            frameBuilder.frame_type = sdk.VideoFrameType.RawMemory
            frameBuilder.pixel_fmt = videoFormat
            frameBuilder.color_space = 0  # kColorSpaceUnknown
            frameBuilder.data = (ctypes.c_void_p * 4)(rawData)
            frameBuilder.linesize = (ctypes.c_int * 4)(videoWidth * 4)
            frameBuilder.width = videoWidth
            frameBuilder.height = videoHeight
            frameBuilder.timestamp_us = int(time.time() * 100000)
            videoFrame = sdk.buildVideoFrame(frameBuilder)
            rtcVideo.pushExternalVideoFrame(videoFrame)
            #C++ pushExternalVideoFrame will release videoFrame, we can't release it again, so set its member to 0
            videoFrame.frame = 0
            videoFrame.pFrame = None
            pushFrameCount += 1
            waitTime = (pushFrameCount + 1) / fps - (now - pushStartTick)
            #print(f'{pushFrameCount} {fps} e {elapsed:.3f} w {waitTime:.3f}')
            if waitTime < 0:
                waitTime = 0

    def onRTCVideoEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        '''not run in UI thread'''
        eventStr = util.prettyDict(event, indent=1, indentStr="\t")
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
        timeStr = datetime.datetime.fromtimestamp(event_time / 1000000).strftime('%Y-%m-%d %H:%M:%S.%f')
        rowCount = self.itemModel.rowCount()

        # way 1
        #itemType = QStandardItem(eventType)
        #itemName = QStandardItem(event_name)
        #itemTime = QStandardItem(timeStr)
        #itemContent = QStandardItem(str(event))
        #itemContent.setData(event, role=Qt.UserRole)
        #self.itemModel.insertRow(rowCount, (itemType, itemName, itemTime, itemContent))
        #self.itemModel.appendRow((itemType, itemName, itemTime, itemContent))

        # way 2
        self.itemModel.insertRow(rowCount)
        self.itemModel.setData(self.itemModel.index(rowCount, ColumnEventType), eventType, role=Qt.DisplayRole)
        if eventType == 'RTCRoom':
            eventPrefix = self.currentEventRoomId + ' '
            self.itemModel.setData(self.itemModel.index(rowCount, ColumnEventType), self.currentEventRoomId, role=Qt.UserRole)
        else:
            eventPrefix = ''
        self.itemModel.setData(self.itemModel.index(rowCount, ColumnEventName), event_name)
        self.itemModel.setData(self.itemModel.index(rowCount, ColumnEventTime), timeStr)
        self.itemModel.setData(self.itemModel.index(rowCount, ColumnEventContent), f'{eventPrefix}{event}', role=Qt.DisplayRole)
        self.itemModel.setData(self.itemModel.index(rowCount, ColumnEventContent), event, role=Qt.UserRole)

        if self.configJson['maxEventRowCount'] > 0 and rowCount > self.configJson['maxEventRowCount']:
            self.itemModel.removeRow(0)
        if self.eventScrollEndCheck.isChecked():
            self.eventView.scrollToBottom()
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
        }

        self.RTCRoomEventHandler = {
            'onRoomStateChanged': self.onRoomStateChanged,
            'onUserJoined': self.onUserJoined,
            'onUserLeave': self.onUserLeave,
            'onUserPublishStream': self.onUserPublishStream,
            'onUserUnpublishStream': self.onUserUnpublishStream,
            'onUserPublishScreen': self.onUserPublishScreen,
            'onUserUnpublishScreen': self.onUserUnpublishScreen,
        }

    # RTCVideo Event Handler
    def onConnectionStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        pass

    def onTakeLocalSnapshotResult(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        videoFrame = sdk.IVideoFrame(event['video_frame'])
        self.appendOutputEditText(f'onTakeLocalSnapshotResult IVideoFrame: {videoFrame.width()}x{videoFrame.height()},'
                                  f'format {videoFrame.pixelFormat()}, planes {videoFrame.numberOfPlanes()}, stride {videoFrame.getPlaneStride(0)}')
        try:
            from PIL import Image
            arrayType = (ctypes.c_uint8 * (videoFrame.getPlaneStride(0) * videoFrame.height()))
            frameBuf = arrayType.from_address(videoFrame.getPlaneData(0).value)
            image = Image.frombytes('RGBA', (videoFrame.width(), videoFrame.height()), frameBuf, 'raw', 'BGRA')
            image.save('localSnapshot.bmp')
        except Exception as ex:
            self.appendOutputEditText(str(ex))
        videoFrame.release()

    def onTakeRemoteSnapshotResult(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        videoFrame = sdk.IVideoFrame(event['video_frame'])
        self.appendOutputEditText(f'onTakeRemoteSnapshotResult IVideoFrame: {videoFrame.width()}x{videoFrame.height()},'
                                  f'format {videoFrame.pixelFormat()}, planes {videoFrame.numberOfPlanes()}, stride {videoFrame.getPlaneStride(0)}')
        try:
            from PIL import Image
            arrayType = (ctypes.c_uint8 * (videoFrame.getPlaneStride(0) * videoFrame.height()))
            frameBuf = arrayType.from_address(videoFrame.getPlaneData(0).value)
            image = Image.frombytes('RGBA', (videoFrame.width(), videoFrame.height()), frameBuf, 'raw', 'BGRA')
            image.save('remoteSnapshot.bmp')
        except Exception as ex:
            self.appendOutputEditText(str(ex))
        videoFrame.release()

    # RTCRoom Event Handler
    def onRoomStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        state = event['state']
        if state != 0:
            errorInfo = sdk.getErrorDescription(state)
            sdk.log.info(f'error desc: {errorInfo}')
            self.checkSDKResult(state)

    def onUserJoined(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRoomUsers:
            return
        userId = event['user_info']['uid']
        self.rtcRoomUsers[self.currentEventRoomId].add(userId)
        if self.roomIdCombox.currentText() == self.currentEventRoomId:
            self.subscribeStreamUserCombox.addItem(userId)
            self.subscribeScreenUserCombox.addItem(userId)

    def onUserLeave(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.currentEventRoomId in self.rtcRoomUsers:
            return
        userId = event['user_id']
        self.rtcRoomUsers[self.currentEventRoomId].remove(userId)
        if self.roomIdCombox.currentText() == self.currentEventRoomId:
            for i in range(self.subscribeStreamUserCombox.count()):
                if userId == self.subscribeStreamUserCombox.itemText(i):
                    self.subscribeStreamUserCombox.removeItem(i)
                    break
            for i in range(self.subscribeScreenUserCombox.count()):
                if userId == self.subscribeScreenUserCombox.itemText(i):
                    self.subscribeScreenUserCombox.removeItem(i)
                    break

        if userId in self.uid2ViewIndex:
            for streamIndex, viewIndex in self.uid2ViewIndex[userId].items():
                if viewIndex in self.viewUsingIndex:
                    self.videoLabels[viewIndex].setText('Remote')
                    self.viewUsingIndex.remove(viewIndex)
                    self.resetViewsBackground([viewIndex])
            self.uid2ViewIndex.pop(userId)

    def onUserPublishStream(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.rtcVideo:
            return
        if not (event['type'] & sdk.MediaStreamType.Video):
            return
        userId = event['user_id']
        if not self.checkAutoSetRemoteStreamVideoCanvas.isChecked():
            sdk.log.warn(f'user_id {userId} joined, but do not setRemoteStreamVideoCanvas for he/she, AutoSetRemoteStreamVideoCanvas is not checked')
            return
        for i in range(self.remoteViewStartIndex, self.viewCount):
            if i not in self.viewUsingIndex:
                break
        else:
            index = self.layoutCombox.currentIndex() + 1
            if index < self.layoutCombox.count():
                self.layoutCombox.setCurrentIndex(index)
                # self.onComboxLayoutSelectionChanged(index)
        freeView, freeViewIndex = self.getFreeView()
        self.videoLabels[freeViewIndex].setText(f'Remote user_id {userId} Camera')
        self.viewUsingIndex.add(freeViewIndex)
        if userId in self.uid2ViewIndex:
            self.uid2ViewIndex[userId][sdk.StreamIndex.Main] = freeViewIndex
        else:
            self.uid2ViewIndex[userId] = {sdk.StreamIndex.Main: freeViewIndex}
        roomId = self.currentEventRoomId
        #roomId = ''
        remoteStreamKey = sdk.RemoteStreamKey(room_id=roomId, user_id=userId, stream_index=sdk.StreamIndex.Main)
        videoCanvas = sdk.VideoCanvas(view=freeView, render_mode=sdk.RenderMode.Fit, background_color=0x000000)
        if sdk.SdkVersion >= '3.47':
            self.rtcVideo.setRemoteVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        else:
            self.rtcVideo.setRemoteStreamVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)

    def onUserUnpublishStream(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.rtcVideo:
            return
        if not (event['type'] & sdk.MediaStreamType.Video):
            return
        if not self.checkAutoSetRemoteStreamVideoCanvas.isChecked():
            sdk.log.warn(f'user_id {userId} joined, but do not setRemoteStreamVideoCanvas for he/she, AutoSetRemoteStreamVideoCanvas is not checked')
            return
        userId = event['user_id']
        remoteStreamKey = sdk.RemoteStreamKey(room_id=self.currentEventRoomId, user_id=userId, stream_index=sdk.StreamIndex.Main)
        videoCanvas = sdk.VideoCanvas(view=0, render_mode=sdk.RenderMode.Fit, background_color=0x000000)
        if sdk.SdkVersion >= '3.47':
            self.rtcVideo.setRemoteVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        else:
            self.rtcVideo.setRemoteStreamVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        if userId in self.uid2ViewIndex:
            if sdk.StreamIndex.Main in self.uid2ViewIndex[userId]:
                viewIndex = self.uid2ViewIndex[userId].pop(sdk.StreamIndex.Main)
                if viewIndex in self.viewUsingIndex:
                    self.videoLabels[viewIndex].setText('Remote')
                    self.viewUsingIndex.remove(viewIndex)
                    self.resetViewsBackground([viewIndex])

    def onUserPublishScreen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.rtcVideo:
            return
        if not (event['type'] & sdk.MediaStreamType.Video):
            return
        userId = event['user_id']
        if not self.checkAutoSetRemoteStreamVideoCanvas.isChecked():
            sdk.log.warn(f'user_id {userId} joined, but do not setRemoteStreamVideoCanvas for he/she, AutoSetRemoteStreamVideoCanvas is not checked')
            return
        for i in range(self.remoteViewStartIndex, self.viewCount):
            if i not in self.viewUsingIndex:
                break
        else:
            index = self.layoutCombox.currentIndex() + 1
            if index < self.layoutCombox.count():
                self.layoutCombox.setCurrentIndex(index)
                # self.onComboxLayoutSelectionChanged(index)
        freeView, freeViewIndex = self.getFreeView()
        self.videoLabels[freeViewIndex].setText(f'Remote user_id {userId} Screen')
        self.viewUsingIndex.add(freeViewIndex)
        if userId in self.uid2ViewIndex:
            self.uid2ViewIndex[userId][sdk.StreamIndex.Screen] = freeViewIndex
        else:
            self.uid2ViewIndex[userId] = {sdk.StreamIndex.Screen: freeViewIndex}
        remoteStreamKey = sdk.RemoteStreamKey(room_id=self.currentEventRoomId, user_id=userId, stream_index=sdk.StreamIndex.Screen)
        videoCanvas = sdk.VideoCanvas(view=freeView, render_mode=sdk.RenderMode.Fit, background_color=0x000000)
        if sdk.SdkVersion >= '3.47':
            self.rtcVideo.setRemoteVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        else:
            self.rtcVideo.setRemoteStreamVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)

    def onUserUnpublishScreen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        if not self.rtcVideo:
            return
        if not (event['type'] & sdk.MediaStreamType.Video):
            return
        if not self.checkAutoSetRemoteStreamVideoCanvas.isChecked():
            sdk.log.warn(f'user_id {userId} joined, but do not setRemoteStreamVideoCanvas for he/she, AutoSetRemoteStreamVideoCanvas is not checked')
            return
        userId = event['user_id']
        remoteStreamKey = sdk.RemoteStreamKey(room_id=self.currentEventRoomId, user_id=userId, stream_index=sdk.StreamIndex.Screen)
        videoCanvas = sdk.VideoCanvas(view=0, render_mode=sdk.RenderMode.Fit, background_color=0x000000)
        if sdk.SdkVersion >= '3.47':
            self.rtcVideo.setRemoteVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        else:
            self.rtcVideo.setRemoteStreamVideoCanvas(stream_key=remoteStreamKey, canvas=videoCanvas)
        if userId in self.uid2ViewIndex:
            if sdk.StreamIndex.Screen in self.uid2ViewIndex[userId]:
                viewIndex = self.uid2ViewIndex[userId].pop(sdk.StreamIndex.Screen)
                if viewIndex in self.viewUsingIndex:
                    self.videoLabels[viewIndex].setText('Remote')
                    self.viewUsingIndex.remove(viewIndex)
                    self.resetViewsBackground([viewIndex])

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
            f'{DemoTitle} 不要在命令行界面上点击，否则会使UI线程卡住, ConsoleLog: bytesdklog'))
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

