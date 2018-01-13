#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
motion control module for pray bot
'''

import threading
import time
import RPi.GPIO as GPIO

from praybotlib.animations import PrayBotAnimations

class PrayBotMotion:
    '''
    motion control class for pray bot
    '''

    SERVO_CHANNELS = [18]
    RELAY_CHANNELS = [22, 23]

    def __init__(self):

        self.pwms = []
        self.pwms_running = []
        self.angles = []

        self._isPlaying = False
        self._reqStopAnimation = False
        self._lock = threading.Lock()

        GPIO.setmode(GPIO.BCM)
        for channel in PrayBotMotion.SERVO_CHANNELS:
            GPIO.setup(channel, GPIO.OUT)
            self.pwms.append(GPIO.PWM(channel, 100))            
            self.pwms_running.append(False)
            self.angles.append(0)
        for channel in PrayBotMotion.RELAY_CHANNELS:
            GPIO.setup(channel, GPIO.OUT, initial=GPIO.HIGH)

    def set_angle(self, n, angle):
        '''
        chanage angle of survo motor n to angel degree
        '''
        if angle > 90 or angle < -90:
            return

        self.angles[n] = angle
        duty = float(angle) / 10.0 + 14.5
        if not self.pwms_running[n]:
            self.pwms[n] = GPIO.PWM(PrayBotMotion.SERVO_CHANNELS[n], 100)
            self.pwms[n].start(duty)
            self.pwms_running[n] = True
        else:
            self.pwms[n].ChangeDutyCycle(duty)

    def _worker(self, animation, smooth):
        self._reqStopAnimation = False
        
        steps = [0 for i in range(len(animation[0]))]
        actives = [False for i in range(len(animation[0]))]
    
        finished = False

        startTime = time.time()
        nextTime = animation[1][0]

        for nn in animation[0][0]:
            n = int(nn)
            angle = animation[0][0][nn]

            actives[n] = True
        
            dt = nextTime
            
            if smooth and self.pwms_running[n]:
                if dt > 0:
                    steps[n] = ((angle - self.angles[n]) / dt) / 50.0
                else:
                    steps[n] = 0
                    self.set_angle(n, angle)
            else:
                steps[n] = 0
                self.set_angle(n, angle)

        nextPos = 1
        while(not (self._reqStopAnimation or finished)):

            currentTime = time.time()
            elaspedTime = currentTime - startTime

            if elaspedTime > nextTime:
                if len(animation[0]) <= nextPos:
                    finished = True
                    continue

                nextTime = animation[1][nextPos]
                for nn in animation[0][nextPos]:
                    n = int(nn)
                    angle = animation[0][nextPos][nn]

                    actives[n] = True
                
                    dt = nextTime - elaspedTime
                    
                    if smooth and self.pwms_running[n]:
                        if dt > 0:
                            steps[n] = ((angle - self.angles[n]) / dt) / 50.0
                        else:
                            steps[n] = 0
                            self.set_angle(n, angle)
                    else:
                        steps[n] = 0
                        self.set_angle(n, angle)

                nextPos += 1

            for i in range(0, len(self.pwms)):
                if actives[i]:
                    self.set_angle(i, self.angles[i] + steps[i])

            time.sleep(0.02 - (time.time() - currentTime))

        self._isPlaying = False

    def wakeup(self):
        '''
        power on servo motor (set relay 1 on)
        '''
        self.set_relay(1, True)

    def rest(self):
        '''
        power off servo motor (set relay 1 off)
        '''
        self.set_relay(1, False)

    def play_animation(self, animation, smooth=False):
        '''
        play motion animation
        '''

        with self._lock:
            while self._isPlaying:
                self._reqStopAnimation = True
                time.sleep(0.5)

            self._isPlaying = True
            t = threading.Thread(target=self._worker, args=(animation, smooth))
            t.start()

    def is_playing(self):
        '''
        check if motion anomation is playing
        '''
        return self._isPlaying

    def wait_animation(self):
        '''
        wait until motion animation completes
        '''

        while self._isPlaying:
            time.sleep(0.2)

    def set_relay(self, n, isOn):
        '''
        set relay n to isOn
        '''
        if isOn:
            GPIO.output(PrayBotMotion.RELAY_CHANNELS[n], GPIO.LOW)
        else:
            GPIO.output(PrayBotMotion.RELAY_CHANNELS[n], GPIO.HIGH)
            
    def stop_all(self):
        '''
        go to rest mode
        '''
        while self._isPlaying:
            time.sleep(0.1)

        time.sleep(0.5)

        for i in range(0, len(self.pwms)):
            self.pwms[i].stop()
            self.pwms_running[i] = False

        for channel in PrayBotMotion.RELAY_CHANNELS:
            GPIO.output(channel, GPIO.HIGH)

        time.sleep(1)

    def clean_up(self):
        '''
        clean up GPIO settings
        '''
        for i in range(0, len(self.pwms)):
            GPIO.cleanup(PrayBotMotion.SERVO_CHANNELS[i])

        for channel in PrayBotMotion.RELAY_CHANNELS:
            GPIO.cleanup(channel)

if __name__ == "__main__":
    import sys

    motion = PrayBotMotion()

    if len(sys.argv) <= 1: 
        motion.wakeup()
        motion.play_animation(PrayBotAnimations.SAMPLE_MOTION)
        while(motion.is_playing()):
            print("Playing..")
            time.sleep(1)
        motion.play_animation(PrayBotAnimations.SAMPLE_MOTION, True)
        while(motion.is_playing()):
            print("Playing..")
            time.sleep(1)        
    else:
        angle = int( sys.argv[1])
        if angle > 90 or angle < -90:
            print "サーボモータの角度を -90 から 90 で指定してください"
            exit(-1)

        print("set servo angle to : %f" % angle)
        motion.wakeup()
        motion.set_angle(0, angle)

        time.sleep(1)


    motion.stop_all()
    motion.rest()
    exit(0)
