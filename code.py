# Circuitpy imports
import json
import os
import time

import board
import busio as io
import digitalio
import analogio
import rtc
import storage
import adafruit_sdcard  # TODO: test sdcardio, remove if it is better
# import sdcardio
import microcontroller

# Special imports
import supervisor

# Network imports
import ssl, wifi, socketpool, adafruit_requests

# Music imports
from audiocore import WaveFile, RawSample
from audiopwmio import PWMAudioOut as AudioOut
import audiomixer
import adafruit_wave as wave

# PyRTOS and LCD library
import lib.pyRTOS as pyRTOS
from lib.lcd.lcd import LCD, CursorMode
from lib.lcd.i2c_pcf8574_interface import I2CPCF8574Interface

# User classes for simplicity
import timekeep
import log
import buttons as B
from scrollable_list import ScrollableList

supervisor.runtime.autoreload = False

ICON_CURSOR = (0x08,0x0C,0x0E,0x0F,0x0E,0x0C,0x08,0x00)
ICON_BAT_FULL = (0x0E,0x1F,0x1F,0x1F,0x1F,0x1F,0x1F,0x1F)
ICON_BAT_MED = (0x0E,0x11,0x11,0x1F,0x1F,0x1F,0x1F,0x1F)
ICON_BAT_LOW = (0x0E,0x11,0x11,0x11,0x11,0x1F,0x1F,0x1F)
ICON_BAT_PLUGGED = (0x0A,0x0A,0x1F,0x1F,0x1F,0x0E,0x04,0x04)
ICON_WIFI_ON = (0x00,0x0E,0x11,0x04,0x0A,0x00,0x04,0x00)
ICON_WIFI_OFF = (0x00,0x11,0x0A,0x04,0x0A,0x11,0x04,0x00)
ICON_PAUSE = (0x00,0x1B,0x1B,0x1B,0x1B,0x1B,0x1B,0x00)


i2c = io.I2C(board.GP5, board.GP4, frequency=100000)
lcd = LCD(I2CPCF8574Interface(i2c, 0x27), num_rows=4, num_cols=20)
lcd.set_cursor_mode(CursorMode.HIDE)

IS_SD_MOUNTED = False

lcd.print('Booting...\n')

# Connect to the card and mount the filesystem.
try:
    spi = io.SPI(board.GP10, board.GP11, board.GP12)
    cs = digitalio.DigitalInOut(board.GP13)
    #cs = board.GP13
    sdcard = adafruit_sdcard.SDCard(spi, cs, 32_000_000)  # TODO: remove baudrate if wont work
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    IS_SD_MOUNTED = True
except Exception as e:
    IS_SD_MOUNTED = False
    print('Failed to mount filesystem:', e)
    lcd.set_cursor_pos(0, 0)
    lcd.print('No SD card\n')
    time.sleep(0.2)

lcd.print('1')
time.sleep(1)

DISPLAY_BUFFER = ''
IS_IN_SLEEP = False
LAST_TIME = time.struct_time((0, 0, 0, 0, 0, 0, 0, -1, -1))

bat_voltage = analogio.AnalogIn(board.VOLTAGE_MONITOR)
bat_plugged = digitalio.DigitalInOut(board.VBUS_SENSE)

# Init audio
CLICK_NORMAL = WaveFile('/sounds/ClickNormal.wav')
CLICK_SELECT = WaveFile('/sounds/ClickSelect.wav')
CLICK_MODE = WaveFile('/sounds/ClickMode.wav')
MUSIC = WaveFile('/sd/music/StarWars60.wav', bytearray(256))

TK = timekeep.TimeKeep()

lcd.print('2')
time.sleep(1)

def connect_to_wifi():
    try:
        wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))
        return False
    except Exception as e:
        print('Failed to connect WiFi:', e)
        return True

def disconnect_from_wifi():
    wifi.radio.stop_station()


