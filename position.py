# coding: utf-8

from typing import Optional, Tuple

import config as conf



LOCATE_POINT1 = 102, 940
LOCATE_POINT2 = 1882, 924
LOCATE_POINT3 = 18, 80

PROCESS_RATIO = 1.0


# Coordinates for customers

R_CUSTOMER = (500, 190), (1410, 360)
R_THIEF = (500, 380), (1400, 100)

R_ORDER = [((610 + 278 * i, 190), (100, 360)) for i in range(5)]
if conf.customer_num == 3:
    R_ORDER = [((700 + 372 * i, 190), (100, 360)) for i in range(3)]
elif conf.customer_num == 4:
    R_ORDER = [((660 + 338 * i, 190), (100, 360)) for i in range(4)]
R_ORDER_THIEF_REL = (-80, 200), (60, 40)
R_ORDER_SWM_H_REL = 0
R_ORDER_SWM_V_REL = 0
P_ORDER_REL = -36, 300


def relocate_customers():
    global R_CUSTOMER
    R_CUSTOMER = (500, 190), (1630, 360)
    global R_THIEF
    R_THIEF = (500, 380), (1630, 100)
    global R_ORDER
    if conf.customer_num == 3:
        R_ORDER = [((690 + 374 * i, 190), (100, 360)) for i in range(3)]
    elif conf.customer_num == 4:
        R_ORDER = [((658 + 336 * i, 190), (100, 360)) for i in range(4)]
    elif conf.customer_num == 5:
        R_ORDER = [((626 + 324 * i, 190), (100, 360)) for i in range(5)]


# Coordinates for table objects

R_READY = (1120, 770), (308, 180)
R_GRILL = (1120 + 272, 770), (308, 180)

R_CARTON = (1620, 744), (244, 66)
R_KIBBEH = (1124, 618), (218, 108)
R_JUICE = (228, 790), (180, 104)


P_STAFF = 144, 580
P_PACK = 728, 872
P_BREAD = 528, 888
P_MOLASSES = 166, 888
P_MOLASSES_TARGET = 890, 848
P_MEAT = 476, 708
P_CUCUMBER = 628, 708
P_SAUCE = 808, 708
P_FRIES = 988, 708

P_JUICE = 330, 840
P_KIBBEH = 1308, 656

P_CARTON = 1660, 910
P_CARTONS = [(1660 + i * 100, 800) for i in range(3)]

P_POTATO = 1860, 640
P_FRYER = 1690, 606

P_CUP = 1782, 912
P_COLA1_BUTTON = 1422, 576
P_COLA2_BUTTON = 1506, 576
P_COLA1 = 1420, 700
P_COLA2 = 1510, 700


L_BREAD_DRAG = 966, 920, 966, 720
L_COLLECT_MONEY = 500, 580, 1600, 580


# Tool functions

def plus(a: Tuple[int, int], b: Tuple[int, int], c: Optional[Tuple[int, int]] = None):
    x = a[0] + b[0]
    y = a[1] + b[1]
    if c is not None:
        x += c[0]
        y += c[1]
    return x, y


def minus(a: Tuple[int, int], b: Tuple[int, int]):
    return a[0] - b[0], a[1] - b[1]
