# coding: utf-8

import cv2
import mss
import numpy
from cv2.typing import MatLike
from typing import List, Optional, Tuple

import config as conf
import data
import position as pos


def match_one(target: MatLike, template: MatLike):
    res = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    return max_val, max_loc


def match_all(target: MatLike, template: MatLike, threshold: float = 0.8
        ) -> List[Tuple[float, Tuple[int, int]]]:
    res = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
    match_locations = numpy.where(res > threshold)
    locations = []
    for x, y in zip(*match_locations[::-1]):
        locations.append((res[y, x], (x, y)))
    locations.sort(key=lambda x: x[0], reverse=True)
    if len(locations) > 20:
        locations = locations[:20]
    keep_locations = []
    for i in range(len(locations)):
        keep = True
        for j in range(i):
            if abs(locations[i][1][0] - locations[j][1][0]) < 6 \
                    and abs(locations[i][1][1] - locations[j][1][1]) < 6:
                keep = False
                break
        if keep:
            keep_locations.append(locations[i])
    return keep_locations


def match_all_not_gray(target: MatLike, template: MatLike, threshold: float = 0.8
        ) -> List[Tuple[float, Tuple[int, int]]]:
    res = match_all(target, template, threshold)
    if len(res) == 0:
        return res
    shape = (template.shape[1], template.shape[0])
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    template_gray = numpy.expand_dims(template_gray, axis=-1).repeat(3, axis=-1)
    keep = []
    for r in res:
        r_gray = match_one(img_slice(target, (r[1], shape)), template_gray)
        if r[0] > r_gray[0]:
            keep.append(r)
    return keep


def img_slice(target: numpy.ndarray, rect: Tuple[Tuple[int, int], Tuple[int, int]]):
    return target[rect[0][1]:(rect[0][1] + rect[1][1]),
                  rect[0][0]:(rect[0][0] + rect[1][0])]