# connect_to_wifi()
# if TK.sync_time_with_ntp() and IS_SD_MOUNTED:  # When time sync fails and SD is mounted
#     lcd.print('3')
#     TK.load_time()
#     time.sleep(1)
# else:
#     lcd.print('3a')
#     time.sleep(1)
# disconnect_from_wifi()

audio = AudioOut(board.GP9)
mixer = audiomixer.Mixer(voice_count=1, channel_count=2, buffer_size=2048, sample_rate=22050, bits_per_sample=16)
audio.play(mixer)

with wave.open('/sd/music/StarWars60.wav', 'rb') as f:
    print('Loading music...')
    print('Sample width:', f.getsampwidth(), 'bytes')
    print('Frequency:', f.getframerate(), 'kHz')
    print('Number of frames:', f.getnframes())
    print('Audio duration:', f.getnframes() / f.getframerate(), 'seconds')
    first = 0
    last = 1/20
    f.setpos(first)
    audio.play(f)
    while audio.playing:
        frame = f.tell()
        if frame >= last:
            audio.stop()
            first = last
            last += 1/20
            f.setpos(first)
            # escape the playing for display
            print('Rendered screen')
            # return to playing
            audio.play(f)


# mixer.play(MUSIC_CANTINA)

lcd.print('Boot complete\n')
lcd.print('SD:' + str(IS_SD_MOUNTED) + '\n')
lcd.print('WiFi:' + str(wifi.radio.connected) + '\n')
time.sleep(1)

LOG = log.Log()

def render(self):
    global DISPLAY_BUFFER
    yield
    while True:
        if IS_IN_SLEEP:
            yield [pyRTOS.timeout(0.5)]
            continue
        if DISPLAY_BUFFER:
            lcd.set_cursor_pos(0, 0)
            lcd.print(DISPLAY_BUFFER)
            DISPLAY_BUFFER = ''
        yield [pyRTOS.timeout_ns(120)]

