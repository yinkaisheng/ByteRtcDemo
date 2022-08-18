#!python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import ctypes
import pprint
import threading
import subprocess
from bytertcsdk import bytertcsdk as sdk
import util
sys.path.append('../automation')
from uiautomation import uiautomation as auto

AppId = '62e52104c0700a038dd110cc'
RoomId = 'sdktest'
UserIdDict = {
    'yks1': '00162e52104c0700a038dd110ccQQCeaqwFI9f0YqMR/mIHAHNka3Rlc3QEAHlrczEGAAAAoxH+YgEAoxH+YgIAoxH+YgMAoxH+YgQAoxH+YgUAoxH+YiAAQUQ/j0j81ufAWBUS6DlR5u5Nn1kkIlbXtURq12s3rgI=',
    'yks2': '00162e52104c0700a038dd110ccQQANWg4CR9f0YscR/mIHAHNka3Rlc3QEAHlrczIGAAAAxxH+YgEAxxH+YgIAxxH+YgMAxxH+YgQAxxH+YgUAxxH+YiAAdddXe3ChDksV8/BBsgKDP3TAmuMTe6pvsGSPZ4L0jGk=',
    'yinkaisheng': '00162e52104c0700a038dd110ccSAA4ZlYCgw37YgNIBGMHAHNka3Rlc3QLAHlpbmthaXNoZW5nBgAAAANIBGMBAANIBGMCAANIBGMDAANIBGMEAANIBGMFAANIBGMgAK+35d0UnwTypbx2DcAI4fEf/aARa7ygQKrp7L8Ph8OY',
}
UserId = 'yks1'
Token = UserIdDict[UserId]

_ConnectedEvent = threading.Event()


class RTCRoomEventHandler:
    def onRTCRoomEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        sdk.log.info(f'{event_name} \n{pprint.pformat(event, indent=2, width=120, compact=True, sort_dicts=False)}')
        pass


class RTCVideoEventHandler:
    def onRTCVideoEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        sdk.log.info(f'{event_name} \n{pprint.pformat(event, indent=2, width=120, compact=True, sort_dicts=False)}')
        if event_name == 'onConnectionStateChanged':
            if event['state'] == sdk.ConnectionState.Connected:
                _ConnectedEvent.set()


def getViewHandle() -> int:
    controlPan = auto.WindowControl(searchDepth=1, ClassName='CabinetWClass', SubName='控制面板')
    handle = 0
    if not controlPan.Exists(0, 0):
        subprocess.Popen('control')
        if controlPan.Exists(2, 0.5):
            handle = controlPan.NativeWindowHandle
        else:
            print('open control failed')
    else:
        controlPan.SetActive()
        handle = controlPan.NativeWindowHandle
    return handle


def main(isCameraCapture: bool = True):
    choices = {}
    index = 0
    for filePath, isDir, fileName, depth, remainCount in util.walkDir('bytertcsdk', maxDepth=1):
        if isDir and fileName.startswith('binx'):
            index += 1
            choices[index] = fileName
    tip = '\n'.join(f'{k}: {v}' for k, v in choices.items()) + f'\nselect: '
    ret = input(tip)
    select = int(ret)
    adir = choices[select]
    sdk.chooseSdkBinDir(adir)

    if adir.endswith('dev'):
        os.add_dll_directory(r'C:\Users\Admin\Codes\CPP\ByteRTC\build_win\Debug')

    videoEventHandler = RTCVideoEventHandler()
    rtcVideo = sdk.RTCVideo(app_id=AppId, event_handler=videoEventHandler)
    print(rtcVideo)

    _ConnectedEvent.wait(0xFFFF)

    rtcVideo.startAudioCapture()
    vdm = rtcVideo.getVideoDeviceManager()
    if vdm:
        vdm.getDeviceList()
        vdm.getDeviceInfoList()

    localCanvas = sdk.VideoCanvas(view=getViewHandle(), render_mode=sdk.RenderMode.Hidden, background_color=0x000000)
    videoSolu = sdk.VideoSolution()
    if isCameraCapture:
        rtcVideo.setLocalVideoCanvas(sdk.StreamIndex.Main, localCanvas)
        videoSolu.width = 640
        videoSolu.height = 360
        videoSolu.fps = 15
        videoSolu.max_send_kbps = 1000
        rtcVideo.setVideoEncoderConfig(sdk.StreamIndex.Main, [videoSolu])
        rtcVideo.startVideoCapture()
    else:
        rtcVideo.setLocalVideoCanvas(sdk.StreamIndex.Screen, localCanvas)
        videoSolu.width = 1920
        videoSolu.height = 1080
        videoSolu.fps = 15
        videoSolu.max_send_kbps = 2000
        rtcVideo.setVideoEncoderConfigSolutions(sdk.StreamIndex.Screen, [videoSolu])
        sourceList = rtcVideo.getScreenCaptureSourceList()
        for sourceInfo in sourceList:
            sdk.log.info(f'{sourceInfo.pid}, {sourceInfo.application}, {sourceInfo.source_name}')
        if sourceList:
            sourceInfo = sourceList[0]
            captureParams = sdk.ScreenCaptureParameters()
            #captureParams.region_rect = sdk.Rectangle(x=0, y=0, width=1920, height=1080)
            rtcVideo.setVideoEncoderConfigSolutions(source_info=sourceInfo, capture_params=captureParams)
    rtcRoom = rtcVideo.createRTCRoom(room_id=RoomId)
    roomEventHandler = RTCRoomEventHandler()
    rtcRoom.setRTCRoomEventHandler(roomEventHandler)
    userInfo = sdk.UserInfo(UserId, extra_info='{"extra_info_key": "HelloWorld"}')
    roomConfig = sdk.RTCRoomConfig()
    roomConfig.room_profile_type = sdk.RoomProfileType.LiveBroadcasting
    roomConfig.is_auto_publish = True
    roomConfig.is_auto_subscribe_audio = True
    roomConfig.is_auto_subscribe_video = True
    #roomConfig.remote_video_config.framerate = 15
    #roomConfig.remote_video_config.resolution_width = 640
    #roomConfig.remote_video_config.resolution_height = 360
    rtcRoom.joinRoom(token=Token, user_info=userInfo, room_config=roomConfig)
    if isCameraCapture:
        rtcRoom.publishStream(sdk.MediaStreamType.Both)
    else:
        rtcRoom.publishScreen(sdk.MediaStreamType.Both)

    #crash begins
    input('----\npaused\n----')
    rtcVideo.dll.byte_deleteRTCVideoEventHandler(rtcVideo.pIRTCVideoEventHandler)
    rtcVideo.pIRTCVideoEventHandler = 0
    rtcVideo.IRTCVideoEventHandler = 0
    #crash ends    input('----\npaused\n----')

    rtcRoom.leaveRoom()
    time.sleep(0.5)
    rtcVideo.stopAudioCapture()
    if isCameraCapture:
        rtcVideo.stopVideoCapture()
    else:
        rtcVideo.stopScreenVideoCapture()
    rtcRoom.destroy()
    rtcVideo.destroy()
    #del rtcRoom
    #del rtcVideo


if __name__ == '__main__':
    isCameraCapture = 1
    if len(sys.argv) > 1 and sys.argv[1] == '0':
        isCameraCapture = 0
    main(isCameraCapture)


