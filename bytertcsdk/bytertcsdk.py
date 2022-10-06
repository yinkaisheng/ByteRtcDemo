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
SdkBinDir = ''  # binx86_3.45.104
SdkBinDirFull = ''  # d:\Codes\Python\ByteRtcDemo\bytertcsdk\binx86_3.43.102
SdkDllName = 'VolcEngineRTC.dll'
SdkVersion = ''  # '3.45.104' get from folder name
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
        if '.' in func.__qualname__:
            logArgs = args[1:]  #class method, exclude self
        else:
            logArgs = args
        argsstr = ', '.join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in logArgs)
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


def ElapsedTime(runTimes=1):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            #argstr = ','.join(str(arg) for arg in args)
            #kwstr = ','.join('{}={}'.format(k, v) for k, v in kwargs.items())
            #instr = ','.join(s for s in (argstr, kwstr) if s)
            instr = ''
            print(f'call {Fore.Cyan}{func.__name__}({instr})')
            start = time.monotonic()
            for i in range(runTimes):
                ret = func(*args, **kwargs)
            end = time.monotonic()
            total = end - start
            avg = total / runTimes
            print(
                f'{Fore.Cyan}{func.__name__}{Fore.Reset} run times {Fore.DarkGreen}{runTimes}{Fore.Reset}'
                f', cost {Fore.DarkGreen}{total:.6f}{Fore.Reset}s, avg cost {Fore.DarkGreen}{avg:.6f}{Fore.Reset}s\n')
            return ret
        return wrapper
    return inner


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
            self.dll.byte_buildVideoFrame.restype = ctypes.c_void_p
            self.dll.byte_IVideoFrame_getPlaneData.restype = ctypes.c_void_p
            self.dll.byte_RTCRoom_sendRoomMessage.restype = ctypes.c_int64
            self.dll.byte_RTCRoom_sendRoomBinaryMessage.restype = ctypes.c_int64
            self.dll.byte_RTCRoom_sendUserMessage.restype = ctypes.c_int64
            self.dll.byte_RTCRoom_sendUserBinaryMessage.restype = ctypes.c_int64
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


class Env(MyIntEnum):
    Product = 0,
    BOE = 1
    Test = 2


@ APITime
def setEnv(env: Env) -> int:
    ret = _DllClient.instance().dll.byte_setEnv(env)
    return ret


@ APITime
def getVersion() -> str:
    version = _DllClient.instance().dll.byte_getSDKVersion()
    return version.decode()


@ APITime
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


class VideoSuperResolutionMode(MyIntEnum):
    Off = 0
    On = 1


class VideoSuperResolutionModeChangedReason(MyIntEnum):
    APIOff = 0
    APIOn = 1
    ResolutionExceed = 2
    OverUse = 3
    DeviceNotSupport = 4
    DynamicClose = 5
    OtherSettingDisabled = 6
    OtherSettingEnabled = 7
    NoComponent = 100
    StreamNotExist = 101


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


class CapturePreference(MyIntEnum):
    Auto = 0
    Manual = 1
    AutoPerformance = 2


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


class MessageConfig(MyIntEnum):
    ReliableOrdered = 0
    UnreliableOrdered = 1
    UnreliableUnordered = 2


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


class VideoSourceType(MyIntEnum):
    External = 0
    Internal = 1
    EncodedWithAutoSimulcast = 2
    EncodedWithoutAutoSimulcast = 3


class VideoFrameType(MyIntEnum):
    RawMemory = 0
    CVPixelBuffer = 1
    GLTexture = 2
    Cuda = 3
    D3D11 = 4
    D3D9 = 5
    JavaFrame = 6
    VAAPI = 7


class VideoPixelFormat(MyIntEnum):
    Unknown = 0
    I420 = 1
    NV12 = 2
    NV21 = 3
    RGB24 = 4
    RGBA = 5
    ARGB = 6
    BGRA = 7
    Texture2D = 0x0DE1
    TextureOES = 0x8D65


class PublicStreamErrorCode(MyIntEnum):
    OK = 0
    PushInvalidParam = 1191
    PushInvalidStatus = 1192
    PushInternalError = 1193
    PushFailed = 1195
    PushTimeout = 1196


