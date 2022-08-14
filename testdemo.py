#!python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import ctypes
import subprocess
from bytertcsdk import config
config.APILogPath = 'api_records.log'
from bytertcsdk import bytertcsdk as sdk
import util
sys.path.append('../automation')
from uiautomation import uiautomation as auto


class RTCRoomEventHandler:
    def onRoomEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        sdk.log.info(f'{event_name} {event}')
        pass


class RTCVideoEventHandler:
    def onVideoEventHappen(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
        sdk.log.info(f'{event_name} {event}')
        pass


def main(isCameraCapture: bool = True):
    if sys.stdout:
        input('----\npaused\n----')
    controlPan = auto.WindowControl(searchDepth=1, SubName='控制面板\\')
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
    sdk.chooseSdkBinDir('binx86_3.43.102')
    videoEventHandler = RTCVideoEventHandler()
    rtcVideo = sdk.RTCVideo(app_id='62e52104c0700a038dd110cc', event_handler=videoEventHandler)
    print(rtcVideo)
    time.sleep(1)

    # rtcVideo.startAudioCapture()
    localCanvas = sdk.VideoCanvas(view=handle, render_mode=sdk.RenderMode.Hidden, background_color=0x000000)
    videoSolu = sdk.VideoSolution()
    if isCameraCapture:
        rtcVideo.setLocalVideoCanvas(sdk.StreamIndex.Main, localCanvas)
        videoSolu.width = 640
        videoSolu.height = 360
        videoSolu.fps = 15
        videoSolu.max_send_kbps = 1000
        #rtcVideo.setVideoEncoderConfig(sdk.StreamIndex.Main, [videoSolu])
        rtcVideo.startVideoCapture()
    else:
        rtcVideo.setLocalVideoCanvas(sdk.StreamIndex.Screen, localCanvas)
        videoSolu.width = 1920
        videoSolu.height = 1080
        videoSolu.fps = 15
        videoSolu.max_send_kbps = 2000
        rtcVideo.setVideoEncoderConfig(sdk.StreamIndex.Screen, [videoSolu])
        sourceList = rtcVideo.getScreenCaptureSourceList()
        # for sourceInfo in sourceList:
            #sdk.log.info(f'{sourceInfo.pid}, {sourceInfo.application}, {sourceInfo.source_name}')
        if sourceList:
            sourceInfo = sourceList[0]
            captureParams = sdk.ScreenCaptureParameters()
            #captureParams.region_rect = sdk.Rectangle(x=0, y=0, width=1920, height=1080)
            rtcVideo.startScreenVideoCapture(source_info=sourceInfo, capture_params=captureParams)
    rtcRoom = rtcVideo.createRTCRoom(roomId='sdktest')
    roomEventHandler = RTCRoomEventHandler()
    rtcRoom.setRTCRoomEventHandler(roomEventHandler)
    userInfo = sdk.UserInfo('yinkaisheng', extra_info='{"extra_test": "HelloWorld"}')
    token = '00162e52104c0700a038dd110ccSAD7FE4EFeD0YpUa/mIHAHNka3Rlc3QLAHlpbmthaXNoZW5nBgAAAJUa/mIBAJUa/mICAJUa/mIDAJUa/mIEAJUa/mIFAJUa/mIgANRMfZXevxZ4/1PRVavybItNg40FmgHB+MJ16uP3/ho6'
    roomConfig = sdk.RTCRoomConfig()
    roomConfig.room_profile_type = sdk.RoomProfileType.Communication
    roomConfig.is_auto_publish = True
    roomConfig.is_auto_subscribe_audio = True
    roomConfig.is_auto_subscribe_video = True
    #roomConfig.remote_video_config.framerate = 15
    #roomConfig.remote_video_config.resolution_width = 640
    #roomConfig.remote_video_config.resolution_height = 360
    rtcRoom.joinRoom(token=token, user_info=userInfo, config=roomConfig)
    if isCameraCapture:
        rtcRoom.publishStream(sdk.MediaStreamType.Both)
    else:
        rtcRoom.publishScreen(sdk.MediaStreamType.Both)
    input('----\npaused\n----')
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