def process(self):
    global DISPLAY_BUFFER
    global LAST_TIME
    t = rtc.RTC()
    is_clock_mode = True

    # Setup menus
    menus = [
        ('Settings', process_settings),
        ('Credits', process_credits),
        ('Music', process_music),
        ('Test', process_credits),
        ('Test2', process_credits),
        ('Test3', process_credits),
    ]
    current_menu = None
    manager = ScrollableList(menus)
    edit_index = 0
    yield

    while True:
        if IS_IN_SLEEP:
            yield [pyRTOS.timeout(0.5)]
            continue

        if B.mode_pressed():
            is_clock_mode = not is_clock_mode
            current_menu = None
            lcd.clear()
            audio.play(CLICK_MODE)
            yield [pyRTOS.timeout(0.05)]

        if is_clock_mode:
            percentage = bat_voltage.value * (1 / 65535) * 10
            if percentage < 3.7:
                lcd.create_char(0, ICON_BAT_MED)
            elif percentage < 3.2:
                lcd.create_char(0, ICON_BAT_LOW)
            elif percentage > 3.7:
                lcd.create_char(0, ICON_BAT_FULL)
            if bat_plugged.value:
                lcd.create_char(0, ICON_BAT_PLUGGED)

            if wifi.radio.connected: # if wifi connected
                lcd.create_char(1, ICON_WIFI_ON)
            else:
                lcd.create_char(1, ICON_WIFI_OFF)

            edit_values = [LAST_TIME.tm_year, LAST_TIME.tm_mon, LAST_TIME.tm_mday, LAST_TIME.tm_hour, LAST_TIME.tm_min, LAST_TIME.tm_sec]

            if B.a_pressed():
                edit_index = (edit_index - 1) % 6
            if B.b_pressed():
                edit_index = (edit_index + 1) % 6
            if B.c_pressed():
                edit_values[edit_index] = (edit_values[edit_index] - 1) % {
                    0: 10000,  # year
                    1: 13,  # month (one more month to skip the decrement)
                    2: 32,  # day (one more day to skip the decrement)
                    3: 24,  # hour
                    4: 60,  # minute
                    5: 60  # second
                }[edit_index]
            if B.d_pressed():
                edit_values[edit_index] = (edit_values[edit_index] + 1) % {
                    0: 10000,  # year
                    1: 13,  # month
                    2: 32,  # day
                    3: 24,  # hour
                    4: 60,  # minute
                    5: 60  # second
                }[edit_index]

            if edit_values != [LAST_TIME.tm_year, LAST_TIME.tm_mon, LAST_TIME.tm_mday, LAST_TIME.tm_hour,
                               LAST_TIME.tm_min, LAST_TIME.tm_sec]:
                t.datetime = time.struct_time((edit_values[0], edit_values[1], edit_values[2], edit_values[3],
                                               edit_values[4], edit_values[5], 0, -1, -1))
                LAST_TIME = time.struct_time((edit_values[0], edit_values[1], edit_values[2], edit_values[3],
                                              edit_values[4], edit_values[5], 0, -1, -1))

            edit_string = ''
            if edit_index == 0:
                edit_string = '^-------------------'
            if edit_index == 1:
                edit_string = '-----^--------------'
            if edit_index == 2:
                edit_string = '--------^-----------'
            if edit_index == 3:
                edit_string = '------------^-------'
            if edit_index == 4:
                edit_string = '---------------^----'
            if edit_index == 5:
                edit_string = '------------------^-'

            date_str = '{:04}-{:02}-{:02}  {:02}:{:02}:{:02}'.format(*edit_values)
            DISPLAY_BUFFER = ('{:.1f}C             ' + chr(1) + chr(0) + date_str + edit_string + ' '*20).format(microcontroller.cpu.temperature)
            # DISPLAY_BUFFER = ('{:.3f}V' + chr(0)).format(percentage)
        else:  # Select mode
            lcd.create_char(0, ICON_CURSOR)
            if current_menu is not None:
                for i in current_menu(self):
                    if i is not None:
                        if i is False:
                            current_menu = None
                            break
                        else:
                            yield [pyRTOS.timeout(i)]
            # Process button input
            if manager.handle_input(audio, CLICK_NORMAL, lcd):
                # yield [pyRTOS.timeout(0.01)]
                pass

            # Render menus
            out = manager.render()
            if callable(out):
                current_menu = out
            else:
                DISPLAY_BUFFER = out

        yield [pyRTOS.timeout(1/60)]

def edit_connection(self):
    global DISPLAY_BUFFER
    yield 0.2
    while True:
        DISPLAY_BUFFER = 'EDIT MODE'.center(20)
        if B.mode_pressed():
            yield False
        yield 1/60

def process_settings(self):
    global DISPLAY_BUFFER
    menus = [
        ('Connect WiFi', process_connect_wifi),
        ('Disconnect WiFI', process_disconnect_wifi),
        ('Edit connection', edit_connection),
        ('Sync time with NTP', process_sync_time_ntp),
        ('Host WiFi page', process_host_page),
        ('Reset', process_reset),
        ('Test', process_credits)
    ]
    manager = ScrollableList(menus)
    current_menu = None
    yield 0.2
    while True:
        if current_menu is not None:
            for i in current_menu(self):
                if i is not None:
                    if i is False:
                        current_menu = None
                        break
                    else:
                        yield i

        manager.handle_input(audio, CLICK_NORMAL, lcd)
        out = manager.render()
        if callable(out):
            current_menu = out
        else:
            DISPLAY_BUFFER = out
        if B.mode_pressed():
            yield False
        yield 1/60


def process_credits(self):
    global DISPLAY_BUFFER
    while True:
        DISPLAY_BUFFER = '-=-=-=-=-=-=-=-=-=-=      ByteBand    \n       by Buko    \n-=-=-=-=-=-=-=-=-=-='
        if B.mode_pressed():
            yield False
        yield 1/60

def process_connect_wifi(self):
    global DISPLAY_BUFFER
    lcd.clear()
    DISPLAY_BUFFER = ''

    if wifi.radio.connected:
        DISPLAY_BUFFER = 'Already connected!'
        yield 2
        yield False

    if connect_to_wifi():
        DISPLAY_BUFFER = 'Failed to connect'
    else:
        DISPLAY_BUFFER = 'Connected!'
    yield 2
    yield False

