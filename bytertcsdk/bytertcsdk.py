#!python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
import os
import sys
import time
import json
import ctypes
import functools
import threading
import logging as log
import ctypes.wintypes
from enum import Enum, IntEnum
from typing import (Any, Callable, Dict, List, Iterable, Tuple)

ExePath = os.path.abspath(sys.argv[0])
ExeDir, ExeNameWithExt = os.path.split(ExePath)
ExeNameNoExt = os.path.splitext(ExeNameWithExt)[0]
os.chdir(ExeDir)
LogDir = os.path.join(ExeDir, 'bytesdklog')
if os.path.exists('Lib') and not os.path.exists('bytertcsdk'):
    SdkDir = os.path.join('Lib', 'bytertcsdk')
else:
    SdkDir = 'bytertcsdk'
SdkDirFull = os.path.join(ExeDir, SdkDir)  # d:\Codes\Python\ByteRtcDemo\bytertcsdk
# the followings must be referenced by full name, such as bytertcsdk.bytertcsdk.SdkBinDir
SdkBinDir = ''  # binx86_3.43.102
SdkBinDirFull = ''  # d:\Codes\Python\ByteRtcDemo\bytertcsdk\binx86_3.43.102
SdkDllName = 'VolcEngineRTC.dll'
SdkVersion = ''  # '3.43.102'
APILogPath = f'pid{os.getpid()}_api.log'
DEVICE_ID_LENGTH = 512

if not os.path.exists(LogDir):
    os.makedirs(LogDir)
log.Formatter.default_msec_format = '%s.%03d'
log.basicConfig(filename=os.path.join(LogDir, APILogPath), level=log.INFO,
                format='%(asctime)s %(levelname)s %(filename)s L%(lineno)d T%(thread)d %(funcName)s: %(message)s')


class LogFormatter(log.Formatter):
    default_time_format = '%H:%M:%S'

    def __init__(self, fmt=None, datefmt=None, style='%', validate=True):
        super(LogFormatter, self).__init__(fmt, datefmt, style, validate)


class GuiStream():
    def __init__(self):
        self.logHandler = None

    def write(self, output: str) -> None:
        if self.logHandler:
            self.logHandler(output)

    def setLogHandler(self, handler) -> None:
        self.logHandler = handler


class GuiFilter(log.Filter):
        def filter(self, record: log.LogRecord):
            if record.funcName == 'API':
                return True


GuiStreamObj = GuiStream()
__sh = log.StreamHandler(GuiStreamObj)
__sh.setFormatter(LogFormatter('%(asctime)s %(filename)s L%(lineno)d T%(thread)d %(funcName)s: %(message)s'))
__logFilter = GuiFilter()
__sh.addFilter(__logFilter)
log.getLogger().addHandler(__sh)


if sys.stdout:
    # class MyHandler(log.Handler):
        # def emit(self, record):
            # print('custom handler called with\n', record)

    __stdsh = log.StreamHandler(sys.stdout)
    __stdsh.setFormatter(LogFormatter('%(asctime)s %(filename)s L%(lineno)d T%(thread)d %(funcName)s: %(message)s'))
    log.getLogger().addHandler(__stdsh)


def isPy38OrHigher():
    return sys.version_info[:2] >= (3, 8)


LastAPICall = ''


def APITime(func):
    @functools.wraps(func)
    def API(*args, **kwargs):
        global LastAPICall
        # argsstr = ', '.join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in args if not isinstance(arg, RTCVideo))
        argsstr = ', '.join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in args[1:])
        keystr = ', '.join('{}={}'.format(k, f"'{v}'" if isinstance(v, str) else v) for k, v in kwargs.items())
        if keystr:
            if argsstr:
                argsstr += ', ' + keystr
            else:
                argsstr = keystr
        LastAPICall = f'{func.__qualname__}({argsstr})'
        log.info(LastAPICall)
        start = time.monotonic()
        ret = func(*args, **kwargs)
        costTime = time.monotonic() - start
        log.info(f'{func.__qualname__} returns {ret}, costTime={costTime:.3} s')
        return ret
    return API


class MyIntEnum(IntEnum):
    __str__ = IntEnum.__repr__


class _DllClient:
    _instance = None

    @classmethod
    def instance(cls) -> '_DllClient':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        os.environ["PATH"] = SdkBinDirFull + os.pathsep + os.environ["PATH"]
        load = False
        try:
            dllPath = os.path.join(SdkBinDirFull, 'ByteRTCPythonSDK.dll')
            self.dll = ctypes.cdll.LoadLibrary(dllPath)
            print(f'load dll: {dllPath}')
            load = True
        except Exception as ex:
            log.error(ex)
        if load:
            self.dll.byte_createRTCVideoEventHandler.restype = ctypes.c_void_p
            self.dll.byte_createRTCVideo.restype = ctypes.c_void_p
            self.dll.byte_getErrorDescription.restype = ctypes.c_char_p
            self.dll.byte_getSDKVersion.restype = ctypes.c_char_p
            self.dll.byte_RTCVideo_getScreenCaptureSourceList.restype = ctypes.c_void_p
            self.dll.byte_RTCVideo_createRTCRoom.restype = ctypes.c_void_p
            self.dll.byte_RTCVideo_getVideoDeviceManager.restype = ctypes.c_void_p
            self.dll.byte_IVideoDeviceManager_enumerateVideoCaptureDevices.restype = ctypes.c_void_p
        else:
            self.dll = None
            log.error(f'Can not load dll. path={SdkBinDirFull}')

    def __del__(self):
        if self.dll:
            pass


def chooseSdkBinDir(sdkBinDir: str):
    '''sdkBinDir: str, such as 'binx86_3.43.102' '''
    global SdkBinDir, SdkBinDirFull, SdkVersion
    SdkBinDir = sdkBinDir
    SdkVersion = SdkBinDir.split('_', 1)[-1]
    if ExeDir.endswith(SdkDir):  # for run bytertcsdk.py directlly
        SdkBinDirFull = os.path.join(ExeDir, SdkBinDir)
    else:
        SdkBinDirFull = os.path.join(ExeDir, SdkDir, SdkBinDir)
    print(f'SdkBinDir={SdkBinDir}, SdkVersion={SdkVersion}, SdkBinDirFull={SdkBinDirFull}')


def getVersion() -> str:
    version = _DllClient.instance().dll.byte_getSDKVersion()
    return version.decode()


def getErrorDescription(error: int) -> str:
    errorDesc = _DllClient.instance().dll.byte_getErrorDescription(error)
    return errorDesc.decode()


class VideoEncodePreference(MyIntEnum):
    Disabled = 0
    Framerate = 1
    Quality = 2
    Balance = 3


