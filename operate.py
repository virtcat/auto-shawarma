# coding: utf-8

import time
from pynput import mouse

import ctypes
PROCESS_PER_MONITOR_DPI_AWARE = 2
ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)


def spin(t: float):
    start_time = time.perf_counter()
    while True:
        if time.perf_counter() - start_time > t:
            break
        time.sleep(0)


class Mouse:

    def __init__(self, offset_x: int = 0, offset_y: int = 0, ratio: float = 1.0):
        self.c = mouse.Controller()
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.ratio = ratio


    def locate(self, offset_x: int = 0, offset_y: int = 0, ratio: float = 1.0):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.ratio = ratio


    def to_screen(self, x: int, y: int):
        sx = self.offset_x + x * self.ratio
        sy = self.offset_y + y * self.ratio
        return (int(sx), int(sy))


    def click(self, x: int, y: int):
        self.c.position = self.to_screen(x, y)
        spin(0.01)
        self.c.press(mouse.Button.left)
        spin(0.03)
        self.c.release(mouse.Button.left)
        spin(0.01)


    def long_press(self, x: int, y: int, t: float):
        self.c.position = self.to_screen(x, y)
        self.c.press(mouse.Button.left)
        spin(t)
        self.c.release(mouse.Button.left)


    def move_to(self, x1: int, y1: int, x2: int, y2: int, t: float = 0.5):
        self.c.position = self.to_screen(x1, y1)
        dx = int((x2 - x1) * self.ratio)
        dy = int((y2 - y1) * self.ratio)
        ticks = int(t / 0.01)
        for i in range(ticks):
            spin(0.01)
            self.c.move(int(dx / ticks * (i + 1)) - int(dx / ticks * i),
                        int(dy / ticks * (i + 1)) - int(dy / ticks * i))


    def drag(self, x1: int, y1: int, x2: int, y2: int, t: float = 0.5):
        self.c.position = self.to_screen(x1, y1)
        spin(0.01)
        self.c.press(mouse.Button.left)
        spin(0.02)
        self.move_to(x1, y1, x2, y2, t - 0.12)
        spin(0.08)
        self.c.release(mouse.Button.left)
        spin(0.01)


    def set_pos(self, x: int, y: int):
        self.c.position = self.to_screen(x, y)


    def press_left(self):
        self.c.press(mouse.Button.left)


    def release_left(self):
        self.c.release(mouse.Button.left)

