import buttons as B
from audiocore import WaveFile
import audiomixer
from lib.lcd.lcd import LCD

class ScrollableList:
    def __init__(self, items: list[tuple]):
        self.items = items
        self.current_index = 0
        self.current_inside_view = 0

    def __iter__(self):
        return self.items

    def render(self):
        out = ''
        i = 0
        for item in self.items[self.current_index:self.current_index + 4]:
            blank = ' '*(20 - (len(item[0]) + 2))
            if i == self.current_inside_view:
                out += chr(0) + ' ' + item[0] + blank
                if B.c_pressed():
                    return self.items[self.current_index + i][1]
            else:
                out += '  ' + item[0] + blank
            i += 1
        return out

    def scroll_to_top(self):
        self.current_index = 0
        self.current_inside_view = 0


    def handle_input(self, mixer: audiomixer.Mixer, click_normal: WaveFile, lcd: LCD):
        if B.b_pressed():
            if mixer is not None:
                mixer.play(click_normal)
            self.current_inside_view += 1
            if self.current_inside_view >= 4:
                self.current_index += 1
                if self.current_index >= len(self.items) - 4:
                    self.current_inside_view = 0
                    self.current_index = 0
            if self.current_inside_view > 3:
                self.current_inside_view = 3
            return True
        if B.a_pressed():
            if mixer is not None:
                mixer.play(click_normal)
            self.current_inside_view -= 1
            if self.current_inside_view < 0:
                self.current_index -= 1
                if self.current_index < 0:
                    self.current_index = len(self.items) - 4
                    self.current_inside_view = 3
            if self.current_inside_view < 0:
                self.current_inside_view = 0
            return True
        return False