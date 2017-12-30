#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Pray Bot Main module
'''

import time
import Queue
import json
import threading
import ConfigParser
import RPi.GPIO as GPIO
import websocket

from praybot.audio import PrayBotAudio
from praybot.motion import PrayBotMotion
from praybot.animations import PrayBotAnimations

class PrayBotMain:
    '''
    Main Class for pray bot
    '''

    VOLUME_UP = 20
    VOLUME_DOWN = 19
    POWER_OFF = 21

    SERVER_URI = "ws://api.pray.robowebapi.com/praybots"
    SETTING_FILE = "setting.cfg"

    def __init__(self, _maxPrayAtOnce, _prayIfPrayedLessThan):
        print("PrayBot init..")
        self.prayQueue = Queue.Queue()
        self.bOpening = False

        self.audio = PrayBotAudio()
        self.motion = PrayBotMotion()

        self.maxPrayAtOnce = _maxPrayAtOnce
        self.prayIfPrayedLessThan = _prayIfPrayedLessThan

        self.config = ConfigParser.SafeConfigParser()
        self.config.read(PrayBotMain.SETTING_FILE)

        v = self.config.getfloat('Audio', 'volume')
        self.audio.set_volume(v)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PrayBotMain.VOLUME_UP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PrayBotMain.VOLUME_UP,
                              GPIO.RISING, callback=self._gpi_callback, bouncetime=300)

        GPIO.setup(PrayBotMain.VOLUME_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PrayBotMain.VOLUME_DOWN,
                              GPIO.RISING, callback=self._gpi_callback, bouncetime=300)

        GPIO.setup(PrayBotMain.POWER_OFF, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(PrayBotMain.POWER_OFF,
                              GPIO.RISING, callback=self._gpi_callback, bouncetime=300)

    def _gpi_callback(self, channel):

        input_state = GPIO.input(channel)
        saveSetting = False
        if channel == PrayBotMain.VOLUME_UP:
            if input_state:
                print "volume up"
                v = self.audio.volume_up()
                self.config.set('Audio', 'volume', '%.2f' % v)
                saveSetting = True
        elif channel == PrayBotMain.VOLUME_DOWN:
            if input_state:
                print "volume down"
                v = self.audio.volume_down()
                self.config.set('Audio', 'volume', '%.2f' % v)
                saveSetting = True

        if saveSetting:
            with open(PrayBotMain.SETTING_FILE, 'wb') as f:
                self.config.write(f)

    def start(self):
        '''
        Start pray bot
        '''
        print "PrayBot start.."
        if self.bOpening:
            print "websocket client already opening.."
            return

        self.praying = None

        self.ws = None
        self.bOpening = True
        self.bStopRequest = False
        self.cond = threading.Condition()
        self._connect()

    def _pray_finished(self):
        print "prayFinished"

        if self.praying != None:
            payload = {
                "req_time":self.praying["req_time"],
                "seq":self.praying["seq"],
                "cmd" : "prayed"}

            self._sendMessage(json.dumps(payload))

        with self.cond:
            self.praying = None
            if self.bStopRequest:
                self.cond.notifyAll()
                return

        if self.prayQueue.qsize() > 0:
            self.praying = self.prayQueue.get()
            self._doPray()

    def _doPray(self):
        payload = {
            "req_time":self.praying["req_time"],
            "seq":self.praying["seq"],
            "cmd" : "prayRequested"}

        self._sendMessage(json.dumps(payload))

        time.sleep(2)
        self.motion.play_animation(PrayBotAnimations.WAKEUP)
        time.sleep(1)
        self.motion.play_animation(PrayBotAnimations.PRAY_MOTION, smooth=True)
        self.audio.say(self.praying["message"]["body"].encode("utf-8"))

        while(self.audio.is_playing() or self.motion.is_playing()):
            if self.audio.is_playing() and not self.motion.is_playing():
                self.motion.play_animation(PrayBotAnimations.PRAY_MOTION, smooth=True)
            #print "Playing.."
            time.sleep(0.5)

        self.motion.wait_animation()
        self.motion.play_animation(PrayBotAnimations.WAKEUP, smooth=True)
        time.sleep(5)
        self.motion.play_animation(PrayBotAnimations.REST, smooth=True)
        self.motion.wait_animation()

        self.motion.stop_all()

        self._pray_finished()


    def _connect(self):
        print "PrayBot connecting to server.."
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(PrayBotMain.SERVER_URI,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close)
        self.ws.on_open = self._on_open
        self.ws.run_forever()

    def _sendMessage(self, p):
        if self.bOpening:
            self.ws.send(p)


    def _on_message(self, ws, data):
        try:
            messages = json.loads(data)
        except:
            return

        if "cmd" not in messages:
            return

        if messages[u"cmd"] != u"add":
            return

        if u"messages" not in messages:
            return

        for item in messages[u"messages"]:
            if (not "message" in item
                    or not "body" in item["message"]
                    or not "prayed" in item):
                continue

            if self.prayQueue.qsize() >= self.maxPrayAtOnce:
                break
            if item[u"prayed"] < int(self.prayIfPrayedLessThan):
                self.prayQueue.put(item)

            with self.cond:
                if self.praying == None and self.prayQueue.qsize() > 0:
                    self.praying = self.prayQueue.get()

                    #print("doPray..")
                    self._doPray()

    def _on_error(self, ws, error):
        self.bOpening = False
        print "WebSocket Error:" + error

    def _on_close(self, ws):
        self.bOpening = False
        print "Websocket closed"

    def _on_open(self, ws):
        print "connected to server"


if __name__ == "__main__":

    prayBot = PrayBotMain(5,1)
    prayBot.start()
