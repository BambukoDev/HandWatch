import board
import digitalio

BUTTON_A_PIN = board.GP21
BUTTON_B_PIN = board.GP20
BUTTON_C_PIN = board.GP19
BUTTON_D_PIN = board.GP18
BUTTON_MODE_PIN = board.GP22

BUTTON_A = digitalio.DigitalInOut(BUTTON_A_PIN)
BUTTON_A.direction = digitalio.Direction.INPUT
BUTTON_A.pull = digitalio.Pull.UP

BUTTON_B = digitalio.DigitalInOut(BUTTON_B_PIN)
BUTTON_B.direction = digitalio.Direction.INPUT
BUTTON_B.pull = digitalio.Pull.UP

BUTTON_C = digitalio.DigitalInOut(BUTTON_C_PIN)
BUTTON_C.direction = digitalio.Direction.INPUT
BUTTON_C.pull = digitalio.Pull.UP

BUTTON_D = digitalio.DigitalInOut(BUTTON_D_PIN)
BUTTON_D.direction = digitalio.Direction.INPUT
BUTTON_D.pull = digitalio.Pull.UP

BUTTON_MODE = digitalio.DigitalInOut(BUTTON_MODE_PIN)
BUTTON_MODE.direction = digitalio.Direction.INPUT
BUTTON_MODE.pull = digitalio.Pull.UP

def a_pressed():
    return not BUTTON_A.value

def b_pressed():
    return not BUTTON_B.value

def c_pressed():
    return not BUTTON_C.value

def d_pressed():
    return not BUTTON_D.value

def mode_pressed():
    return not BUTTON_MODE.value