class VideoStreamScaleMode(MyIntEnum):
    Auto = 0
    Stretch = 1
    FitWithCropping = 2
    FitWithFilling = 3


class RoomProfileType(MyIntEnum):
    Communication = 0
    LiveBroadcasting = 1
    Game = 2
    CloudGame = 3
    LowLatency = 4
    Chat = 5
    ChatRoom = 6
    LwTogether = 7
    GameHD = 8
    CoHost = 9
    InteractivePodcast = 10
    KTV = 11
    Chorus = 12
    VRChat = 13
    GameStreaming = 14
    LanLiveStreaming = 15
    Meeting = 16
    MeetingRoom = 17
    Classroom = 18


class StreamIndex(MyIntEnum):
    Main = 0
    Screen = 1


class RenderMode(MyIntEnum):
    Hidden = 1
    Fit = 2
    Fill = 3


class ConnectionState(MyIntEnum):
    Disconnected = 1
    Connecting = 2
    Connected = 3
    Reconnecting = 4
    Reconnected = 5
    Lost = 6
    Failed = 7


class NetworkType(MyIntEnum):
    Unknown = -1
    Disconnected = 0
    LAN = 1
    WIFI = 2
    Mobile2G = 3
    Mobile3G = 4
    Mobile4G = 5
    Mobile5G = 6


class PerformanceAlarmMode(MyIntEnum):
    Normal = 0
    Simulcast = 1


class PerformanceAlarmReason(MyIntEnum):
    BandwidthFallbacked = 0
    BandwidthResumed = 1
    PerformanceFallbacked = 2
    PerformanceResumed = 3


class MediaDeviceType(MyIntEnum):
    AudioUnknown = -1
    AudioRenderDevice = 0
    AudioCaptureDevice = 1
    VideoRenderDevice = 2
    VideoCaptureDevice = 3
    ScreenVideoCaptureDevice = 4
    ScreenAudioCaptureDevice = 5


class MediaDeviceState(MyIntEnum):
    Started = 1
    Stopped = 2
    RuntimeError = 3
    Paused = 4
    Resumed = 5
    Added = 10
    Removed = 11
    InterruptionBegan = 12
    InterruptionEnded = 13
    BecomeSystemDefault = 14
    ResignSystemDefault = 15


class MediaDeviceWarning(MyIntEnum):
    OK = 0
    OperationDenied = 1
    CaptureSilence = 2
    AndroidSysSilence = 3
    AndroidSysSilenceDisappear = 4
    DetectClipping = 10
    DetectLeakEcho = 11
    DetectLowSNR = 12
    DetectInsertSilence = 13
    CaptureDetectSilence = 14
    CaptureDetectSilenceDisappear = 15
    CaptureDetectHowling = 16
    SetAudioRouteInvalidScenario = 20
    SetAudioRouteNotExists = 21
    SetAudioRouteFailedByPriority = 22
    SetAudioRouteNotVoipMode = 23
    SetAudioRouteDeviceNotStart = 24


class MediaDeviceError(MyIntEnum):
    OK = 0
    DeviceNoPermission = 1
    DeviceBusy = 2
    DeviceFailure = 3
    DeviceNotFound = 4
    DeviceDisconnected = 5
    DeviceNoCallback = 6
    DeviceUNSupportFormat = 7
    DeviceNotFindGroupId = 8


class AudioDeviceType(MyIntEnum):
    Unknown = -1
    RenderDevice = 0
    CaptureDevice = 1
    ScreenCaptureDevice = 2


class VideoDeviceType(MyIntEnum):
    Unknown = -1
    RenderDevice = 0
    CaptureDevice = 1
    ScreenCaptureDevice = 2


class HttpProxyState(MyIntEnum):
    Init = 0
    Connected = 1
    Error = 2


class Socks5ProxyState(MyIntEnum):
    Init = 0
    Connected = 1
    Error = 2
    TcpConnectFail = 3
    TcpClose = 4
    ProtocolTcpFail = 5
    ProtocolUdpFail = 6
    AuthFail = 7
    Unknown = 8


class RecordingState(MyIntEnum):
    Error = 0
    Processing = 1
    Success = 2


class RecordingErrorCode(MyIntEnum):
    Ok = 0
    NoPermission = -1
    NotSupport = -2
    Other = -3


class VideoCodecType(MyIntEnum):
    Unknown = 0
    H264 = 1
    ByteVC1 = 2


class VideoCodecMode(MyIntEnum):
    Auto = 0
    Hardware = 1
    Software = 2


class SEIStreamEventType(MyIntEnum):
    StreamAdd = 0
    StreamRemove = 1


class SyncInfoStreamType(MyIntEnum):
    Audio = 0


class NetworkDetectionLinkType(MyIntEnum):
    Up = 0
    Down = 1


class NetworkQuality(MyIntEnum):
    Unknown = 0
    Excellent = 1
    Good = 2
    Poor = 3
    Bad = 4
    Vbad = 5


class NetworkDetectionStopReason(MyIntEnum):
    User = 0
    Timeout = 1
    ConnectionLost = 2
    Streaming = 3
    InnerErr = 4


class MuteState(MyIntEnum):
    Off = 0
    On = 1


class LocalAudioStreamState(MyIntEnum):
    Stopped = 0
    Recording = 1
    Encoding = 2
    Failed = 3
    Mute = 4
    Unmute = 5


class LocalAudioStreamError(MyIntEnum):
    Ok = 0
    Failure = 1
    DeviceNoPermission = 2
    DeviceBusy = 3
    RecordFailure = 4
    EncodeFailure = 5
    NoRecordingDevice = 6


class RemoteAudioState(MyIntEnum):
    Stopped = 0
    Starting = 1
    Decoding = 2
    Frozen = 3
    Failed = 4


class RemoteAudioStateChangeReason(MyIntEnum):
    Internal = 0
    NetworkCongestion = 1
    NetworkRecovery = 2
    LocalMuted = 3
    LocalUnmuted = 4
    RemoteMuted = 5
    RemoteUnmuted = 6
    RemoteOffline = 7


class LocalVideoStreamState(MyIntEnum):
    Stopped = 0
    Recording = 1
    Encoding = 2
    Failed = 3


class LocalVideoStreamError(MyIntEnum):
    Ok = 0
    Failure = 1
    DeviceNoPermission = 2
    DeviceBusy = 3
    DeviceNotFound = 4
    CaptureFailure = 5
    EncodeFailure = 6
    DeviceDisconnected = 7


class RemoteVideoState(MyIntEnum):
    Stopped = 0
    Starting = 1
    Decoding = 2
    Frozen = 3
    Failed = 4


