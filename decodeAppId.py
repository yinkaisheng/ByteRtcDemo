#!python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
import string


def decodeAppId(appId: str) -> str:
    '''
    decode the AppId gotten from the config file
    if you don't want to put AppId plaintext in config file
    you can put encoded AppId in config file and implement this function to decode it
    '''
    chars = list(appId)
    chars.reverse()
    newAppId = []
    for c in chars:
        index = string.digits.find(c)
        if index >= 0:
            nc = string.digits[(index + len(string.digits) // 2) % len(string.digits)]
        else:
            index = string.ascii_lowercase.find(c)
            if index >= 0:
                nc = string.ascii_lowercase[(index + len(string.ascii_lowercase) // 2) % len(string.ascii_lowercase)]
            else:
                nc = c
        # print(c, '->', nc)
        newAppId.append(nc)
    newAppId = ''.join(newAppId)
    return newAppId