class SEIMessageSourceType(MyIntEnum):
    Default = 0
    System = 1


class AudioDumpStatus(MyIntEnum):
    StartFailure = 0
    StartSuccess = 1
    StopFailure = 2
    StopSuccess = 3
    RunningFailure = 4
    RunningSuccess = 5


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


class StructVideoCaptureConfig(ctypes.Structure):
    _fields_ = [("capturePreference", ctypes.c_int),
                ("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("frameRate", ctypes.c_int),
                ]


class VideoCaptureConfig:
    def __init__(self, capturePreference: CapturePreference = CapturePreference.Auto, width: int = 0, height: int = 0, frameRate: int = 0):
        self.capturePreference = capturePreference
        self.width = width
        self.height = height
        self.frameRate = frameRate

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(capturePreference={self.capturePreference}, width={self.width}, height={self.height}, frameRate={self.frameRate}'

    __repr__ = __str__

    def toStruct(self) -> StructVideoCaptureConfig:
        sVideoCaptureConfig = StructVideoCaptureConfig()
        sVideoCaptureConfig.capturePreference = self.capturePreference
        sVideoCaptureConfig.width = self.width
        sVideoCaptureConfig.height = self.height
        sVideoCaptureConfig.frameRate = self.frameRate
        return sVideoCaptureConfig


class StructVideoEncoderConfig(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("frameRate", ctypes.c_int),
                ("maxBitrate", ctypes.c_int),
                ("encoderPreference", ctypes.c_int),
                ]


class VideoEncoderConfig:
    def __init__(self, width: int = 0, height: int = 0, frameRate: int = 0, maxBitrate: int = -1, encoderPreference: VideoEncodePreference = VideoEncodePreference.Framerate):
        self.width = width
        self.height = height
        self.frameRate = frameRate
        self.maxBitrate = maxBitrate
        self.encoderPreference = encoderPreference

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(width={self.width}, height={self.height}, frameRate={self.frameRate}, maxBitrate={self.maxBitrate}'    \
               f', encoderPreference={self.encoderPreference}, '

    __repr__ = __str__

    def toStruct(self) -> StructVideoEncoderConfig:
        sVideoEncoderConfig = StructVideoEncoderConfig()
        sVideoEncoderConfig.width = self.width
        sVideoEncoderConfig.height = self.height
        sVideoEncoderConfig.frameRate = self.frameRate
        sVideoEncoderConfig.maxBitrate = self.maxBitrate
        sVideoEncoderConfig.encoderPreference = self.encoderPreference
        return sVideoEncoderConfig


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

    # def toStruct(self) -> StructVideoDeviceInfo:


class StructCloudProxyInfo(ctypes.Structure):
    _fields_ = [("cloud_proxy_ip", ctypes.c_char_p),
                ("cloud_proxy_port", ctypes.c_int),
                ]


class StructCloudProxyConfiguration(ctypes.Structure):
    _fields_ = [("cloud_proxies", ctypes.POINTER(StructCloudProxyInfo)),
                ("cloud_proxy_count", ctypes.c_int),
                ]


class StructCloudProxyConfiguration(ctypes.Structure):
    _fields_ = [("cloud_proxies", ctypes.POINTER(StructCloudProxyInfo)),
                ("cloud_proxy_count", ctypes.c_int),
                ]


class StructVideoFrameBuilder(ctypes.Structure):
    _fields_ = [("frame_type", ctypes.c_int),
                ("pixel_fmt", ctypes.c_int),
                ("color_space", ctypes.c_int),
                ("data", ctypes.c_void_p * 4),
                ("linesize", ctypes.c_int * 4),
                ("extra_data", ctypes.c_void_p),
                ("extra_data_size", ctypes.c_int),
                ("supplementary_info", ctypes.c_void_p),
                ("supplementary_info_size", ctypes.c_int),
                ("size", ctypes.c_int),
                ("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("rotation", ctypes.c_int),
                ("flip", ctypes.c_bool),
                ("hwaccel_buffer", ctypes.c_void_p),
                ("user_opaque", ctypes.c_void_p),
                ("timestamp_us", ctypes.c_int64),
                ("hwaccel_context", ctypes.c_void_p),
                ("tex_matrix", ctypes.c_float * 16),
                ("texture_id", ctypes.c_uint32),
                ("memory_deleter", ctypes.c_void_p),
                ]


class IVideoFrame:
    def __init__(self, frame: int):
        self.dll = _DllClient.instance().dll
        self.frame = frame
        self.pFrame = ctypes.c_void_p(frame)

    def __del__(self):
        self.release()

    def frameType(self) -> VideoFrameType:
        if self.pFrame:
            frameType = self.dll.byte_IVideoFrame_frameType(self.pFrame)
            return VideoFrameType(frameType)

    def pixelFormat(self) -> VideoPixelFormat:
        if self.pFrame:
            pixelFormat = self.dll.byte_IVideoFrame_pixelFormat(self.pFrame)
            return VideoPixelFormat(pixelFormat)

    def width(self) -> int:
        if self.pFrame:
            return self.dll.byte_IVideoFrame_width(self.pFrame)

    def height(self) -> int:
        if self.pFrame:
            return self.dll.byte_IVideoFrame_height(self.pFrame)

    def numberOfPlanes(self) -> int:
        if self.pFrame:
            return self.dll.byte_IVideoFrame_numberOfPlanes(self.pFrame)

    def getPlaneStride(self, plane_index: int) -> int:
        if self.pFrame:
            return self.dll.byte_IVideoFrame_getPlaneStride(self.pFrame, plane_index)

    def getPlaneData(self, plane_index: int) -> ctypes.c_void_p:
        if self.pFrame:
            ptrValue = self.dll.byte_IVideoFrame_getPlaneData(self.pFrame, plane_index)
            return ctypes.c_void_p(ptrValue)

    def release(self):
        if self.frame:
            self.dll.byte_IVideoFrame_release(self.pFrame)
            self.frame = 0
            self.pFrame = None


def buildVideoFrame(builder: StructVideoFrameBuilder) -> IVideoFrame:
    ptrValue = _DllClient.instance().dll.byte_buildVideoFrame(ctypes.byref(builder))
    if ptrValue:
        return IVideoFrame(ptrValue)


RTCEventCFuncCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_char_p)


class IRTCRoomEventHandler:
    def onRTCRoomEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        """
        event_time: micro seconds since epoch
        """
        print(f'{room_id} {event_name} {event_json}')


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

    @APITime
    def subscribeStream(self, user_id: str, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_subscribeStream(self.pIRTCRoom, user_id.encode(), stream_type)

    @APITime
    def unsubscribeStream(self, user_id: str, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_unsubscribeStream(self.pIRTCRoom, user_id.encode(), stream_type)

    @APITime
    def subscribeScreen(self, user_id: str, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_subscribeScreen(self.pIRTCRoom, user_id.encode(), stream_type)

    @APITime
    def unsubscribeScreen(self, user_id: str, stream_type: MediaStreamType) -> None:
        if not self.pIRTCRoom:
            return
        self.dll.byte_RTCRoom_unsubscribeScreen(self.pIRTCRoom, user_id.encode(), stream_type)

    @APITime
    def sendRoomMessage(self, message: str) -> None:
        if not self.pIRTCRoom:
            return
        ret = self.dll.byte_RTCRoom_sendRoomMessage(self.pIRTCRoom, message.encode())
        return ret

    @APITime
    def sendRoomBinaryMessage(self, message: bytes) -> None:
        if not self.pIRTCRoom:
            return
        ret = self.dll.byte_RTCRoom_sendRoomBinaryMessage(self.pIRTCRoom, message, len(message))
        return ret

    @APITime
    def sendUserMessage(self, user_id: str, message: str, config: MessageConfig) -> None:
        if not self.pIRTCRoom:
            return
        ret = self.dll.byte_RTCRoom_sendUserMessage(self.pIRTCRoom, user_id.encode(), message.encode(), config)
        return ret

    @APITime
    def sendUserBinaryMessage(self, user_id: str, message: bytes, config: MessageConfig) -> None:
        if not self.pIRTCRoom:
            return
        ret = self.dll.byte_RTCRoom_sendUserBinaryMessage(self.pIRTCRoom, user_id.encode(), message, len(message), config)
        return ret

    def __modifyEventIfHasEnum(self, event_name: str, event: dict) -> None:
        if event_name == 'onLocalStreamStats':
            event['stats']['local_rx_quality'] = NetworkQuality(event['stats']['local_rx_quality'])
            event['stats']['local_tx_quality'] = NetworkQuality(event['stats']['local_tx_quality'])
            event['stats']['video_stats']['codec_type'] = VideoCodecType(event['stats']['video_stats']['codec_type'])
        elif event_name == 'onRemoteStreamStats':
            event['stats']['remote_rx_quality'] = NetworkQuality(event['stats']['remote_rx_quality'])
            event['stats']['remote_tx_quality'] = NetworkQuality(event['stats']['remote_tx_quality'])
            if 'codec_type' in event['stats']['video_stats']:
                event['stats']['video_stats']['codec_type'] = VideoCodecType(event['stats']['video_stats']['codec_type'])
            if 'super_resolution_mode' in event['stats']['video_stats']:
                event['stats']['video_stats']['super_resolution_mode'] = VideoSuperResolutionMode(event['stats']['video_stats']['super_resolution_mode'])
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
    def startCloudProxy(self, proxies: List[Tuple[str, int]]) -> None:
        if not self.pIRTCVideo:
            return
        proxyArray = (StructCloudProxyInfo * len(proxies))(*(StructCloudProxyInfo(it[0].encode(), it[1]) for it in proxies))
        proxyConfig = StructCloudProxyConfiguration(proxyArray, len(proxies))
        self.dll.byte_RTCVideo_startCloudProxy(self.pIRTCVideo, ctypes.byref(proxyConfig))

    @ APITime
    def stopCloudProxy(self) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_stopCloudProxy(self.pIRTCVideo)

    @ APITime
    def setLocalVideoCanvas(self, index: StreamIndex, canvas: VideoCanvas) -> int:
        if not self.pIRTCVideo:
            return
        ret = self.dll.byte_RTCVideo_setLocalVideoCanvas(self.pIRTCVideo, index, ctypes.byref(canvas.toStruct()))
        return ret

    @ APITime
    def setRemoteVideoCanvas(self, stream_key: RemoteStreamKey, canvas: VideoCanvas) -> None:
        '''sdk version >= 3.47'''
        if not self.pIRTCVideo:
            return
        if SdkVersion < '3.47':
            log.error('does not support this API, use setRemoteStreamVideoCanvas')
            return
        self.dll.byte_RTCVideo_setRemoteVideoCanvas(self.pIRTCVideo, ctypes.byref(stream_key.toStruct()),
                                                    ctypes.byref(canvas.toStruct()))

    @ APITime
    def setRemoteStreamVideoCanvas(self, stream_key: RemoteStreamKey, canvas: VideoCanvas) -> None:
        '''sdk version < 3.47'''
        if not self.pIRTCVideo:
            return
        if SdkVersion >= '3.47':
            log.error('does not support this API, use setRemoteVideoCanvas')
            return
        self.dll.byte_RTCVideo_setRemoteStreamVideoCanvas(self.pIRTCVideo, ctypes.byref(stream_key.toStruct()),
                                                          ctypes.byref(canvas.toStruct()))

    @ APITime
    def setVideoCaptureConfig(self, capture_config: VideoCaptureConfig) -> int:
        if not self.pIRTCVideo:
            return
        ret = self.dll.byte_RTCVideo_setVideoCaptureConfig(self.pIRTCVideo, ctypes.byref(capture_config.toStruct()))
        return ret

    @ APITime
    def setVideoEncoderConfig(self, max_solution: VideoEncoderConfig) -> int:
        if not self.pIRTCVideo:
            return
        ret = self.dll.byte_RTCVideo_setVideoEncoderConfig(self.pIRTCVideo, ctypes.byref(max_solution.toStruct()))
        return ret

    @ APITime
    def setVideoEncoderConfigList(self, channel_solutions: List[VideoEncoderConfig]) -> int:
        if not self.pIRTCVideo:
            return
        arrayType = StructVideoEncoderConfig * len(channel_solutions)
        cConfigs = arrayType()
        for i, config in enumerate(channel_solutions):
            cConfigs[i] = config.toStruct()
        ret = self.dll.byte_RTCVideo_setVideoEncoderConfigList(self.pIRTCVideo, cConfigs, len(channel_solutions))
        return ret

    @ APITime
    def setVideoEncoderConfigSolutions(self, index: StreamIndex, solutions: List[VideoSolution]) -> int:
        if not self.pIRTCVideo:
            return
        arrayType = StructVideoSolution * len(solutions)
        cSolutions = arrayType()
        for i, solu in enumerate(solutions):
            cSolutions[i] = solu.toStruct()
        ret = self.dll.byte_RTCVideo_setVideoEncoderConfigSolutions(self.pIRTCVideo, index, cSolutions, len(solutions))
        return ret

    @APITime
    def enableSimulcastMode(self, enabled: bool):
        ret = None if SdkVersion >= '3.47' else -1
        if not self.pIRTCVideo:
            return ret
        if SdkVersion >= '3.47':
            self.dll.byte_RTCVideo_enableSimulcastMode(self.pIRTCVideo, int(enabled))
        else:
            ret = self.dll.byte_RTCVideo_enableSimulcastMode(self.pIRTCVideo, int(enabled))
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
    def takeLocalSnapshot(self, stream_index: StreamIndex) -> int:
        if not self.pIRTCVideo:
            return -1
        return self.dll.byte_RTCVideo_takeLocalSnapshot(self.pIRTCVideo, stream_index, self.pIRTCVideoEventHandler)

    @ APITime
    def takeRemoteSnapshot(self, stream_key: RemoteStreamKey) -> int:
        if not self.pIRTCVideo:
            return -1
        return self.dll.byte_RTCVideo_takeRemoteSnapshot(self.pIRTCVideo, ctypes.byref(stream_key.toStruct()), self.pIRTCVideoEventHandler)

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
    def setVideoSourceType(self, stream_index: StreamIndex, source_type: VideoSourceType) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_setVideoSourceType(self.pIRTCVideo, stream_index, source_type)

    @ APITime
    def setRemoteVideoSuperResolution(self, stream_key: RemoteStreamKey, mode: VideoSuperResolutionMode) -> None:
        if not self.pIRTCVideo:
            return
        if SdkVersion < '3.46':
            log.error('does not support this API')
            return -1
        ret = self.dll.byte_RTCVideo_setRemoteVideoSuperResolution(self.pIRTCVideo, ctypes.byref(stream_key.toStruct()), mode)
        return ret

    def pushExternalVideoFrame(self, frame: IVideoFrame) -> None:
        if not self.pIRTCVideo:
            return
        self.dll.byte_RTCVideo_pushExternalVideoFrame(self.pIRTCVideo, frame.pFrame)
        # frame.release() #do not call release, sdk will call it

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
        elif event_name == 'onRemoteVideoSuperResolutionModeChanged':
            event['stream_key']['stream_index'] = StreamIndex(event['stream_key']['stream_index'])
            event['mode'] = VideoSuperResolutionMode(event['mode'])
            event['reason'] = VideoSuperResolutionModeChangedReason(event['reason'])
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
            event['result'] = EchoTestResult(event['result'])
        elif event_name == 'onPlayPublicStreamResult':
            if SdkVersion >= '3.47':
                event['errorCode'] = PublicStreamErrorCode(event['errorCode'])
        elif event_name == 'onPushPublicStreamResult':
            if SdkVersion >= '3.47':
                event['errorCode'] = PublicStreamErrorCode(event['errorCode'])
        elif event_name == 'onPublicStreamSEIMessageReceived':
            if SdkVersion >= '3.47':
                event['source_type'] = SEIMessageSourceType(event['source_type'])
        elif event_name == 'onAudioDumpStateChanged':   # >=3.47
            event['status'] = AudioDumpStatus(event['status'])


if __name__ == '__main__':
    print('bytertcsdk')
