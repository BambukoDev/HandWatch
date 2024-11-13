import rtc
import time
import json
import ssl, wifi, socketpool, adafruit_requests

class TimeKeep:
    def __init__(self):
        t = rtc.RTC()
        t.datetime = time.struct_time((2024, 11, 4, 21, 30, 0, 0, -1, -1))

    def load_time(self):
        t = rtc.RTC()
        try:
            with open('/sd/time.json', 'r') as f:
                try:
                    j = json.load(f)
                    t.datetime = time.struct_time((j['year'], j['month'], j['day'], j['hour'], j['minute'], j['second'], 0, -1, -1))
                    # print(j['year'], j['month'], j['day'], j['hour'], j['minute'], j['second'])
                except Exception as e:
                    print('Failed to load JSON:' + str(e))
                    f.close()
                    return True
                f.close()
                return False
        except Exception as e:
            print('Failed to load JSON:' + str(e))
            return True


    def write_time(self):
        t = rtc.RTC()
        j = {
            'year': t.datetime.tm_year,
            'month': t.datetime.tm_mon,
            'day': t.datetime.tm_mday,
            'hour': t.datetime.tm_hour,
            'minute': t.datetime.tm_min,
            'second': t.datetime.tm_sec
        }
        with open('/sd/time.json', 'w') as f:
            print(json.dumps(j), file=f, end='')
            f.close()

    def sync_time_with_ntp(self):
        if not wifi.radio.connected:
            return True
        try:
            t = rtc.RTC()
            pool = socketpool.SocketPool(wifi.radio)
            requests = adafruit_requests.Session(pool, ssl.create_default_context())
            response = requests.get('https://api.ipify.org/?format=json')
            j = json.loads(response.text)
            print('Public ip:', j['ip'])
            response = requests.get('https://timeapi.io/api/time/current/ip?ipAddress=' + j['ip'])
            print('Got response:\n', response.text)
            j = json.loads(response.text)
            t = rtc.RTC()
            t.datetime = time.struct_time(
                (j['year'], j['month'], j['day'], j['hour'], j['minute'], j['seconds'], 0, -1, -1))
        except Exception as e:
            print('WiFi NTP Error:', e)
            return True
        return False
