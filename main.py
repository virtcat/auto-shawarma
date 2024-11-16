# coding: utf-8

import multiprocessing as mp
import queue
import threading
import time
from pynput import keyboard
from typing import Union

import config as conf
import data
import operate
import position as pos
import recognize


m = operate.Mouse()


def log(s: str):
    print(s)


def swm_to_str(s: data.Shawarma):
    return f'swm({int(s.no_cucumber)},{int(s.no_fries)},{int(s.no_molasses)},{int(s.no_sauce)})'

def order_to_str(o: data.Order):
    if o is None:
        return 'None'
    swm = ','.join(swm_to_str(s) for s in o.swm) or '-'
    return f'{swm},cola:({o.cola1},{o.cola2}),fries:{o.fries},juice:{o.juice},kibbeh:{o.kibbeh}'


def refill():
    m.click(*pos.P_STAFF)


def collect_money():
    m.drag(*pos.L_COLLECT_MONEY, 0.3)


def make_swm(s: data.Shawarma):
    if conf.bread_machine == 0:
        m.click(*pos.P_BREAD)
        operate.spin(0.05)
    st = time.time()
    make_time = 0.7
    if s is None or not s.no_molasses:
        make_time += 0.25
        if conf.molasess == 1:
            make_time += 0.25
            m.drag(*pos.P_MOLASSES, *pos.P_MOLASSES_TARGET, 0.25)
            operate.spin(0.05)
        if conf.molasess == 2:
            m.click(*pos.P_MOLASSES)
            operate.spin(0.05)
    for _ in range(conf.add_click):
        m.click(*pos.P_MEAT)
        operate.spin(0.05)
    if s is None or not s.no_cucumber:
        for _ in range(conf.add_click):
            m.click(*pos.P_CUCUMBER)
            operate.spin(0.05)
    if s is None or not s.no_sauce:
        for _ in range(conf.add_click):
            m.click(*pos.P_SAUCE)
            operate.spin(0.05)
    if s is None or not s.no_fries:
        for _ in range(conf.add_click):
            m.click(*pos.P_FRIES)
            operate.spin(0.05)
    operate.spin(max(0.15, st + make_time - time.time()))
    m.drag(*pos.L_BREAD_DRAG, 0.2)


def prepare_cola():
    if conf.cup_upgrade < 1:
        m.click(*pos.P_CUP)
        time.sleep(0.03)
        m.click(*pos.P_CUP)
        time.sleep(0.3)
    if conf.cup_upgrade < 2:
        m.click(*pos.P_COLA1_BUTTON)
        time.sleep(0.03)
        m.click(*pos.P_COLA2_BUTTON)


def prepare_fries1(c: int = 3):
    for _ in range(c):
        m.click(*pos.P_CARTON)
        time.sleep(0.03)


def prepare_fries2(i: int = 0):
    if conf.carton_upgrade == 1:
        m.drag(*pos.P_CARTONS[i], *pos.P_FRIES, 0.2)
    elif conf.carton_upgrade == 2:
        m.click(*pos.P_CARTONS[i])


def serve_target(i: int):
    return pos.plus(pos.R_ORDER[i][0], pos.P_ORDER_REL)


def serve_cola_fries(i: int, o: data.Order, fries: list = None):
    target = serve_target(i)
    if o.fries > 0 and fries is not None:
        for j in range(min(o.fries, len(fries))):
            m.drag(*fries[j], *target, 0.2)
            operate.spin(0.04)
    if o.cola1:
        m.drag(*pos.P_COLA1, *target, 0.16)
        operate.spin(0.04)
    if o.cola2:
        m.drag(*pos.P_COLA2, *target, 0.16)
        operate.spin(0.04)


def serve_swm(i: int, o: data.Order, swm: list = None):
    target = serve_target(i)
    if swm is not None:
        for s_order in o.swm:
            for j in range(len(swm)):
                if swm[j] is not None and s_order == swm[j][1]:
                    m.drag(*swm[j][0], *target, 0.2)
                    swm[j] = None
                    operate.spin(0.04)
                    break


def serve(i: int, o: data.Order, fries: list = None, swm: list = None):
    target = serve_target(i)

    for _ in range(o.juice):
        m.drag(*pos.P_JUICE, *target, 0.2)
        operate.spin(0.04)
    for _ in range(o.kibbeh):
        m.drag(*pos.P_KIBBEH, *target, 0.2)
        operate.spin(0.04)

    serve_cola_fries(i, o, fries)

    serve_swm(i, o, swm)