class Screen:

    def __init__(self):
        self.sct = mss.mss()
        self.rect = None
        self.ratio = pos.PROCESS_RATIO
        self.pc = False
        self.t1 = cv2.imread('img/location1.png')
        self.t2 = cv2.imread('img/location2.png')
        self.t3 = cv2.imread('img/location3.png')


    def located(self):
        return self.rect is not None


    def locate_game(self):
        img = numpy.array(self.sct.grab(self.sct.monitors[0]))[:, :, :3]
        img_y, img_x = img.shape[:2]
        ratio_s = 0.5
        while img.shape[1] * ratio_s > 1960:
            ratio_s /= 2
        img_s = cv2.resize(img, (0, 0), fx=ratio_s, fy=ratio_s)
        test_color = numpy.array([110, 110, 110], dtype=numpy.float32)
        img_test = numpy.sqrt(numpy.average((img_s - test_color) ** 2, axis=-1))
        img_test = img_test < 6.0
        test_y, test_x = img_test.shape[:2]
        candidates = []
        stride_x, stride_y = 32, 16
        for ix in range(0, test_x - stride_x, stride_x):
            for iy in range(200, test_y - stride_y, stride_y):
                count = numpy.sum(img_test[iy:(iy + stride_y), ix:(ix + stride_x)])
                if count > stride_x / 2:
                    candidates.append((count, (ix, iy)))
        candidates.sort(key=lambda x: x[0], reverse=True)

        ratio_cand = 1.0
        score = 0.8
        match1 = (0, 0)
        o_stride_x = max(40, int(stride_x / ratio_s))
        o_stride_y = max(40, int(stride_y / ratio_s))
        for c, (ix, iy) in candidates[:12]:
            ox = int(ix / ratio_s)
            oy = int(iy / ratio_s)
            corner = pos.plus((ox, oy), (-o_stride_x, -o_stride_y))
            corner2 = pos.plus(corner, (2 * o_stride_x, 2 * o_stride_y))
            if corner[0] < 0 or corner[1] < 0 or corner2[0] > img_x or corner2[1] > img_y:
                continue
            area = img_slice(img, (corner, (2 * o_stride_x, 2 * o_stride_y)))
            # Test from 0.5x to 2x
            for i in range(-4, 5):
                ratio_test = (2 ** (1/4)) ** i
                t1_temp = cv2.resize(self.t1, (0, 0), fx=ratio_test, fy=ratio_test)
                res = match_one(area, t1_temp)
                if res[0] > score:
                    score = res[0]
                    ratio_cand = ratio_test
                    match1 = pos.plus(corner, res[1])
            if score > 0.96:
                break
        if score < 0.9:
            print('Locate point 1 not detected')
            return False

        vec = pos.minus(pos.LOCATE_POINT2, pos.LOCATE_POINT1)
        expect_t2 = pos.plus(match1, (int(vec[0] * ratio_cand), int(vec[1] * ratio_cand)))
        corner = pos.plus(expect_t2, (-40, -40), (int(-vec[0] * ratio_cand * 0.2), 0))
        corner2 = pos.plus(expect_t2, (80, 80), (int(vec[0] * ratio_cand * 0.2), 0))
        corner2 = min(corner2[0], img_x), min(corner2[1], img_y)
        size = pos.minus(corner2, corner)
        if size[0] < 40 or size[1] < 40:
            print('Locate point 2 area error:', corner, corner2)
            return False
        area2 = img_slice(img, (corner, size))
        t2_temp = cv2.resize(self.t2, (0, 0), fx=ratio_cand, fy=ratio_cand)
        res = match_one(area2, t2_temp)
        if res[0] < 0.8:
            print('Locate point 2 not detected')
            return False
        match2 = pos.plus(corner, res[1])
        ratio = (match2[0] - match1[0]) / (pos.LOCATE_POINT2[0] - pos.LOCATE_POINT1[0])

        vec = pos.minus(pos.LOCATE_POINT3, pos.LOCATE_POINT1)
        expect_t3 = pos.plus(match1, (int(vec[0] * ratio), int(vec[1] * ratio)))
        corner = pos.plus(expect_t3, (-4, -4))
        if corner[0] < 0 or corner[1] < 0:
            print('Locate point 3 area error:', corner)
            return False
        area3 = img_slice(img, (corner, (40, 40)))
        t3_temp = cv2.resize(self.t3, (0, 0), fx=ratio, fy=ratio)
        res = match_one(area3, t3_temp)

        left = int(match1[0] - pos.LOCATE_POINT1[0] * ratio)
        top = int(match1[1] - pos.LOCATE_POINT1[1] * ratio)
        width = int(1920 * ratio)
        if res[0] < 0.8:
            self.pc = True
            width = int((1920 + 180) * ratio)
        height = int(1080 * ratio)
        if left < -8 or top < 8 or left + width > img_x + 8 or top + height > img_y + 8:
            print('Window rect', (left, top), (width, height), 'exceed the screen',  (img_x, img_y))
            return False
        left += self.sct.monitors[0]["left"]
        top += self.sct.monitors[0]["top"]
        self.rect = (left, top), (width, height)
        self.ratio = ratio
        print('>> Location:', self.rect, self.ratio)
        return True


    def grab_game(self):
        if self.rect is None:
            if not self.locate_game():
                return None
        pad = 10
        shot = self.sct.grab({
            "left": self.rect[0][0] + pad, "top": self.rect[0][1] + pad,
            "width": self.rect[1][0] - pad * 2, "height": self.rect[1][1] - pad * 2 })
        img = numpy.array(shot)[:, :, :3]
        img = numpy.pad(img, [(pad, pad), (pad, pad), (0, 0)])
        if abs(self.ratio - 1.0) > 0.001:
            img = cv2.resize(img, (0, 0), fx=1 / self.ratio, fy=1 / self.ratio)
        return img


    def grab_game_customer(self):
        if self.rect is None:
            self.locate_game()
        corner_xy = self.to_screen_xy(*pos.R_CUSTOMER[0])
        width  = int(pos.R_CUSTOMER[1][0] * self.ratio)
        height = int(pos.R_CUSTOMER[1][1] * self.ratio)
        shot = self.sct.grab({
            "left": corner_xy[0], "top": corner_xy[1],
            "width": width, "height": height })
        img = numpy.array(shot)[:, :, :3]
        if abs(self.ratio - 1.0) > 0.001:
            img = cv2.resize(img, (0, 0), fx=1 / self.ratio, fy=1 / self.ratio)
        return img


    def to_screen_xy(self, x: int, y: int):
        sx = self.rect[0][0] + x * self.ratio
        sy = self.rect[0][1] + y * self.ratio
        return int(sx), int(sy)


