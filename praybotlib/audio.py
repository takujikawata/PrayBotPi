#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Module for audio play for pray bot
'''

import time
from contextlib import closing
import logging
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
import pygame

class PrayBotAudio:
    '''
    audio handle class for pray bot
    '''

    def __init__(self):
        self.logger = logging.getLogger("praybot")

        pygame.init()
        pygame.mixer.init()

        self.in_say = False

        self.session = Session(region_name="us-west-2")
        self.polly = self.session.client("polly")

    def stop(self):
        '''
        stop audio
        '''
        pygame.quit()  

    def get_volume(self):
        '''
        get volume
        '''
        return pygame.mixer.music.get_volume()

    def set_volume(self, _volume):
        '''
        change audio volume 
        '''
        pygame.mixer.music.set_volume(_volume)

    def say(self, _message):
        '''
        speak message
        '''

        in_say = True
        self.logger.info("Speak: %s" % _message)
        
        try:
            response = self.polly.synthesize_speech(Text="<speak><prosody pitch='+50%'>"
                                                    + _message
                                                    + "</prosody></speak>",
                                                    TextType="ssml",
                                                    OutputFormat="mp3",
                                                    VoiceId="Mizuki")
        except (BotoCoreError, ClientError) as error:
            self.logger.warning(error)
            return

        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                output = "speech.mp3"
                try:
                    with open(output, "wb") as file:
                        file.write(stream.read())
                except IOError as error:
                    self.logger.warning(error)
                    return

        else:
            self.logger.warning("Could not stream audio")
            return

        pygame.mixer.music.load("speech.mp3")
        pygame.mixer.music.play()

        in_say = False

    def is_playing(self):
        '''
        check if audio is playing
        '''
        return self.in_say or pygame.mixer.music.get_busy()

    def volume_up(self):
        '''
        volume up +5%
        '''
        v = self.get_volume()
        v += 0.05
        if v > 1.0:
            v = 1.0

        #print v
        self.set_volume(v)

        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load("audio/button04a.mp3")
            pygame.mixer.music.play()

        return v

    def volume_down(self):
        '''
        volume down -5%
        '''
        v = self.get_volume()
        v -= 0.05
        if v < 0:
            v = 0

        #print v
        self.set_volume(v)

        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load("audio/button04a.mp3")
            pygame.mixer.music.play()

        return v

    def greeting(self):
        '''
        say greeting message
        '''
        import datetime
        h = datetime.datetime.now().hour
        a = "audio/hello.mp3"
        if h >= 4 and h <= 10:
            a = "audio/goodmorning.mp3"
        elif h > 10 and h < 17:
            a = "audio/hello.mp3"
        else:
            a = "audio/goodevening.mp3"

        pygame.mixer.music.load(a)
        pygame.mixer.music.play()

    def play_audio(self, path):
        '''
        play audio file
        '''
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()


    def wait_playback(self):
        while self.is_playing():
            time.sleep(0.1)

if __name__ == "__main__":


    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                        level=logging.DEBUG)

    audio = PrayBotAudio()

    import sys
    if len(sys.argv) <= 1:
        audio.greeting()
        exit(0)
    else:
        message = sys.argv[1]

    if (len(sys.argv)) == 3:
        volume = float(sys.argv[2])
    else:
        volume = 1.0

    audio.set_volume(volume)
    print("Audio Volume: %f" % audio.get_volume())
    print("Say: %s" % message)

    audio.say(message)

    while audio.is_playing():
        time.sleep(1)
        print "Continue.."
        continue

    print "END"

    audio.stop()
    exit(0)