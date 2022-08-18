#下面所有代码在MainWindow中的上下文执行
def publishCameraStreamTest(self, cameraIndex: int):
    if self.rtcVideo is None:
        appInfo = self.configJson['appNameList'][self.configJson['appNameIndex']]
        appId = appInfo['appId']    #使用配置文件ByteRtcDemo.config里的AppId
        #appid = '62e52104c0700a038dd110cc' #使用自己的AppId
        jsonParams = '{"key": "value"}'
        self.rtcVideo = sdk.RTCVideo(app_id=appId, event_handler=self, parameters=jsonParams)
    self.setWindowTitle(f'{DemoTitle}, sdk: {sdk.getVersion()}, APILog: bytesdklog/{sdk.APILogPath}')

    self.rtcVideo.startAudioCapture()

    #从界面获取采集宽高等配置
    videoCaptureConfig = sdk.VideoCaptureConfig()
    videoCaptureConfig.capturePreference = sdk.CapturePreference(int(self.capturePreferenceCombox.currentText()[-1]))
    videoCaptureConfig.width = int(self.widthEdit.text())
    videoCaptureConfig.height = int(self.heightEdit.text())
    videoCaptureConfig.frameRate = int(self.fpsEdit.text())
    #使用自定义配置
    #videoCaptureConfig.capturePreference = sdk.CapturePreference.Auto #0
    #videoCaptureConfig.capturePreference = sdk.CapturePreference.Manual #1
    #videoCaptureConfig.capturePreference = sdk.CapturePreference.AutoPerformance    #2
    #videoCaptureConfig.width = 1280
    #videoCaptureConfig.height = 720
    #videoCaptureConfig.frameRate = 15
    self.rtcVideo.setVideoCaptureConfig(videoCaptureConfig)

    #从界面获取编码宽高等配置
    videoEncoderConfig = sdk.VideoEncoderConfig()
    videoEncoderConfig.width = int(self.widthEdit.text())
    videoEncoderConfig.height = int(self.heightEdit.text())
    videoEncoderConfig.frameRate = int(self.fpsEdit.text())
    videoEncoderConfig.maxBitrate = int(self.bitrateEdit.text())
    videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Framerate
    #使用自定义配置
    #videoEncoderConfig.width = 1280
    #videoEncoderConfig.height = 720
    #videoEncoderConfig.frameRate = 15
    #videoEncoderConfig.maxBitrate = -1
    #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Disabled #0
    #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Framerate #1
    #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Quality #2
    #videoEncoderConfig.encoderPreference = sdk.VideoEncodePreference.Balance #3
    self.rtcVideo.setVideoEncoderConfig(videoEncoderConfig)

    viewText = self.localViewEdit.text().strip()
    viewHandle = int(viewText, base=16 if viewText.startswith('0x') or viewText.startswith('0X') else 10)
    #renderMode = sdk.RenderMode.Hidden  #1
    renderMode = sdk.RenderMode.Fit     #2
    #renderMode = sdk.RenderMode.Fill    #3
    videoCanvas = sdk.VideoCanvas(view=viewHandle, render_mode=renderMode, background_color=0x000000)
    index = sdk.StreamIndex.Main    #0
    #index = sdk.StreamIndex.Screen #1
    self.rtcVideo.setLocalVideoCanvas(index, videoCanvas)

    #选择摄像头
    self.vdm = self.rtcVideo.getVideoDeviceManager()
    if self.vdm:
        deviceInfoList = self.vdm.getDeviceInfoList()
        if cameraIndex < len(deviceInfoList):
            self.vdm.setVideoCaptureDevice(deviceInfoList[cameraIndex].device_id)

    self.rtcVideo.startVideoCapture()

    if self.rtcRoom is None:
        self.roomId = self.roomIdEdit.text().strip()
        #self.roomId = "TheRoomId"
        self.rtcRoom = self.rtcVideo.createRTCRoom(self.roomId)
        self.rtcRoom.setRTCRoomEventHandler(self)

    userId = self.userIdEdit.text().strip()
    #userId = 'TheUserId'
    token = self.tokenEdit.text().strip()
    if not token:
        userTokens = self.configJson['appNameList'][self.configJson['appNameIndex']].get(self.rtcRoom.roomId, None)
        if userTokens:
            token = userTokens.get(userId, '')
    #token = 'TheToken'
    jsonExtra = '{"rtctest":"hello byte rtc"}'
    userInfo = sdk.UserInfo(uid=userId, extra_info=jsonExtra)
    roomConfig = sdk.RTCRoomConfig()
    roomConfig.room_profile_type = sdk.RoomProfileType.Communication        #0
    #roomConfig.room_profile_type = sdk.RoomProfileType.LiveBroadcasting     #1
    #roomConfig.room_profile_type = sdk.RoomProfileType.Game                 #2
    #roomConfig.room_profile_type = sdk.RoomProfileType.CloudGame            #3
    #roomConfig.room_profile_type = sdk.RoomProfileType.LowLatency           #4
    #roomConfig.room_profile_type = sdk.RoomProfileType.Chat                 #5
    #roomConfig.room_profile_type = sdk.RoomProfileType.ChatRoom             #6
    #roomConfig.room_profile_type = sdk.RoomProfileType.LwTogether           #7
    #roomConfig.room_profile_type = sdk.RoomProfileType.GameHD               #8
    #roomConfig.room_profile_type = sdk.RoomProfileType.CoHost               #9
    #roomConfig.room_profile_type = sdk.RoomProfileType.InteractivePodcast   #10
    #roomConfig.room_profile_type = sdk.RoomProfileType.KTV                  #11
    #roomConfig.room_profile_type = sdk.RoomProfileType.Chorus               #12
    #roomConfig.room_profile_type = sdk.RoomProfileType.VRChat               #13
    #roomConfig.room_profile_type = sdk.RoomProfileType.GameStreaming        #14
    #roomConfig.room_profile_type = sdk.RoomProfileType.LanLiveStreaming     #15
    #roomConfig.room_profile_type = sdk.RoomProfileType.Meeting              #16
    #roomConfig.room_profile_type = sdk.RoomProfileType.MeetingRoom          #17
    #roomConfig.room_profile_type = sdk.RoomProfileType.Classroom            #18
    roomConfig.is_auto_publish = True
    #roomConfig.is_auto_publish = False
    roomConfig.is_auto_subscribe_audio = True
    #roomConfig.is_auto_subscribe_audio = False
    roomConfig.is_auto_subscribe_video = True
    #roomConfig.is_auto_subscribe_video = False

    for i in range(5):
        if self.connected:
            break
        time.sleep(0.05)
    self.rtcRoom.joinRoom(token, user_info=userInfo, room_config=roomConfig)