class Recognizer:

    def __init__(self) -> None:
        self.t_juice = cv2.imread('img/juice.png')
        self.t_kibbeh = cv2.imread('img/kibbeh.png')
        self.t_fryer_empty = cv2.imread('img/fryer_empty.png')
        self.t_fries_full = cv2.imread('img/fries_full.png')
        self.t_fries_empty = cv2.imread('img/fries_empty.png')
        self.t_cola1 = cv2.imread('img/cola1.png')
        self.t_cola2 = cv2.imread('img/cola2.png')
        self.t_cola1_b = cv2.imread('img/cola1_b.png')
        self.t_cola2_b = cv2.imread('img/cola2_b.png')
        self.t_swm_ready = cv2.imread('img/swm_ready.png')
        self.t_swm_grill = cv2.imread('img/swm_grill.png')

        self.t_thief = cv2.imread('img/thief.png')
        self.t_beggar = cv2.imread('img/beggar.png')
        self.t_beggar_run = cv2.imread('img/beggar_run.png')

        self.t_order_swm = cv2.imread('img/order_swm.png')
        self.t_order_swm_h = cv2.imread('img/order_swm_h.png')
        self.t_order_fries = cv2.imread('img/order_fries.png')
        self.t_order_cola1 = cv2.imread('img/order_cola1.png')
        self.t_order_cola2 = cv2.imread('img/order_cola2.png')
        self.t_order_juice = cv2.imread('img/order_juice.png')
        self.t_order_kibbeh = cv2.imread('img/order_kibbeh.png')

        self.t_order_swm_cucumber  = cv2.imread('img/order_swm_cucumber.png')
        self.t_order_swm_fries     = cv2.imread('img/order_swm_fries.png')
        self.t_order_swm_fries1    = cv2.imread('img/order_swm_fries1.png')
        self.t_order_swm_fries2    = cv2.imread('img/order_swm_fries2.png')
        self.t_order_swm_molasses  = cv2.imread('img/order_swm_molasses.png')
        self.t_order_swm_molasses1 = cv2.imread('img/order_swm_molasses1.png')
        self.t_order_swm_molasses2 = cv2.imread('img/order_swm_molasses2.png')
        self.t_order_swm_sauce     = cv2.imread('img/order_swm_sauce.png')


    def swm_ingredient(self, img: MatLike):
        s = data.Shawarma()
        if match_one(img, self.t_order_swm_cucumber)[0] > 0.75:
            s.no_cucumber = True

        if match_one(img, self.t_order_swm_fries)[0] > 0.75:
            s.no_fries = True
        elif match_one(img, self.t_order_swm_fries1)[0] > 0.75:
            s.no_fries = True
        elif match_one(img, self.t_order_swm_fries2)[0] > 0.75:
            s.no_fries = True
        if match_one(img, self.t_order_swm_molasses)[0] > 0.75:
            s.no_molasses = True
        elif match_one(img, self.t_order_swm_molasses1)[0] > 0.75:
            s.no_molasses = True
        elif match_one(img, self.t_order_swm_molasses2)[0] > 0.75:
            s.no_molasses = True

        if match_one(img, self.t_order_swm_sauce)[0] > 0.75:
            s.no_sauce = True
        return s


    def order(self, img: MatLike, i: int, is_customer_area: bool = False):
        rect = pos.R_ORDER[i]
        if is_customer_area:
            rect = (pos.minus(rect[0], pos.R_CUSTOMER[0]), rect[1])
        area = img_slice(img, rect)
        o = data.Order()

        swm_rect = []
        for res in match_all_not_gray(area, self.t_order_swm, 0.8):
            swm_rect.append((
                    pos.plus(rect[0], res[1], (24, 0)), (80, 44)))
        if conf.optional_ingredient:
            for res in match_all_not_gray(area, self.t_order_swm_h, 0.8):
                swm_rect.append((
                    pos.plus(rect[0], res[1], (56, -14)), (80, 44)))
        swm_rect.sort(key=lambda x: x[0][0] + x[0][1])
        for r in swm_rect:
            swm = data.Shawarma()
            if conf.optional_ingredient:
                swm_area = img_slice(img, r)
                swm = self.swm_ingredient(swm_area)
            o.swm.append(swm)

        o.fries = len(match_all(area, self.t_order_fries, 0.8))
        o.cola1 = len(match_all_not_gray(area, self.t_order_cola1, 0.8))
        o.cola2 = len(match_all_not_gray(area, self.t_order_cola2, 0.8))
        o.juice = len(match_all(area, self.t_order_juice, 0.8))
        o.kibbeh = len(match_all_not_gray(area, self.t_order_kibbeh, 0.75))

        if len(o.swm) + o.fries + o.cola1 + o.cola2 + o.juice + o.kibbeh == 0:
            return None
        area = img_slice(img, (pos.plus(rect[0], pos.R_ORDER_THIEF_REL[0]),
                               pos.R_ORDER_THIEF_REL[1]))
        o.beggar = match_one(area, self.t_beggar)[0] > 0.8
        return o


    def juice(self, img: MatLike):
        area = img_slice(img, pos.R_JUICE)
        return len(match_all(area, self.t_juice))


    def kibbeh(self, img: MatLike):
        area = img_slice(img, pos.R_KIBBEH)
        return len(match_all(area, self.t_kibbeh))


    def thief(self, img: MatLike):
        area = img_slice(img, pos.R_THIEF)
        res = match_one(area, self.t_thief)
        if res[0] > 0.8:
            return pos.plus(res[1], pos.R_THIEF[0])
        return None


    def beggar(self, img: MatLike):
        area = img_slice(img, pos.R_THIEF)
        res = match_one(area, self.t_beggar_run)
        if res[0] > 0.8:
            return pos.plus(res[1], pos.R_THIEF[0])
        return None


    def fryer(self, img: MatLike):
        area = img_slice(img, pos.R_FRYER)
        mse = ((area - self.t_fryer_empty) ** 2).mean()
        return mse > 20


    def cola(self, img: MatLike):
        area = img_slice(img, pos.R_COLA)
        state1 = 0
        res1 = match_one(area, self.t_cola1)
        res1b = match_one(area, self.t_cola1_b)
        if res1[0] > 0.9:
            state1 = 2
        elif res1b[0] > 0.92:
            state1 = 1
        state2 = 0
        res2 = match_one(area, self.t_cola2)
        res2b = match_one(area, self.t_cola2_b)
        if res2[0] > 0.9:
            state2 = 2
        elif res2b[0] > 0.92:
            state2 = 1
        return state1, state2


    def carton_full(self, img: MatLike):
        rect = pos.R_CARTON
        area = img_slice(img, rect)
        res_full = match_all(area, self.t_fries_full)
        return [(x[1][0] + rect[0][0] + 40, x[1][1] + rect[0][1] + 40) for x in res_full]


    def carton_empty(self, img: MatLike):
        rect = pos.R_CARTON
        area = img_slice(img, rect)
        res_full = match_all(area, self.t_fries_empty)
        return [(x[1][0] + rect[0][0] + 40, x[1][1] + rect[0][1] + 40) for x in res_full]


    def amount_fries(self, img: MatLike):
        rect_fries = ((1020, 648), (20, 30))
        area_fries = img_slice(img, rect_fries)
        se = numpy.sum((area_fries - numpy.array([95, 95, 95])) ** 2, -1)
        amount_fries = numpy.sum(se > 900) / (20 * 30)
        return amount_fries


    def packed(self, img: MatLike):
        rect = pos.R_READY
        area = img_slice(img, rect)
        swm = []
        for x in match_all(area, self.t_swm_ready):
            s = data.Shawarma()
            if conf.optional_ingredient:
                swm_area = img_slice(img, ((rect[0][0] + x[1][0] + 70, rect[0][1] + x[1][1]), (80, 44)))
                s = self.swm_ingredient(swm_area)
            swm.append((pos.plus(rect[0], x[1]), s))
        swm.sort(key=lambda x: x[0][1])
        return swm


    def grill_done(self, img: MatLike):
        rect = pos.R_GRILL
        area = img_slice(img, rect)
        res = match_all(area, self.t_swm_grill)
        return [(x[1][0] + rect[0][0], x[1][1] + rect[0][1]) for x in res]


    def grill(self, img: MatLike):
        swm = []
        for i in range(3):
            rect = (1512, 812 + i * 52), (32, 16)
            area = img_slice(img, rect)
            mean = area.mean(axis=(0, 1))
            diff = numpy.linalg.norm(area - mean, axis=-1)
            r = (diff > 40).sum() / (rect[1][0] * rect[1][1])
            if r > 0.1:
                rect2 = (1512 + 56, rect[0][1] - 24), (80, 44)
                area2 = img_slice(img, rect2)
                s = self.swm_ingredient(area2)
                swm.append(s)
        return swm


if __name__ == '__main__':
    pass
