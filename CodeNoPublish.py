#下面所有代码在MainWindow中的上下文执行
def noPublisTest(self):
    index = self.envCombox.currentIndex()
    if index >= 0:
        env = sdk.Env(index)
        #env = sdk.Env.Product
        #env = sdk.Env.BOE
        #env = sdk.Env.Test
        sdk.setEnv(env)
    if self.rtcVideo is None:
        appInfo = self.configJson['appNameList'][self.configJson['appNameIndex']]
        appId = appInfo['appId']    #使用配置文件ByteRtcDemo.config里的AppId
        #appid = '62e52104c0700a038dd110cc' #使用自己的AppId
        jsonParams = '{"key": "value"}'
        self.rtcVideo = sdk.RTCVideo(app_id=appId, event_handler=self, parameters=jsonParams)
    self.setWindowTitle(f'{DemoTitle}, sdk: {sdk.getVersion()}, APILog: bytesdklog/{sdk.APILogPath}')

    if self.cloudProxyCheck.isChecked():
        self.onClickCloudProxyCheck()
    #self.rtcVideo.startCloudProxy([('10.37.144.157', 6779)])


#给MainWindow动态添加方法
MainWindow.noPublisTest = noPublisTest


def onConnectionStateChanged(self, event_time: int, event_name: str, event_json: str, event: dict) -> None:
    #自定义回调处理，打开log文件查看dict对象内容
    if event['state'] == sdk.ConnectionState.Connected:
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

        userId = self.userIdEdit.text().strip()
        #userId = 'TheUserId'
        token = self.tokenEdit.text().strip()
        if not token:
            userTokens = self.configJson['appNameList'][self.configJson['appNameIndex']].get(roomId, None)
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
        roomConfig.is_auto_publish = False  #self.autoPublishCheck.isChecked()
        roomConfig.is_auto_subscribe_audio = self.autoSubscribeAudioCheck.isChecked()
        roomConfig.is_auto_subscribe_video = self.autoSubscribeVideoCheck.isChecked()
        # roomConfig.is_auto_publish = True
        # roomConfig.is_auto_publish = False
        # roomConfig.is_auto_subscribe_audio = True
        # roomConfig.is_auto_subscribe_audio = False
        # roomConfig.is_auto_subscribe_video = True
        # roomConfig.is_auto_subscribe_video = False

        rtcRoom.joinRoom(token, user_info=userInfo, room_config=roomConfig)

        # streamType = sdk.MediaStreamType(int(self.streamMediaStreamTypeCombox.currentText()[-1]))
        # rtcRoom.publishStream(streamType)
        # rtcRoom.publishStream(sdk.MediaStreamType.Audio)
        # rtcRoom.publishStream(sdk.MediaStreamType.Video)
        # rtcRoom.publishStream(sdk.MediaStreamType.Both)


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
self.noPublisTest()

#最后请手动点击destroyRTCVideo按钮销毁对象或者延迟调用self.onClickDestroyRtcVideoBtn
#self.delayCall(timeMs=10000, func=self.onClickDestroyRtcVideoBtn)