def equal_order(old: data.Order, new: data.Order):
    if old is None or new is None:
        return old is None and new is None
    if old.cola1 != new.cola1 \
            or old.cola2 != new.cola2 \
            or old.fries != new.fries \
            or old.juice != new.juice \
            or old.kibbeh != new.kibbeh \
            or old.beggar != new.beggar:
        return False
    if len(old.swm) != len(new.swm):
        return False
    for old_swm, new_swm in zip(old.swm, new.swm):
        if old_swm != new_swm:
            return False
    return True


def merge_order(old: data.Order, new: data.Order):
    if old is None:
        return new
    if new is None:
        return old
    o = data.Order()
    o.cola1 = max(old.cola1, new.cola1)
    o.cola2 = max(old.cola2, new.cola2)
    o.fries = max(old.fries, new.fries)
    o.juice = max(old.juice, new.juice)
    o.kibbeh = max(old.kibbeh, new.kibbeh)
    o.beggar = old.beggar or new.beggar
    if len(old.swm) < len(new.swm):
        o.swm = new.swm
    elif len(old.swm) > len(new.swm):
        o.swm = old.swm
    else:
        for old_swm, new_swm in zip(old.swm, new.swm):
            s = data.Shawarma()
            s.no_cucumber = old_swm.no_cucumber or new_swm.no_cucumber
            s.no_fries    = old_swm.no_fries    or new_swm.no_fries
            s.no_molasses = old_swm.no_molasses or new_swm.no_molasses
            s.no_sauce    = old_swm.no_sauce    or new_swm.no_sauce
            o.swm.append(s)
    return o


def background_process(res: mp.Queue, cmd: mp.Queue):
    log('>> Background process start')
    r = recognize.Recognizer()
    scr = recognize.Screen()
    scr.locate_game()
    if scr.pc:
        pos.relocate_customers()
    t = time.time()
    while True:
        now = time.time()
        sleep_time = max(0.3 + t - now, 0.05)
        time.sleep(sleep_time)
        t = time.time()
        try:
            c = cmd.get_nowait()
            if c == 'q':
                log('>> Background process exit')
                break
        except queue.Empty:
            pass
        if res.qsize() > 100:
            continue

        now = time.time()
        img_customer = scr.grab_game_customer()
        orders = []
        for i in range(conf.customer_num):
            orders.append(r.order(img_customer, i, True))
        res.put((now, orders))


ctl_exit: bool = False
ctl_work: bool = False
ctl_auto: int = 1

cmd_queue = queue.Queue()


