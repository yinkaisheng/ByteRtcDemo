#!python3
# -*- coding: utf-8 -*-
import time
from typing import (Any, Callable, Dict, List, Tuple)
import threading
from PyQt5.QtCore import (QObject, QThread, QTimer, pyqtSignal, pyqtSlot)
import util


MsgIDThreadExit = 0
print = util.printx


class MyThread(QThread):
    Signal = pyqtSignal(tuple)

    def __init__(self, taskId: int, func: Callable[[pyqtSignal, int, Any], Any], args: Any, parent: QObject = None, notifyWhenExit: bool = True):
        super().__init__(parent)
        self.taskId = taskId
        self.func = func
        self.args = args
        self.notifyWhenExit = notifyWhenExit

    def run(self) -> None:
        sysThreadId = threading.get_ident()
        print('task id {} runs in thread {}'.format(self.taskId, sysThreadId))
        result = self.func(self.Signal, self.taskId, self.args)
        if self.notifyWhenExit:
            self.Signal.emit((self.taskId, MsgIDThreadExit, result))


class AsyncTask():
    def __init__(self):
        super().__init__()
        self._taskThreads = {}
        self._taskNotifiers = {}
        self._taskId = 0
        self._msgIdName = {MsgIDThreadExit: 'MsgIDThreadExit'}
        self.delayCallTimers = {}

    def delayCall(self, timeMs: int, func: Callable[[None], None]) -> None:
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.onDelayCallTimer)
        timer.start(timeMs)
        self.delayCallTimers[timer] = func

    def onDelayCallTimer(self) -> None:
        timer = self.sender()
        func = self.delayCallTimers.pop(timer)
        func()

    def setMsgIDName(self, msgId: int, name: str) -> None:
        self._msgIdName[msgId] = name

    def runTaskInThread(self, taskFunc: Callable[[pyqtSignal, int, Any], Any], args: Any, notifyFunc: Callable[[int, int, Any], None]) -> int:
        """
        run taskFunc with args in a new thread, notifyFunc will run in caller thread when the new thread emits a signal or exits
        taskFunc: callable function(signal: pyqtSignal, taskId: int, args: Any)
        notifyFunc: callable function(taskId: int, msgId: int, args: Any) or a function list,
                    if it is a list, only the first function has arguments(taskId: int, msgId: int, args: Any),
                    others have no arguments.
        in taskFunc, call signal.emit(taskId, msgId, args), msgId must > 0,
          then notifyFunc will be called in caller thread that spawned the new thread
        return int, a task id that starts with 1, corresponds to the new thread
        """
        self._taskId += 1
        thread = MyThread(self._taskId, taskFunc, args)
        thread.Signal.connect(self._threadSlot)
        self._taskThreads[self._taskId] = thread
        self._taskNotifiers[self._taskId] = notifyFunc
        sysThreadId = threading.get_ident()
        print('caller thread id {} spawns task id {}'.format(sysThreadId, self._taskId))
        thread.start()
        return self._taskId

    def taskIsRunning(self) -> bool:
        return bool(self._taskThreads)

    def taskCount(self) -> int:
        return len(self._taskThreads)

    def addExtraCallback(self, callbackFunc: Callable[[], None], callbackArgv: Any = None) -> None:
        for taskId in self._taskNotifiers:
            if isinstance(self._taskNotifiers[taskId], list):
                self._taskNotifiers[taskId].append((callbackFunc, callbackArgv))
            else:
                singleTask = self._taskNotifiers[taskId]
                self._taskNotifiers[taskId] = [singleTask, (callbackFunc, callbackArgv)]

    def _threadSlot(self, atuple: Tuple[int, int, Any]) -> None:
        taskId, msgId, args = atuple
        sysThreadId = threading.get_ident()
        print('slot runs in thread id {}, signal emitted from task id {}, msg id {}[{}]'.format(
            sysThreadId, taskId, msgId, self._msgIdName.get(msgId, '?')))
        if isinstance(self._taskNotifiers[taskId], list):
            self._taskNotifiers[taskId][0](taskId, msgId, args)
            for func, argv in self._taskNotifiers[taskId][1:]:  # [1:] are callbacks added by addExtraCallback
                print('----call extra callback----')
                func(argv)
        else:
            self._taskNotifiers[taskId](taskId, msgId, args)
        if msgId == MsgIDThreadExit:
            # avoid QThread: Destroyed while thread is still running
            while self._taskThreads[taskId].isRunning():
                time.sleep(0.005)
            del self._taskThreads[taskId]
            del self._taskNotifiers[taskId]
