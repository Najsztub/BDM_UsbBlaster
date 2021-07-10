import cmd, sys, time
import datetime
from BDM import *

from threading import Thread, Event, RLock, Condition

# https://medium.com/greedygame-engineering/an-elegant-way-to-run-periodic-tasks-in-python-61b7c477b679
class PT(Thread):
    def __init__(self, dt, hFunction, lock):
        Thread.__init__(self)
        self.daemon = True
        self.stopped = Event()
        self.dt = dt
        self.execute = hFunction
        self.lock = lock
        self.prev = datetime.datetime.now()

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.wait(self.dt):
            while self.lock.is_set():
                self.lock.wait()
            self.lock.clear()
            self.execute()
            curr = datetime.datetime.now()
            print("Time diff: " + str(curr-self.prev))
            self.prev = curr
            self.lock.set()


def msg():
    print("WTD")


lock = Event()
wtd = PT(.1, msg, lock)
wtd.start()

def thr():
    time.sleep(2)
    print("Waited 2 s")

print(lock == wtd.lock)

for _ in range(20):

    lock.clear()
    # t1 = Thread(target=thr).start()
    thr()
    lock.set()