def process_disconnect_wifi(self):
    global DISPLAY_BUFFER
    lcd.clear()
    DISPLAY_BUFFER = ''

    if not wifi.radio.connected:
        DISPLAY_BUFFER = 'Already disconnected!'
        yield 2
        yield False

    disconnect_from_wifi()
    DISPLAY_BUFFER = 'Disconnected!'
    yield 2
    yield False

def process_reset(self):
    global DISPLAY_BUFFER
    lcd.clear()
    lcd.set_cursor_pos(0, 0)
    lcd.print('Resetting...')
    time.sleep(2)
    microcontroller.reset()


def process_sync_time_ntp(self):
    global DISPLAY_BUFFER
    DISPLAY_BUFFER = ''
    lcd.clear()

    if not wifi.radio.connected:
        DISPLAY_BUFFER = 'Connect to WiFi\nfirst!'
        yield 2
        yield False

    if TK.sync_time_with_ntp():
        DISPLAY_BUFFER = 'Failed to connect'

    else:
        DISPLAY_BUFFER = 'Synced'
    yield 2
    yield False


def process_host_page(self):
    global DISPLAY_BUFFER
    DISPLAY_BUFFER = ''
    lcd.clear()

    if not wifi.radio.connected:
        DISPLAY_BUFFER = 'Connect to WiFi\nfirst!'
        yield 2
        yield False

    DISPLAY_BUFFER = 'Not implemented yet'
    yield 2
    yield False


def process_music(self):
    global DISPLAY_BUFFER
    global mixer
    DISPLAY_BUFFER = ''
    lcd.clear()

    if not IS_SD_MOUNTED:
        DISPLAY_BUFFER = 'SD Card unavailable'
        yield 1
        yield False

    # Reset the mixer to new values
    audio.stop()
    mixer = audiomixer.Mixer(channel_count=MUSIC.channel_count, buffer_size=2048, sample_rate=MUSIC.sample_rate, bits_per_sample=MUSIC.bits_per_sample)
    audio.play(mixer)

    mixer.voice[1].level = 1

    mixer.play(MUSIC, voice=1)

    while True:
        DISPLAY_BUFFER = 'Playing: ' + str(mixer.playing)
        if B.mode_pressed():
            mixer.stop_voice(1)
            yield False
        render(self)
        time.sleep(1)
        # yield 1/20

def display_timeout(self):
    global IS_IN_SLEEP
    ms_since_input = 0
    yield
    while True:
        # Check for user input, and reset the timer
        if B.a_pressed() or B.b_pressed() or B.c_pressed() or B.d_pressed() or B.mode_pressed():
            lcd.set_backlight(True)
            IS_IN_SLEEP = False
            ms_since_input = 0
        if ms_since_input >= 200:
            IS_IN_SLEEP = True
            lcd.set_backlight(False)
        else:
            ms_since_input += 1
        yield [pyRTOS.timeout(1/60)]


def write_time_sd(self):
    global LAST_TIME
    global IS_SD_MOUNTED
    if not IS_SD_MOUNTED:
        return
    yield
    while True:
        TK.write_time()
        yield [pyRTOS.timeout(1)]


def update_last_time(self):
    global LAST_TIME
    t = rtc.RTC()
    yield
    while True:
        LAST_TIME = t.datetime
        yield [pyRTOS.timeout(1)]


lcd.print('4')
time.sleep(1)

pyRTOS.add_task(pyRTOS.Task(render, name='render', priority=1))
pyRTOS.add_task(pyRTOS.Task(process, name='process'))
pyRTOS.add_task(pyRTOS.Task(display_timeout, name='display_timeout', priority=255))
pyRTOS.add_task(pyRTOS.Task(write_time_sd, name='write_time', priority=10))
pyRTOS.add_task(pyRTOS.Task(update_last_time, name='update_last_time', priority=2))

pyRTOS.start()