#给MainWindow动态添加方法
MainWindow.publishCameraStreamTest = publishCameraStreamTest


def onConnectionStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
    #自定义回调处理，打开log文件查看dict对象内容
    if event['state'] == sdk.ConnectionState.Connected:
        self.connected = True


MainWindow.onConnectionStateChanged = onConnectionStateChanged


def onRoomStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
    #自定义回调处理，打开log文件查看dict对象内容
    if event['state'] != 0:
        print('wrong')


MainWindow.onRoomStateChanged = onRoomStateChanged

#绑定回调，回调发生时会自动调用新添加的方法，所有回调都已转到UI线程处理
self.RTCVideoEventHandler['onConnectionStateChanged'] = self.onConnectionStateChanged
self.RTCRoomEventHandler['onRoomStateChanged'] = self.onRoomStateChanged
'''
下面几个回调Demo内部已经有内置的处理
onUserJoined
onUserLeave
onUserPublishStream
onUserUnpublishStream
onUserPublishScreen
onUserUnpublishScreen
如果要增加自定义处理，可以这样使用
def onUserJoinedExtra(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
    self.onUserJoined(event_time, event_name, event_json, event)
    #write your extra code
    
MainWindow.onUserJoinedExtra = onUserJoinedExtra
self.RTCRoomEventHandler['onUserJoined'] = self.onUserJoinedExtra
'''

#执行测试代码
self.connected = False
self.publishCameraStreamTest(cameraIndex=1)

#最后请手动点击destroyRTCVideo按钮销毁对象或者延迟调用self.onClickDestroyRtcVideoBtn
#self.delayCall(timeMs=10000, func=self.onClickDestroyRtcVideoBtn)
