#!/usr/bin/python

from datetime import datetime
import hashlib
import hmac
import requests
import RPi.GPIO as GPIO
import serial
import struct
import time
import yaml

# System variables
counter = 0
apiFailureDate = False
exitRelay = 15
keypadDevice = False
keypadEnabled = False

# Initialisation from config
with open('config.yaml') as config_f:
    config = yaml.safe_load(config_f)

api_key = config['members']['apikey']
secret = config['hotp']['secret']
codeLength = config['hotp']['length']
get_api_url = config['hotp']['get_api']
post_api_url = config['hotp']['post_api']
apiLockoutHours = config['hotp']['api_failure_lockout_hours']
door_release_time = config['door']['release_time']
keypadConfig = config.get('serial', False)


def dt(mac):
    hdig = mac.hexdigest()
    offset = int(hdig[-1], 16)
    p = hdig[offset * 2: offset * 2 + 8]
    return int(p, 16) & 0x7fffffff


def hotp(key, counter, length):
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1)
    s = dt(mac)
    return "{:06}".format(s % 10 ** length)


def readCounter():
    global counter
    with open("counter.txt", "r") as f:
        return int(f.readline())


def getCounter():
    global counter, apiFailureDate, keypadEnabled
    localCounter = readCounter()

    try:
        response = requests.get(get_api_url)
        remoteCounter = int(response.json()["counter"])
        if(remoteCounter == -1):
            keypadEnabled = False
        else:
            keypadEnabled = True
            counter = max(remoteCounter, localCounter)
            if(counter != localCounter):
                updateCounter(counter)
                announceCodeAtCounter(counter)
        apiFailureDate = False
    except:
        counter = localCounter
        # Record first instance of failure to measure downtime
        if(apiFailureDate == False):
            apiFailureDate = datetime.now()
        print("Failed")


def updateCounter(c):
    global counter

    counter = max(counter, c)

    with open('counter.txt', 'w') as f:
        f.write('%d' % c)


def announceCodeAtCounter(counter):
    global codeLength, secret

    try:
        valid_code = hotp(secret, counter, codeLength)
        payload = {'code': valid_code, 'counter': counter}
        requests.post(post_api_url, data=payload)
    except:
        pass


def connectSerial():
    global keypadDevice, keypadConfig
    if(keypadConfig and keypadDevice == False):
        try:
            keypadDevice = serial.Serial(
                keypadConfig['port'], keypadConfig['baud'], timeout=1
            )
            keypadDevice.flush()
            print("Connected!")
        except Exception as e:
            print("Failed to connect!")
            pass


def disconnectSerial():
    global keypadDevice
    try:
        if keypadDevice:
            print("Disconnected")
            keypadDevice.close()
            keypadDevice = False
    except Exception as e:
        print("Failed to disconnect keypad")


def validateCode(input_code):
    global codeLength
    valid_code = hotp(secret, counter, codeLength)

    return input_code == valid_code


def main():
    global apiLockoutHours, counter, keypadEnabled, apiFailureDate, door_release_time
    last_report = 0

    while True:
        connectSerial()

        if((datetime.now() - apiFailureDate).hours > apiLockoutHours):
            keypadEnabled = False
        else:
            keypadEnabled = True

        try:
            if keypadDevice:
                if keypadDevice.in_waiting > 0:
                    line = keypadDevice.readline().decode('utf-8').rstrip()

                    if(keypadEnabled and validateCode(line)):
                        updateCounter(counter + 1)

                        # Release the door
                        GPIO.output(exitRelay, GPIO.LOW)
                        time.sleep(door_release_time)
                        GPIO.output(exitRelay, GPIO.HIGH)

                        # Tell the member system
                        announceCodeAtCounter(counter)
                    else:
                        print("Invalid code")
        except Exception as e:
            disconnectSerial()
        finally:
            now = datetime.now()
            if(now.minute != last_report):
                last_report = now.minute
                getCounter()
            time.sleep(0.5)
        time.sleep(1)


if __name__ == '__main__':
    main()