class RemoteVideoStateChangeReason(MyIntEnum):
    Internal = 0
    NetworkCongestion = 1
    NetworkRecovery = 2
    LocalMuted = 3
    LocalUnmuted = 4
    RemoteMuted = 5
    RemoteUnmuted = 6
    RemoteOffline = 7


class FirstFrameSendState(MyIntEnum):
    Sending = 0
    Sent = 1
    End = 2


class FirstFramePlayState(MyIntEnum):
    Playing = 0
    Played = 1
    End = 2


class EchoTestResult(MyIntEnum):
    TestSuccess = 0
    TestTimeout = 1
    TestIntervalShort = 2
    AudioDeviceError = 3
    VideoDeviceError = 4
    AudioReceiveError = 5
    VideoReceiveError = 6
    InternalError = 7


class MediaStreamType(MyIntEnum):
    Audio = 1 << 0
    Video = 1 << 1
    Both = (1 << 0) | (1 << 1)


class ScreenMediaType(MyIntEnum):
    VideoOnly = 0
    AudioOnly = 1
    VideoAndAudio = 2


class ScreenCaptureSourceType(MyIntEnum):
    Unknown = 0
    Window = 1
    Screen = 2


class MouseCursorCaptureState(MyIntEnum):
    On = 0
    Off = 1


class ContentHint(MyIntEnum):
    Details = 0
    Motion = 1


class UserOfflineReason(MyIntEnum):
    Quit = 0
    Dropped = 1
    SwitchToInvisible = 2
    KickedByAdmin = 3


class StreamRemoveReason(MyIntEnum):
    Unpublish = 0
    PublishFailed = 1
    KeepLiveFailed = 2
    ClientDisconnected = 3
    Republish = 4
    Other = 5


class SubscribeState(MyIntEnum):
    Success = 0
    FailedNotInRoom = 1
    FailedStreamNotFound = 2
    FailedOverLimit = 3


class RtcRoomMode(MyIntEnum):
    Normal = 0
    AudioSelection = 1


class AVSyncState(MyIntEnum):
    AVStreamSyncBegin = 0
    AudioStreamRemove = 1
    VdieoStreamRemove = 2
    SetAVSyncStreamId = 3


class ForwardStreamError(MyIntEnum):
    OK = 0
    InvalidArgument = 1201
    InvalidToken = 1202
    Response = 1203
    RemoteKicked = 1204
    NotSupport = 1205


class ForwardStreamState(MyIntEnum):
    Idle = 0
    Success = 1
    Failure = 2


class ForwardStreamEvent(MyIntEnum):
    Disconnected = 0
    Connected = 1
    Interrupt = 2
    DstRoomUpdated = 3
    UnExpectAPICall = 4


class DeviceTransportType(MyIntEnum):
    Unknown = 0
    BuiltIn = 1
    BlueToothUnknownMode = 2
    BlueToothHandsFreeMode = 3
    BlueToothStereoMode = 4
    DisplayAudio = 5
    Virtual = 6


class StructVideoCanvas(ctypes.Structure):
    _fields_ = [("view", ctypes.c_void_p),
                ("render_mode", ctypes.c_int),
                ("background_color", ctypes.c_int),
                ]


class VideoCanvas:
    def __init__(self, view: int, render_mode: RenderMode = RenderMode.Hidden, background_color: int = 0x000000):
        self.view = view
        self.render_mode = render_mode
        self.background_color = background_color

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(view={self.view}(0x{self.view:X}), render_mode={self.render_mode}, background_color=0x{self.background_color:X})'

    __repr__ = __str__

    def toStruct(self) -> StructVideoCanvas:
        #sVideoCanvas = StructVideoCanvas(self.view, self.render_mode, self.background_color)
        sVideoCanvas = StructVideoCanvas()
        sVideoCanvas.view = self.view
        sVideoCanvas.render_mode = self.render_mode
        sVideoCanvas.background_color = self.background_color
        return sVideoCanvas


class StructVideoSolution(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("fps", ctypes.c_int),
                ("max_send_kbps", ctypes.c_int),
                ("encode_preference", ctypes.c_int),
                ]


class VideoSolution:
    def __init__(self, width: int = 0, height: int = 0, fps: int = 0, max_send_kbps: int = -1, encode_preference: VideoEncodePreference = VideoEncodePreference.Framerate):
        self.width = width
        self.height = height
        self.fps = fps
        self.max_send_kbps = max_send_kbps
        self.encode_preference = encode_preference

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(width={self.width}, height={self.height}, fps={self.fps}, max_send_kbps={self.max_send_kbps}'    \
               f', encode_preference={self.encode_preference})'

    __repr__ = __str__

    def toStruct(self) -> StructVideoSolution:
        sVideoSolu = StructVideoSolution()
        sVideoSolu.width = self.width
        sVideoSolu.height = self.height
        sVideoSolu.fps = self.fps
        sVideoSolu.max_send_kbps = self.max_send_kbps
        sVideoSolu.encode_preference = self.encode_preference
        return sVideoSolu


class StructUserInfo(ctypes.Structure):
    _fields_ = [("uid", ctypes.c_char_p),
                ("extra_info", ctypes.c_char_p),
                ]


class UserInfo:
    def __init__(self, uid: str, extra_info: str = None):
        self.uid = uid  # [a-zA-Z0-9_@\-]{1,128}
        self.extra_info = extra_info  # max 200 size

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(uid={self.uid}, extra_info={self.extra_info})'

    __repr__ = __str__

    def toStruct(self) -> StructUserInfo:
        sUserInfo = StructUserInfo()
        sUserInfo.uid = self.uid.encode()
        sUserInfo.extra_info = self.extra_info.encode()
        return sUserInfo


class StructRemoteStreamKey(ctypes.Structure):
    _fields_ = [("room_id", ctypes.c_char_p),
                ("user_id", ctypes.c_char_p),
                ("stream_index", ctypes.c_int),
                ]


class RemoteStreamKey:
    def __init__(self, room_id: str, user_id: str, stream_index: StreamIndex):
        self.room_id = room_id
        self.user_id = user_id
        self.stream_index = stream_index

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(room_id={self.room_id}, user_id={self.user_id}, stream_index={self.stream_index})'

    __repr__ = __str__

    def toStruct(self) -> StructRemoteStreamKey:
        sRemoteStreamKey = StructRemoteStreamKey()
        sRemoteStreamKey.room_id = self.room_id.encode()
        sRemoteStreamKey.user_id = self.user_id.encode()
        sRemoteStreamKey.stream_index = self.stream_index
        return sRemoteStreamKey


