# HOTP based Keypad entry system
This is a small program which can manage access to physical spaces, using one time use HOTP codes. 

✨ Ideal for running on a Raspberry Pi (or other computer or server) to manage one time passwords such as for access to a physical space e.g. a hackerspace/makerspace, room, cabinet.

## Summary
The system requires:
* Keypad
* Raspberry Pi
* Lock

### The Keypad
The input is over USB. Therefore you can use:
* USB keypad
* Standard keypad with matrix wires, which connects to an Arduino, which in turn sends any codes entered over USB. 
  >Ideal for using vandal resistant outside keypads with an arduino inside alongside the Pi running the Python script.

### The Pi
The keypad connects to the Pi. The `keypad-access.py` script needs to be automatically started when the Pi boots.
 > There are many resources to get a python script running at boot.

The script will constantly try to reconnect to the keypad if connection is lost.

### The lock
I've built this to release a fail-secure lock, but with a bit of tweaking of the code, or a relay added in, you can make it suitable for a fail safe lock.


## Communication
This system internally listens for input from a keypad, generates HOTP codes, and validates what it receives. To be useful, it can:
*  announce the current valid code somewhere secure. 
*  be made to regenerate codes, by checking for an external counter


### 📢 Announces the currently valid code somewhere secure
  * The Pi will `POST your.api.here/route {'code': 'N', 'counter': 'M'}` when a new code is generated.
    * `N` and `M` will be numbers 
  * This could be to an online service which displays the valid code to authenticated users. This can be whatever you want. Use some kind of an API key however to prevent abuse.

### 👀 be made to regenerate codes, by checking for an external counter
  * The Pi will `GET your.api.here/route`
  * the API should return `{'counter' : 'N'}`
  * If this endpoint counter is higher than the internal counter, the internal counter will update. This will cause a new code to be announced.
  * If this endpoint counter is `-1`, then the keypad will lockout.
  * If this endpoint stops working, after a given time interval, the keypad will lockout


## Use case
This is designed for the membership system at Hackspace Manchester (forked from Build Brighton Member System). 

It allows contractors access as well as people who forgot their fob - they can log in to the membership system and fetch the code to let them in.

The regeneration feature is ideal as we can remotely regenerate the valid code, so long as the Pi has access to the internet. The membership system increases it's own counter and publishes the updated counter, and the Pi will announce back the new code, thus invalidating the old one.
If there's no internet, the keypad will lockout after a while.

The lockout feature is ideal for when we want to disable the keypad or if the internet goes down.


## ToDo