def main_loop():
    global ctl_work
    global ctl_auto

    scr = recognize.Screen()
    r = recognize.Recognizer()

    t_beggar = 0
    t_refill: float = 0.0
    t_fryer: float = 0.0
    t_cola: float = 0.0
    t_carton: float = 0.0
    t_collect: float = 0.0
    t_make: float = 0.0

    last_img = None
    img = None
    now = 0.0

    process = None
    process_res = mp.Queue()
    process_cmd = mp.Queue()
    swm_next = []
    packed_record = []

    log('>> Main loop start')

    while True:
        time.sleep(0.1)
        if ctl_exit:
            process_cmd.put('q')
            if process is not None and process.is_alive():
                process.join()
            log('>> Main loop exit')
            break

        command = None
        while not cmd_queue.empty():
            command = cmd_queue.get()
        if command == '9':
            ctl_work = False
            log('Stop working')
        elif command in ['0', '-', '=']:
            idx = ['0', '-', '='].index(command)
            if scr.locate_game():
                if scr.pc:
                    pos.relocate_customers()
                m.locate(*scr.rect[0], scr.ratio)
                ctl_auto = idx
                img = None
                orders = [{} for _ in range(conf.customer_num)]
                swm_next = []
                packed_record = []
                ctl_work = True
                if ctl_auto == 2:
                    process_res = mp.Queue()
                    process_cmd = mp.Queue()
                    process = mp.Process(target=background_process, args=(process_res, process_cmd))
                    process.start()
                else:
                    process_cmd.put('q')
                log('Start in <{}> mode'.format(['Manual', 'Semi-auto', 'Auto'][idx]))
            else:
                ctl_work = False
                log('Fail to locate! Stop working.')
        if not ctl_work:
            process_cmd.put('q')
            continue

        last_img = img
        img = None
        now = time.time()

        # High priority operations
        if ctl_auto > 0:
            img = scr.grab_game()

            if conf.thief_upgrade < 2:
                thief = r.thief(img)
                if thief:
                    log('> Thief!')
                    for i in range(5):
                        m.click(thief[0] + 10, thief[1] + 40)
                        time.sleep(0.03)
                    continue

            if ctl_auto == 1:
                beggar = r.beggar(img)
                if beggar:
                    if time.time() - t_beggar > 10:
                        log('> Beggar!')
                        for i in range(3):
                            m.click(beggar[0] + 30, beggar[1] + 20)
                            time.sleep(0.03)
                            t_beggar = time.time()
                        continue

        # Response to command if exist
        if command is not None:
            if command == 'd':
                collect_money()
            elif command == 'a':
                refill()
            elif command in ['s', 'q', 'w', 'e', 'r']:
                swm = data.Shawarma()
                if conf.optional_ingredient:
                    if command == 'q':
                        swm.no_molasses = True
                    elif command == 'w':
                        swm.no_cucumber = True
                    elif command == 'e':
                        swm.no_sauce = True
                    elif command == 'r':
                        swm.no_fries = True
                make_swm(swm)
            elif command == 't':
                prepare_cola()
            elif command == 'f':
                prepare_fries1()
            elif command == 'v':
                for i in range(3):
                    prepare_fries2(i)
                    time.sleep(0.05)
            elif command in ['1', '2', '3', '4', '5']:
                i = int(command) - 1
                if i >= conf.customer_num:
                    continue
                if img is None:
                    img = scr.grab_game()
                order = r.order(img, i)
                fries = r.carton_full(img)
                swm = r.packed(img)
                if order is not None:
                    serve(i, order, fries, swm)

        # Low priority operations
        if ctl_auto > 0 and img is not None:
            # Get grilled shawarma to prevent it from burned
            if conf.grill_upgrade == 1:
                packed = r.packed(img)
                grill = r.grill_done(img)
                if len(packed) < 3 and len(grill) > 0:
                    for g in grill:
                        m.drag(g[0], g[1] + 20, g[0] - 200, g[1] + 20, 0.2)
                        if conf.package_upgrade == 0:
                            log('Not support!')
                        if conf.package_upgrade == 1:
                            time.sleep(0.25)
                            m.click(*pos.P_PACK)
                        time.sleep(0.05)
                    continue

            # Refill ingredients
            if t_refill + 32 < now or r.juice(img) < 2 or r.kibbeh(img) < 3:
                if t_refill + 10 < now:
                    refill()
                    t_refill = now
                    continue

            # Prepare drinks
            if conf.drink_upgrade > 0 and t_cola < now:
                cola = r.cola(img)
                if cola[0] == 0 or cola[1] == 0:
                    t_cola = now + 2
                    if conf.drink_upgrade == 1:
                        t_cola += 4
                    prepare_cola()
                    continue

            # Prepare fries
            if conf.carton_upgrade in [1, 2] and t_carton < now:
                carton_empty = r.carton_empty(img)
                carton_full = r.carton_full(img)
                count = len(carton_full) + len(carton_empty)
                if count == 0:
                    t_carton = now + 3
                    prepare_fries1(3 - count)
                    continue
                if len(carton_empty) >= 2:
                    amount_fries = r.amount_fries(img)
                    if amount_fries > 0.2:
                        t_carton = now + 6 
                        for c in carton_empty:
                            if conf.carton_upgrade == 1:
                                m.drag(c[0], c[1], *pos.P_FRIES, 0.2)
                            if conf.carton_upgrade == 2:
                                m.click(c[0], c[1])
                            time.sleep(0.05)
                        continue

            # Fry potatoes
            if conf.potato_upgrade == 0:
                if not r.fryer(img):
                    m.long_press(*pos.P_POTATO, 1.2)
                    continue
            if conf.fryer_upgrade < 2 and t_fryer + 6 < now and r.amount_fries(img) < 0.2:
                m.click(*pos.P_FRYER)
                t_fryer = now
                continue

            # Collect money regularly
            if conf.thief_upgrade < 2 and t_collect + 12 < now:
                t_collect = now
                collect_money()
                continue

        # Full automatic operations
        if ctl_auto == 2 and img is not None and last_img is not None:
            while True:
                try:
                    t_grab, res = process_res.get_nowait()
                except queue.Empty:
                    break
                for i in range(conf.customer_num):
                    o = res[i]
                    if t_grab <= orders[i].get('last_diff', 0):
                        continue
                    if o is None:
                        if orders[i].get('last_diff', 0) + 6 < t_grab:
                            orders[i] = {}
                    elif orders[i].get('create', 0) == 0:
                        orders[i] = {
                            'o': o,
                            'o_new': None,
                            'o_new_time': 0,
                            'create': t_grab,
                            'last_diff': t_grab,
                            'last_recog': t_grab,
                            'last_serve': t_grab,
                            'queue': 0}
                    else:
                        if not equal_order(o, orders[i]['o']):
                            if equal_order(o, orders[i]['o_new']):
                                if orders[i]['o_new_time'] + 4.0 < t_grab:
                                    orders[i]['o'] = o
                                    orders[i]['o_new'] = None
                            else:
                                orders[i]['o_new'] = o
                                orders[i]['o_new_time'] = t_grab
                            orders[i]['o'] = merge_order(o, orders[i]['o'])
                            orders[i]['last_diff'] = t_grab
                        orders[i]['last_recog'] = t_grab

            sort_list = [(orders[i]['create'], i) for i in range(len(orders)) if orders[i]]
            sort_list.sort()

            if len(swm_next) == 0:
                old = []
                if len(packed_record) == 5:
                    for s in packed_record[0]:
                        flag = True
                        for i in range(1, 5):
                            if s not in packed_record[i]:
                                flag = False
                        if flag:
                            old.append(s)
                for _, i in sort_list:
                    if orders[i]['queue'] > 0 and orders[i]['queue'] + 24 > now:
                        continue
                    if orders[i]['last_diff'] + 0.6 > orders[i]['last_recog']:
                        continue
                    swm_add = orders[i]['o'].swm
                    if conf.optional_ingredient:
                        swm_add = []
                        for s in orders[i]['o'].swm:
                            if not any(s == x[1] for x in old):
                                swm_add.append(s)
                    swm_next.extend(swm_add)
                    log(f'>> Append order {i}, num {len(swm_add)}: ' \
                        + ', '.join(swm_to_str(s) for s in swm_add))

                    orders[i]['queue'] = now
                    if len(swm_next) >= 2:
                        break
                if len(swm_next) > 0:
                    packed_record.append(packed)
                    packed_record = packed_record[-5:]

            if len(swm_next) > 0 and t_make + 0.6 < now and r.amount_fries(img) > 0.1:
                grill = r.grill(img)
                if len(grill) < 3:
                    s = swm_next[0]
                    swm_next = swm_next[1:]
                    make_swm(s)
                    t_make = time.time()
                    continue
            do_serve = False
            packed = r.packed(img)
            for _, i in sort_list:
                if orders[i]['last_serve'] + 1.5 < now:
                    if orders[i]['last_diff'] + 1.2 > orders[i]['last_recog']:
                        continue
                    o: data.Shawarma = orders[i]['o']
                    if orders[i]['last_serve'] <= orders[i]['create'] and o.cola1 + o.cola2 + o.fries > 0:
                        fries = r.carton_full(img)
                        serve_cola_fries(i, o, fries)
                        orders[i]['o'] = data.Order()
                        orders[i]['last_diff'] = time.time()
                        orders[i]['last_serve'] = time.time()
                        do_serve = True
                        break
                    if len(packed) > 0 and orders[i]['queue'] > 0 and orders[i]['queue'] + 4 < now:
                        fries = []
                        if o.fries > 0:
                            fries = r.carton_full(img)
                        serve(i, o, fries, packed)
                        if o.beggar:
                            time.sleep(0.3)
                            for _ in range(8 + 8 * (5 - conf.customer_num)):
                                rect = pos.R_ORDER[i]
                                m.click(rect[0][0], rect[0][1] + 240)
                                time.sleep(0.1)
                        orders[i]['o'] = data.Order()
                        orders[i]['last_diff'] = time.time()
                        orders[i]['last_serve'] = time.time()
                        do_serve = True
                        break
            if do_serve:
                continue



def on_press(key: Union[keyboard.Key, keyboard.KeyCode]):
    if key in [keyboard.Key.pause, keyboard.Key.esc]:
        global ctl_exit
        ctl_exit = True
        return False

    if isinstance(key, keyboard.KeyCode):
        cmd_queue.put(key.char)


def on_release(key: Union[keyboard.Key, keyboard.KeyCode]):
    pass


if __name__ == '__main__':
    thread = threading.Thread(target=main_loop)
    thread.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    thread.join()