class StructRemoteVideoConfig(ctypes.Structure):
    _fields_ = [("framerate", ctypes.c_int),
                ("resolution_width", ctypes.c_int),
                ("resolution_height", ctypes.c_int),
                ]


class RemoteVideoConfig:
    def __init__(self, framerate: int = 0, resolution_width: int = 0, resolution_height: int = 0):
        self.framerate = framerate
        self.resolution_width = resolution_width
        self.resolution_height = resolution_height

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(framerate={self.framerate}, resolution_width={self.resolution_width}, resolution_height={self.resolution_height})'

    __repr__ = __str__

    def toStruct(self) -> StructRemoteVideoConfig:
        sRemoteVideoConfig = StructRemoteVideoConfig()
        sRemoteVideoConfig.framerate = self.framerate
        sRemoteVideoConfig.resolution_width = self.resolution_width
        sRemoteVideoConfig.resolution_height = self.resolution_height
        return sRemoteVideoConfig


class StructRectangle(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int),
                ("y", ctypes.c_int),
                ("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ]


class Rectangle:
    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(x={self.x}, y={self.y}, width={self.width}, height={self.height})'

    __repr__ = __str__

    def toStruct(self) -> StructRectangle:
        sRect = StructRectangle()
        sRect.x = self.x
        sRect.y = self.y
        sRect.width = self.width
        sRect.height = self.height
        return sRect


class StructScreenCaptureSourceInfo(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int),
                ("source_id", ctypes.c_void_p),
                ("source_name", ctypes.c_char_p),
                ("application", ctypes.c_char_p),
                ("pid", ctypes.c_int),
                ("primaryMonitor", ctypes.c_bool),
                ("region_rect", StructRectangle),
                ]


class ScreenCaptureSourceInfo:
    def __init__(self):
        self.type = ScreenCaptureSourceType.Unknown
        self.source_id = 0
        self.source_name = ''
        self.application = ''
        self.pid = 0
        self.primaryMonitor = True
        self.region_rect = Rectangle()

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(type={self.type}, source_id={self.source_id}, source_name={self.source_name}'     \
               f', application={self.application}, pid={self.pid}, primaryMonitor={self.primaryMonitor}, region_rect={self.region_rect})'

    __repr__ = __str__

    def toStruct(self) -> StructScreenCaptureSourceInfo:
        sSourceInfo = StructScreenCaptureSourceInfo()
        sSourceInfo.type = self.type
        sSourceInfo.source_id = self.source_id
        sSourceInfo.source_name = self.source_name.encode()
        sSourceInfo.application = self.application.encode()
        sSourceInfo.pid = self.pid
        sSourceInfo.primaryMonitor = self.primaryMonitor
        sSourceInfo.region_rect = self.region_rect.toStruct()
        return sSourceInfo


class StructScreenFilterConfig(ctypes.Structure):
    _fields_ = [("excluded_window_list", ctypes.c_void_p),
                ("excluded_window_num", ctypes.c_int),
                ]


class ScreenFilterConfig:
    def __init__(self, excluded_window_list: List[int] = None):
        self.excluded_window_list = excluded_window_list

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(excluded_window_list={self.excluded_window_list})'

    __repr__ = __str__

    def toStruct(self) -> StructScreenFilterConfig:
        sFilterConfig = StructScreenFilterConfig()
        if self.excluded_window_list:
            sFilterConfig.excluded_window_list = (ctypes.c_size_t * len(self.excluded_window_list))(self.excluded_window_list)
            sFilterConfig.excluded_window_num = len(self.excluded_window_list)
        else:
            sFilterConfig.excluded_window_list = None
            sFilterConfig.excluded_window_num = 0
        return sFilterConfig


class StructHighlightConfig(ctypes.Structure):
    _fields_ = [("enable_highlight", ctypes.c_bool),
                ("border_color", ctypes.c_uint32),
                ("border_width", ctypes.c_int),
                ]


class HighlightConfig:
    def __init__(self):
        self.enable_highlight = True
        self.border_color = 0xFF29CCA3
        self.border_width = 4

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(enable_highlight={self.enable_highlight}, border_color=0x{self.border_color:08X}, border_width={self.border_width})'

    __repr__ = __str__

    def toStruct(self) -> StructHighlightConfig:
        sConfig = StructHighlightConfig()
        sConfig.enable_highlight = self.enable_highlight
        sConfig.border_color = self.border_color
        sConfig.border_width = self.border_width
        return sConfig


class StructScreenCaptureParameters(ctypes.Structure):
    _fields_ = [("content_hint", ctypes.c_int),
                ("region_rect", StructRectangle),
                ("capture_mouse_cursor", ctypes.c_int),
                ("filter_config", StructScreenFilterConfig),
                ("highlight_config", StructHighlightConfig),
                ]


class ScreenCaptureParameters:
    def __init__(self):
        self.content_hint = ContentHint.Details
        self.region_rect = Rectangle()
        self.capture_mouse_cursor = MouseCursorCaptureState.On
        self.filter_config = ScreenFilterConfig()
        self.highlight_config = HighlightConfig()

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(content_hint={self.content_hint}, region_rect={self.region_rect}'    \
               f', filter_config={self.filter_config}, highlight_config={self.highlight_config})'

    __repr__ = __str__

    def toStruct(self) -> StructScreenCaptureParameters:
        sCaptureParams = StructScreenCaptureParameters()
        sCaptureParams.content_hint = self.content_hint
        sCaptureParams.region_rect = self.region_rect.toStruct()
        sCaptureParams.capture_mouse_cursor = self.capture_mouse_cursor
        sCaptureParams.filter_config = self.filter_config.toStruct()
        sCaptureParams.highlight_config = self.highlight_config.toStruct()
        return sCaptureParams


class StructRTCRoomConfig(ctypes.Structure):
    _fields_ = [("room_profile_type", ctypes.c_int),
                ("is_auto_publish", ctypes.c_bool),
                ("is_auto_subscribe_audio", ctypes.c_bool),
                ("is_auto_subscribe_video", ctypes.c_bool),
                ("remote_video_config", StructRemoteVideoConfig),
                ]


class RTCRoomConfig:
    def __init__(self, room_profile_type: RoomProfileType = RoomProfileType.Communication):
        self.room_profile_type = room_profile_type
        self.is_auto_publish = True
        self.is_auto_subscribe_audio = True
        self.is_auto_subscribe_video = True
        self.remote_video_config = RemoteVideoConfig()

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(room_profile_type={self.room_profile_type}'  \
               f', is_auto_publish={self.is_auto_publish}, is_auto_subscribe_video={self.is_auto_subscribe_video}'  \
               f', remote_video_config={self.remote_video_config})'

    __repr__ = __str__

    def toStruct(self) -> StructRTCRoomConfig:
        sRTCRoomConfig = StructRTCRoomConfig()
        sRTCRoomConfig.room_profile_type = self.room_profile_type
        sRTCRoomConfig.is_auto_publish = self.is_auto_publish
        sRTCRoomConfig.is_auto_subscribe_audio = self.is_auto_subscribe_audio
        sRTCRoomConfig.is_auto_subscribe_video = self.is_auto_subscribe_video
        sRTCRoomConfig.remote_video_config = self.remote_video_config.toStruct()
        return sRTCRoomConfig


