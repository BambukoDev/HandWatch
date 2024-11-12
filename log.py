class Log:
    def __init__(self):
        pass

    def log(self, message):
        with open('/sd/log.txt', 'a') as f: # Append to log file
            print(message, file=f)
            f.close()