class StructVideoDeviceInfo(ctypes.Structure):
    _fields_ = [("device_id", ctypes.c_char * DEVICE_ID_LENGTH),
                ("device_name", ctypes.c_char * DEVICE_ID_LENGTH),
                ("device_vid", ctypes.c_int64),
                ("device_pid", ctypes.c_int64),
                ("transport_type", ctypes.c_int),
                ]


class VideoDeviceInfo:
    def __init__(self):
        self.device_id = ''
        self.device_name = ''
        self.device_vid = 0
        self.device_pid = 0
        self.transport_type = DeviceTransportType.Unknown

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(device_id={self.device_id}, device_name={self.device_name}'  \
               f', device_vid={self.device_vid}, device_pid={self.device_pid}, transport_type={self.transport_type}'

    __repr__ = __str__

    #def toStruct(self) -> StructVideoDeviceInfo:


RTCEventCFuncCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_char_p)


class IRTCRoomEventHandler:
    def onRTCRoomEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        """
        event_time: micro seconds since epoch
        """
        print(f'{event_name} {event_json}')


class IRTCVideoEventHandler:
    def onRTCVideoEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        """
        event_time: micro seconds since epoch
        """
        print(f'{event_name} {event_json}')


class RTCRoom:
    def __init__(self, room_id: str, IRTCRoom: int):
        self.dll = _DllClient.instance().dll
        self.roomId = room_id
        self.IRTCRoom = IRTCRoom
        self.pIRTCRoom = ctypes.c_void_p(self.IRTCRoom)
        self.roomEventHandler = None
        self.roomEventCFuncCallback = RTCEventCFuncCallback(self.RTCRoomEventCFuncCallback)
        self.IRTCRoomEventHandler = self.dll.byte_createRTCRoomEventHandler()
        self.pIRTCRoomEventHandler = ctypes.c_void_p(self.IRTCRoomEventHandler)
        self.dll.byte_RTCRoom_setRTCRoomEventHandler(self.pIRTCRoom, self.pIRTCRoomEventHandler)
        self.dll.byte_RTCRoomEventHandler_setCallback(self.pIRTCRoomEventHandler, self.roomEventCFuncCallback)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(id=0x{id(self):X}, IRTCRoom=0x{self.IRTCRoom:X})'

    def __del__(self):
        self.destroy()

    def RTCRoomEventCFuncCallback(self, event_handler: int, event_time: int, event_name: bytes, event_json: bytes) -> None:
        event_name = event_name.decode()
        event_json = event_json.decode()
        event = json.loads(event_json)
        self.__modifyEventIfHasEnum(event_name, event)
        if self.roomEventHandler:
            self.roomEventHandler.onRTCRoomEventHappen(event_time, event_name, event_json, event)

    @APITime
    def destroy(self) -> None:
        if self.IRTCRoom:
            log.info(f'will destroy IRTCRoom=0x{self.IRTCRoom:X}')
            self.dll.byte_RTCRoom_destroy(self.pIRTCRoom)
        self.IRTCRoom = 0
        self.pIRTCRoom = None
        if self.IRTCRoomEventHandler:
            self.dll.byte_deleteRTCRoomEventHandler(self.pIRTCRoomEventHandler)
            self.IRTCRoomEventHandler = 0
            self.pIRTCRoomEventHandler = None

    @APITime
    def setRTCRoomEventHandler(self, event_handler: IRTCRoomEventHandler) -> None:
        self.roomEventHandler = event_handler

    @APITime
    def joinRoom(self, token: str, user_info: UserInfo, room_config: RTCRoomConfig) -> int:
        if not self.pIRTCRoom:
            return
        ret = self.dll.byte_RTCRoom_joinRoom(self.pIRTCRoom, token.encode(),
                                             ctypes.byref(user_info.toStruct()),
                                             ctypes.byref(room_config.toStruct()))
        return ret

    @APITime
    def leaveRoom(self) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_leaveRoom(self.pIRTCRoom)

    @APITime
    def publishStream(self, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_publishStream(self.pIRTCRoom, stream_type)

    @APITime
    def unpublishStream(self, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_unpublishStream(self.pIRTCRoom, stream_type)

    @APITime
    def publishScreen(self, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_publishScreen(self.pIRTCRoom, stream_type)

    @APITime
    def unpublishScreen(self, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_unpublishScreen(self.pIRTCRoom, stream_type)

    def __modifyEventIfHasEnum(self, event_name: str, event: dict) -> None:
        if event_name == 'onLocalStreamStats':
            event['stats']['local_rx_quality'] = NetworkQuality(event['stats']['local_rx_quality'])
            event['stats']['local_tx_quality'] = NetworkQuality(event['stats']['local_tx_quality'])
            event['stats']['video_stats']['codec_type'] = VideoCodecType(event['stats']['video_stats']['codec_type'])
        if event_name == 'onRemoteStreamStats':
            event['stats']['remote_rx_quality'] = NetworkQuality(event['stats']['remote_rx_quality'])
            event['stats']['remote_tx_quality'] = NetworkQuality(event['stats']['remote_tx_quality'])
        elif event_name == 'onUserLeave':
            event['reason'] = UserOfflineReason(event['reason'])
        elif event_name == 'onMuteAllRemoteAudio':
            event['mute_state'] = MuteState(event['mute_state'])
        elif event_name == 'onMuteAllRemoteVideo':
            event['mute_state'] = MuteState(event['mute_state'])
        elif event_name == 'onStreamRemove':
            event['reason'] = StreamRemoveReason(event['reason'])
            event['stream']['max_profile']['codec_mode'] = VideoCodecMode(event['stream']['max_profile']['codec_mode'])
            event['stream']['max_profile']['codec_name'] = VideoCodecType(event['stream']['max_profile']['codec_name'])
            event['stream']['max_profile']['encode_preference'] = VideoEncodePreference(event['stream']['max_profile']['encode_preference'])
            event['stream']['max_profile']['scale_mode'] = VideoStreamScaleMode(event['stream']['max_profile']['scale_mode'])
            for i in range(event['stream']['profile_count']):
                event['stream']['profiles'][i]['codec_mode'] = VideoCodecMode(event['stream']['profiles'][i]['codec_mode'])
                event['stream']['profiles'][i]['codec_name'] = VideoCodecType(event['stream']['profiles'][i]['codec_name'])
                event['stream']['profiles'][i]['encode_preference'] = VideoEncodePreference(event['stream']['profiles'][i]['encode_preference'])
                event['stream']['profiles'][i]['scale_mode'] = VideoStreamScaleMode(event['stream']['profiles'][i]['scale_mode'])
        elif event_name == 'onStreamAdd':
            event['stream']['max_profile']['codec_mode'] = VideoCodecMode(event['stream']['max_profile']['codec_mode'])
            event['stream']['max_profile']['codec_name'] = VideoCodecType(event['stream']['max_profile']['codec_name'])
            event['stream']['max_profile']['encode_preference'] = VideoEncodePreference(event['stream']['max_profile']['encode_preference'])
            event['stream']['max_profile']['scale_mode'] = VideoStreamScaleMode(event['stream']['max_profile']['scale_mode'])
            for i in range(event['stream']['profile_count']):
                event['stream']['profiles'][i]['codec_mode'] = VideoCodecMode(event['stream']['profiles'][i]['codec_mode'])
                event['stream']['profiles'][i]['codec_name'] = VideoCodecType(event['stream']['profiles'][i]['codec_name'])
                event['stream']['profiles'][i]['encode_preference'] = VideoEncodePreference(event['stream']['profiles'][i]['encode_preference'])
                event['stream']['profiles'][i]['scale_mode'] = VideoStreamScaleMode(event['stream']['profiles'][i]['scale_mode'])
        elif event_name == 'onUserPublishStream':
            event['type'] = MediaStreamType(event['type'])
        elif event_name == 'onUserUnpublishStream':
            event['type'] = MediaStreamType(event['type'])
            event['reason'] = StreamRemoveReason(event['reason'])
        elif event_name == 'onUserPublishScreen':
            event['type'] = MediaStreamType(event['type'])
        elif event_name == 'onUserUnpublishScreen':
            event['type'] = MediaStreamType(event['type'])
            event['reason'] = StreamRemoveReason(event['reason'])
        elif event_name == 'onStreamSubscribed':
            event['state_code'] = SubscribeState(event['state_code'])
        elif event_name == 'onRoomModeChanged':
            event['mode'] = RtcRoomMode(event['mode'])
        elif event_name == 'onAVSyncStateChange':
            event['state'] = AVSyncState(event['state'])
        elif event_name == 'onForwardStreamStateChanged':
            for i in range(event['info_count']):
                event['infos'][i]['error'] = ForwardStreamError(event['infos'][i]['error'])
                event['infos'][i]['state'] = ForwardStreamState(event['infos'][i]['state'])
        elif event_name == 'onForwardStreamEvent':
            for i in range(event['info_count']):
                event['infos'][i]['event'] = ForwardStreamEvent(event['infos'][i]['event'])
        elif event_name == 'onNetworkQuality':
            event['local_quality']['rx_quality'] = NetworkQuality(event['local_quality']['rx_quality'])
            event['local_quality']['tx_quality'] = NetworkQuality(event['local_quality']['tx_quality'])
            for i in range(event['remote_qualities_num']):
                event['remote_qualities'][i]['rx_quality'] = ForwardStreamEvent(event['remote_qualities'][i]['rx_quality'])
                event['remote_qualities'][i]['tx_quality'] = ForwardStreamEvent(event['remote_qualities'][i]['tx_quality'])


class VideoDeviceManager:
    def __init__(self, ptr: int):
        self.dll = _DllClient.instance().dll
        self.cptr = ctypes.c_void_p(ptr)

    @ APITime
    def getVideoCaptureDevice(self) -> [str, int]:
        '''return (deviceId, result)'''
        arrayType = ctypes.c_char * DEVICE_ID_LENGTH
        deviceId = arrayType()
        ret = self.dll.byte_IVideoDeviceManager_getVideoCaptureDevice(self.cptr, deviceId)
        return deviceId.value.decode(), ret

    @ APITime
    def setVideoCaptureDevice(self, device_id: str) -> int:
        ret = self.dll.byte_IVideoDeviceManager_setVideoCaptureDevice(self.cptr, device_id.encode())
        return ret

    @ APITime
    def getDeviceList(self) -> List[Tuple[str, str]]:
        '''return a list of (deviceName, deviceId)'''
        vdcPtr = self.dll.byte_IVideoDeviceManager_enumerateVideoCaptureDevices(self.cptr)
        if vdcPtr == 0:
            return []
        cvdcPtr = ctypes.c_void_p(vdcPtr)
        count = self.dll.byte_IVideoDeviceCollection_getCount(cvdcPtr)
        deviceList = []
        arrayType = ctypes.c_char * DEVICE_ID_LENGTH
        for i in range(count):
            deviceName = arrayType()
            deviceId = arrayType()
            ret = self.dll.byte_IVideoDeviceCollection_getDevice(cvdcPtr, i, deviceName, deviceId)
            if ret == 0:
                deviceList.append((deviceName.value.decode(), deviceId.value.decode()))
        self.dll.byte_IVideoDeviceCollection_release(cvdcPtr)
        cvdcPtr = None
        return deviceList

    @ APITime
    def getDeviceInfoList(self) -> List[VideoDeviceInfo]:
        vdcPtr = self.dll.byte_IVideoDeviceManager_enumerateVideoCaptureDevices(self.cptr)
        if vdcPtr == 0:
            return []
        cvdcPtr = ctypes.c_void_p(vdcPtr)
        count = self.dll.byte_IVideoDeviceCollection_getCount(cvdcPtr)
        deviceList = []
        for i in range(count):
            sVideoDeviceInfo = StructVideoDeviceInfo()
            ret = self.dll.byte_IVideoDeviceCollection_getDeviceInfo(cvdcPtr, i, ctypes.byref(sVideoDeviceInfo))
            if ret == 0:
                videoDeviceInfo = VideoDeviceInfo()
                videoDeviceInfo.device_id = sVideoDeviceInfo.device_id.decode()
                videoDeviceInfo.device_name = sVideoDeviceInfo.device_name.decode()
                videoDeviceInfo.device_pid = sVideoDeviceInfo.device_pid
                videoDeviceInfo.device_vid = sVideoDeviceInfo.device_vid
                videoDeviceInfo.transport_type = DeviceTransportType(sVideoDeviceInfo.transport_type)
                deviceList.append(videoDeviceInfo)
        self.dll.byte_IVideoDeviceCollection_release(cvdcPtr)
        cvdcPtr = None
        return deviceList


class RTCVideo:
    def __init__(self, app_id: str, event_handler: IRTCVideoEventHandler = None, parameters: str = ''):
        if not app_id:
            self.IRTCVideo = 0
            return
        self.dll = _DllClient.instance().dll
        self.videoEventHandler = event_handler
        self.videoEventCFuncCallback = RTCEventCFuncCallback(self.RTCVideoEventCFuncCallback)
        self.IRTCVideoEventHandler = self.dll.byte_createRTCVideoEventHandler()
        self.pIRTCVideoEventHandler = ctypes.c_void_p(self.IRTCVideoEventHandler)
        self.dll.byte_RTCVideoEventHandler_setCallback(self.pIRTCVideoEventHandler, self.videoEventCFuncCallback)
        self.IRTCVideo = self.dll.byte_createRTCVideo(app_id.encode(), self.pIRTCVideoEventHandler, parameters.encode())
        self.pIRTCVideo = ctypes.c_void_p(self.IRTCVideo)
        self.version = getVersion()
        lineLen = 60
        log.info('\n\n{0}\n|{1:^{middleLen}}|\n{0}\n'.format(
            '-' * lineLen, f'Byte RTC SDK Version: {self.version}', middleLen=lineLen - 2))
        self.rooms = {}

    def __del__(self):
        self.destroy()

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(id=0x{id(self):X}, IRTCVideo=0x{self.IRTCVideo:X} version={self.version})'

    def RTCVideoEventCFuncCallback(self, event_handler: int, event_time: int, event_name: bytes, event_json: bytes) -> None:
        event_name = event_name.decode()
        event_json = event_json.decode()
        event = json.loads(event_json)
        self.__modifyEventIfHasEnum(event_name, event)
        if self.videoEventHandler:
            self.videoEventHandler.onRTCVideoEventHappen(event_time, event_name, event_json, event)

    @ APITime
    def destroy(self) -> None:
        if self.rooms:
            for roomId in list(self.rooms.keys()):
                del self.rooms[roomId]
            self.rooms.clear()
        if self.IRTCVideo:
            log.info(f'will destroy IRTCVideo=0x{self.IRTCVideo:X}')
            self.dll.byte_destroyRTCVideo()
            self.IRTCVideo = 0
            self.pIRTCVideo = None
        if self.IRTCVideoEventHandler:
            self.dll.byte_deleteRTCVideoEventHandler(self.pIRTCVideoEventHandler)
            self.IRTCVideoEventHandler = 0
            self.pIRTCVideoEventHandler = None

    @ APITime
    def setLocalVideoCanvas(self, index: StreamIndex, canvas: VideoCanvas) -> int:
        if not self.pIRTCVideo:
            return
        ret = self.dll.byte_RTCVideo_setLocalVideoCanvas(self.pIRTCVideo, index, ctypes.byref(canvas.toStruct()))
        return ret

    @ APITime
    def setRemoteStreamVideoCanvas(self, stream_key: RemoteStreamKey, canvas: VideoCanvas) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_setRemoteStreamVideoCanvas(self.pIRTCVideo, ctypes.byref(stream_key.toStruct()),
                                                          ctypes.byref(canvas.toStruct()))

    @ APITime
    def setVideoEncoderConfig(self, index: StreamIndex, solutions: List[VideoSolution]) -> int:
        if not self.pIRTCVideo:
            return
        arrayType = StructVideoSolution * len(solutions)
        cSolutions = arrayType()
        for i, solu in enumerate(solutions):
            cSolutions[i] = solu.toStruct()
        ret = self.dll.byte_RTCVideo_setVideoEncoderConfig(self.pIRTCVideo, index, cSolutions, len(solutions))
        return ret

    @ APITime
    def getVideoDeviceManager(self) -> VideoDeviceManager:
        if not self.pIRTCVideo:
            return
        vdm = self.dll.byte_RTCVideo_getVideoDeviceManager(self.pIRTCVideo)
        if vdm:
            return VideoDeviceManager(vdm)

    @ APITime
    def startVideoCapture(self) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_startVideoCapture(self.pIRTCVideo)

    @ APITime
    def stopVideoCapture(self) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_stopVideoCapture(self.pIRTCVideo)

    @ APITime
    def startScreenCapture(self, type_: ScreenMediaType, context: int) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_startScreenCapture(self.pIRTCVideo, type_, ctypes.c_void_p(context))

    @ APITime
    def startScreenCapture2(self, type_: ScreenMediaType, bundle_id: str) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_startScreenCapture2(self.pIRTCVideo, type_, bundle_id.encode())

    @ APITime
    def getScreenCaptureSourceList(self) -> List[ScreenCaptureSourceInfo]:
        if not self.pIRTCVideo:
            return
        sourceList = self.dll.byte_RTCVideo_getScreenCaptureSourceList(self.pIRTCVideo)
        pSourceList = ctypes.c_void_p(sourceList)
        sourceCount = self.dll.byte_IScreenCaptureSourceList_getCount(pSourceList)
        screenCaptureSourceList = []
        for i in range(sourceCount):
            sSourceInfo = StructScreenCaptureSourceInfo()
            self.dll.byte_IScreenCaptureSourceList_getSourceInfo(pSourceList, ctypes.byref(sSourceInfo), i)
            sourceInfo = ScreenCaptureSourceInfo()
            sourceInfo.application = sSourceInfo.application.decode() if sSourceInfo.application else ''
            sourceInfo.pid = sSourceInfo.pid
            sourceInfo.primaryMonitor = sSourceInfo.primaryMonitor
            sourceInfo.region_rect = Rectangle(x=sourceInfo.region_rect.x, y=sourceInfo.region_rect.y,
                                               width=sourceInfo.region_rect.width, height=sourceInfo.region_rect.height)
            sourceInfo.source_id = sSourceInfo.source_id
            sourceInfo.source_name = sSourceInfo.source_name.decode() if sSourceInfo.source_name else ''
            sourceInfo.type = ScreenCaptureSourceType(sSourceInfo.type)
            screenCaptureSourceList.append(sourceInfo)
        self.dll.byte_IScreenCaptureSourceList_release(pSourceList)
        return screenCaptureSourceList

    @ APITime
    def startScreenVideoCapture(self, source_info: ScreenCaptureSourceInfo, capture_params: ScreenCaptureParameters) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_startScreenVideoCapture(self.pIRTCVideo, ctypes.byref(source_info.toStruct()), ctypes.byref(capture_params.toStruct()))

    @ APITime
    def stopScreenVideoCapture(self) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_stopScreenVideoCapture(self.pIRTCVideo)

    @ APITime
    def startAudioCapture(self) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_startAudioCapture(self.pIRTCVideo)

    @ APITime
    def stopAudioCapture(self) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_stopAudioCapture(self.pIRTCVideo)

    @ APITime
    def createRTCRoom(self, room_id: str) -> RTCRoom:
        if not self.pIRTCVideo:
            return
        IRTCRoom = self.dll.byte_RTCVideo_createRTCRoom(self.pIRTCVideo, room_id.encode())
        if IRTCRoom:
            if room_id in self.rooms:
                log.info(f'createRTCRoom room_id={room_id} many times')
                rtcRoom = self.rooms[room_id]
                if IRTCRoom != rtcRoom.IRTCRoom:
                    oldRoom = rtcRoom
                    # oldRoom.destroy()
                    rtcRoom = RTCRoom(room_id=room_id, IRTCRoom=IRTCRoom)
                    self.rooms[room_id] = rtcRoom
            else:
                rtcRoom = RTCRoom(room_id=room_id, IRTCRoom=IRTCRoom)
                self.rooms[room_id] = rtcRoom
            return rtcRoom
        else:
            pass

    def __modifyEventIfHasEnum(self, event_name: str, event: dict) -> None:
        if event_name == 'onConnectionStateChanged':
            event['state'] = ConnectionState(event['state'])
        elif event_name == 'onNetworkTypeChanged':
            event['type'] = NetworkType(event['type'])
        elif event_name == 'onPerformanceAlarms':
            event['mode'] = PerformanceAlarmMode(event['mode'])
            event['reason'] = PerformanceAlarmReason(event['reason'])
        elif event_name == 'onMediaDeviceStateChanged':
            event['device_type'] = MediaDeviceType(event['device_type'])
            event['device_state'] = MediaDeviceState(event['device_state'])
            event['device_error'] = MediaDeviceError(event['device_error'])
        elif event_name == 'onAudioDeviceStateChanged':
            event['device_type'] = AudioDeviceType(event['device_type'])
            event['device_state'] = MediaDeviceState(event['device_state'])
            event['device_error'] = MediaDeviceError(event['device_error'])
        elif event_name == 'onVideoDeviceStateChanged':
            event['device_type'] = VideoDeviceType(event['device_type'])
            event['device_state'] = MediaDeviceState(event['device_state'])
            event['device_error'] = MediaDeviceError(event['device_error'])
        elif event_name == 'onMediaDeviceWarning':
            event['device_type'] = MediaDeviceType(event['device_type'])
            event['device_warning'] = MediaDeviceWarning(event['device_warning'])
        elif event_name == 'onAudioDeviceWarning':
            event['device_type'] = AudioDeviceType(event['device_type'])
            event['device_warning'] = MediaDeviceWarning(event['device_warning'])
        elif event_name == 'onVideoDeviceWarning':
            event['device_type'] = VideoDeviceType(event['device_type'])
            event['device_warning'] = MediaDeviceWarning(event['device_warning'])
        elif event_name == 'onHttpProxyState':
            event['state'] = HttpProxyState(event['state'])
        elif event_name == 'onHttpsProxyState':
            event['state'] = HttpProxyState(event['state'])
        elif event_name == 'onSocks5ProxyState':
            event['state'] = Socks5ProxyState(event['state'])
        elif event_name == 'onRecordingStateUpdate':
            event['index'] = StreamIndex(event['index'])
            event['state'] = RecordingState(event['state'])
            event['error_code'] = RecordingErrorCode(event['error_code'])
            event['info']['video_codec_type'] = VideoCodecType(event['info']['video_codec_type'])
        elif event_name == 'onRecordingProgressUpdate':
            event['index'] = StreamIndex(event['index'])
            event['info']['video_codec_type'] = VideoCodecType(event['info']['video_codec_type'])
        elif event_name == 'onSEIStreamUpdate':
            event['type'] = SEIStreamEventType(event['type'])
        elif event_name == 'onLocalAudioStateChanged':
            event['state'] = LocalAudioStreamState(event['state'])
            event['error'] = LocalAudioStreamError(event['error'])
        elif event_name == 'onStreamSyncInfoReceived':
            event['stream_type'] = SyncInfoStreamType(event['stream_type'])
        elif event_name == 'onNetworkDetectionResult':
            event['type'] = NetworkDetectionLinkType(event['type'])
            event['quality'] = NetworkQuality(event['quality'])
        elif event_name == 'onNetworkDetectionStopped':
            event['reason'] = NetworkDetectionLinkType(event['reason'])
        elif event_name == 'onLocalVideoSizeChanged':
            event['index'] = StreamIndex(event['index'])
        elif event_name == 'onFirstLocalVideoFrameCaptured':
            event['index'] = StreamIndex(event['index'])
        elif event_name == 'onUserMuteAudio':
            event['mute_state'] = StreamIndex(event['mute_state'])
        elif event_name == 'onUserMuteVideo':
            event['mute'] = StreamIndex(event['mute'])
        elif event_name == 'onRemoteAudioStateChanged':
            event['state'] = RemoteAudioState(event['state'])
            event['reason'] = RemoteAudioStateChangeReason(event['reason'])
        elif event_name == 'onLocalVideoStateChanged':
            event['index'] = StreamIndex(event['index'])
            event['state'] = LocalVideoStreamState(event['state'])
            event['error'] = LocalVideoStreamError(event['error'])
        elif event_name == 'onRemoteVideoStateChanged':
            event['key']['stream_index'] = StreamIndex(event['key']['stream_index'])
            event['state'] = RemoteVideoState(event['state'])
            event['reason'] = RemoteVideoStateChangeReason(event['reason'])
        elif event_name == 'onAudioFrameSendStateChanged':
            event['state'] = FirstFrameSendState(event['state'])
        elif event_name == 'onVideoFrameSendStateChanged':
            event['state'] = FirstFrameSendState(event['state'])
        elif event_name == 'onScreenVideoFrameSendStateChanged':
            event['state'] = FirstFrameSendState(event['state'])
        elif event_name == 'onAudioFramePlayStateChanged':
            event['state'] = FirstFramePlayState(event['state'])
        elif event_name == 'onVideoFramePlayStateChanged':
            event['state'] = FirstFramePlayState(event['state'])
        elif event_name == 'onScreenVideoFramePlayStateChanged':
            event['state'] = FirstFramePlayState(event['state'])
        elif event_name == 'onFirstLocalAudioFrame':
            event['index'] = StreamIndex(event['index'])
        elif event_name == 'onEchoTestResult':
            event['result'] = StreamIndex(event['result'])


if __name__ == '__main__':
    print('bytertcsdk')
