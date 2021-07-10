import cmd, sys, time, os, copy
import math
import datetime
from BDM import *

from threading import Thread, Event

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
            # while self.lock.locked():
            #     pass
            self.lock.acquire()
            self.execute()
            # curr = datetime.datetime.now()
            # print("Time diff: " + str(curr-self.prev))
            # self.prev = curr
            self.lock.release()


class BDMShell(cmd.Cmd):
    intro = 'Welcome to the BDM shell.   Type help or ? to list commands.\n'
    prompt = '(BDM) '

    # ----- basic commands -----
    def do_reset(self, arg):
        'Clear the screen and return turtle to center:  RESET'
        
    def do_init(self, arg):
        'Reset Device and stop: INIT'
        self.bdm.ep.write(RST)
        resp = self.bdm.dev.read(0x81, 64, 100)
        time.sleep(10 / 1000)
        self.bdm.save_sys_registers()
        init_registers = [
            (0xe, 0x0, 0x05),
            (0xf, 0x0, 0x05)
        ]
        for reg in init_registers:
            self.bdm.bdm_out(0x2480+reg[0])
            self.bdm.bdm_out(reg[1])
            self.bdm.bdm_out(reg[2])

        # Enable watchdog
        self.bdm.run = False
        self.do_wtd("start")

    def do_run(self, arg):
        'Resume execution: run [ADDRESS]'
        args = arg.split()
        if len(args) == 1:
            data=int(args[0], 0)
            # Set RPC to data
            self.bdm.lock.acquire()
            self.bdm.bdm_out(0x2480)
            self.bdm.bdm_out(data >> 16)
            self.bdm.bdm_out(data & 0xffff)
            self.bdm.lock.release()
        self.close()

    def do_wait(self, arg):
        'Wait for t seconds: wait [seconds]'
        args = arg.split()
        timeout = 1
        if len(args) == 1:
            timeout = float(args[0])
        time.sleep(timeout)
            
    def do_bye(self, arg):
        'Start execution, close the BDM window, and exit:  BYE'
        print('BDM Exits')
        self.close()
        if self.wtd is not None:
            self.wtd.stop()
        return True

    def do_mset(self, arg):
        'Set memory value: mset ADDRESS VALUE [w/b]'
        args = arg.split()
        assert len(args) >= 2
        address=int(args[0], 0)
        data=int(args[1], 0)
        word = True
        if len(args) == 3 and args[2] == 'b':
            word = False
        self.bdm.lock.acquire()
        self.bdm.mwrite(address, data, word)
        self.bdm.lock.release()
        self.bdm.run = False
        

    def do_mget(self, arg):
        'Get memory value: mget ADDRESS [w/b]'
        args = arg.split()
        assert len(args) >= 1
        address=int(args[0], 0)
        word = True
        if len(args) == 2 and args[1] == 'b':
            word = False
        self.bdm.lock.acquire()
        self.bdm.bdm_out(0x1900 + word * 0x40)
        self.bdm.bdm_out(address >> 16)
        self.bdm.bdm_out(address & 0xffff)
        inw = self.bdm.bdm_in(2)
        self.bdm.lock.release()
        print("0x%04x: 0x%04x" % (address, inw[3]))
        self.bdm.run = False

    def do_rset(self, arg):
        'Set register value: rset REG DATA(dw)'
        args = arg.split()
        assert len(args) == 2
        reg=int(args[0], 0)
        data=int(args[1], 0)

        self.bdm.lock.acquire()
        self.bdm.bdm_out(0x2080+reg)
        self.bdm.bdm_out(data >> 16)
        self.bdm.bdm_out(data & 0xffff)
        self.bdm.lock.release()
        self.bdm.run = False

    def do_rsset(self, arg):
        'Set system register value: rset REG DATA(dw)'
        args = arg.split()
        assert len(args) == 2
        reg=int(args[0], 0)
        data=int(args[1], 0)

        self.bdm.lock.acquire()
        self.bdm.bdm_out(0x2480+reg)
        self.bdm.bdm_out(data >> 16)
        self.bdm.bdm_out(data & 0xffff)
        self.bdm.lock.release()
        self.bdm.run = False


    def do_rsdump(self, arg):
        'Print system registers: RSDUMP'
        print("System regs:")  
        self.bdm.run = False
        self.bdm.lock.acquire()
        for reg in sys_registers:
            self.bdm.bdm_out(0x2580+reg[2])
            inr = self.bdm.bdm_in(3)
            print("%s, %s: %s" % (reg[1], reg[0], str([hex(inr[3]), hex(inr[5])])))
        self.bdm.lock.release()

    def do_rdump(self, arg):
        'Print CPU registers: RDUMP'
        print("CPU regs:")  
        self.bdm.lock.acquire()
        for reg in range(16):
            self.bdm.bdm_out(0x2180+reg)
            inr = self.bdm.bdm_in(3)
            if (reg >> 3) > 0:
                reg_type = 'A'
            else:
                reg_type = 'D'
            print("%s%x, %s" % (reg_type, reg & 0x7, str([hex(inr[3]), hex(inr[5])])))
        self.bdm.lock.release()
        self.bdm.run = False


    def do_wtd(self, arg):
        'Start and stop Watchdog'
        args = arg.split()
        if args[0] == 'start':
            # Enable CS10 as WTD
            self.bdm.mwrite(0xff_fa74, 0x4f20)
            self.bdm.mwrite(0xff_fa76, 0x6970)
            self.wtd = PT(0.5, self.wtd_poke, self.bdm.lock)
            self.wtd.start()
        if args[0] == 'stop':
            self.wtd.stop()

    def do_mdump(self, arg):
        'Dump memory contents: mdump ADDRESS LENGTH b/w'
        args=arg.split()
        start=int(args[0], 0)
        length=int(args[1], 0)
        word=True
        if len(args) > 2 and args[2] == 'b': word = False

        self.bdm.run = False

        print("Dumping mem from 0x%04x" % start)

        step = 0x40
        for block in range((length // step)+1):
            self.bdm.lock.acquire()
            self.wtd_poke()
            self.bdm.bdm_out(0x1900 + word * 0x40)
            self.bdm.bdm_out(start >> 16)
            self.bdm.bdm_out(start & 0xffff)
            inw = self.bdm.bdm_in(2)
            print("0x%04x: 0x%04x" % (start, inw[3]))
            if block == (length // step):
                step = length % step
            for i in range(step-1):
                self.bdm.bdm_out(0x1D00 + word * 0x40)
                inw = self.bdm.bdm_in(2)
                print("0x%04x: 0x%04x" % (start + (word + 1)*(i+1), inw[3]))
            self.bdm.lock.release()
            start += step << word
  
            
    def do_mdump_file(self, arg):
        'Dump memory contents to a raw bin file: mdump_file FILE ADDRESS LENGTH b/w'
        args=arg.split()
        start=int(args[1], 0)
        length=int(args[2], 0)
        word=True
        if len(args) > 3 and args[3] == 'b': word = False
        print("Dumping mem from %s" % (str(hex(start))))
        
        self.bdm.run = False

        step = 0x40
        with open(args[0], 'wb') as f:
            for block in range((length // step)+1):
                print('Dumping file 0x%04x/0x%04x\r'%(start, length), end="")
                self.bdm.lock.acquire()
                # with self.bdm.lock:
                self.wtd_poke()   
                self.bdm.bdm_out(0x1900 + word * 0x40)
                self.bdm.bdm_out(start >> 16)
                self.bdm.bdm_out(start & 0xffff)
                inw = self.bdm.bdm_in(2)

                f.write(bytearray(inw[3].to_bytes(2, 'big')))

                if block == (length // step):
                    step = length % step
                for i in range(step-1):
                    self.bdm.bdm_out(0x1D00 + word * 0x40)
                    inw = self.bdm.bdm_in(2)
                    f.write(bytearray(inw[3].to_bytes(2, 'big')))
                self.bdm.lock.release()
                start += step << word
        print("\nEnd.")

    def do_mfill_file(self, arg):
        'TODO: Fill memory contents with a raw bin file: mfill_file FILE ADDRESS '
        args=arg.split()
        start=int(args[1], 0)
        start_0 = copy.copy(start)
        word=True
        
        self.bdm.run = False

        step_b = 0x40
        step_w = (step_b << 1)
        # TODO: Handle except
        file_size = os.path.getsize(args[0])

        print("Fill mem from 0x%04x with 0x%04x bytes" % (start, file_size))

        with open(args[0], 'rb') as f:
            for block in range(math.ceil(file_size / step_b)):
                print('Writing mem at 0x%04x/0x%04x\r'%(start, start_0+file_size), end="")
                self.bdm.lock.acquire()
                self.wtd_poke()   
                self.bdm.mwrite(start, int.from_bytes(f.read(2), byteorder='big'), word=True)

                if block == math.ceil(file_size // step_b):
                    step_b = file_size % step_b
                for i in range((step_b - 2)  >> 1):
                    # Fill mem
                    out_w = int.from_bytes(f.read(2), byteorder='big')
                    self.bdm.bdm_out(0x1C40)
                    self.bdm.bdm_out(out_w)
                start += step_b
                self.bdm.lock.release()
        print("\nEnd.")

    def do_play(self, arg):
        'Playback commands from a file:  play rose.cmd'
        self.close()
        with open(arg) as f:
            self.cmdqueue.extend(f.read().splitlines())

    #####################################################################
    def preloop(self):
        self.bdm = BDM()
        self.wtd = None

    def close(self):
        # if self.wtd is not None:
        #     self.wtd.stop()
        self.bdm.bdm_out(0x0c00)
        self.bdm.run = True


    def wtd_poke(self):
        if self.bdm.run == True: 
            return
        # print('Poke')
        wtd = 0x4f_2000

        self.bdm.bdm_out(0x1940)
        self.bdm.bdm_out(wtd >> 16)
        self.bdm.bdm_out(wtd & 0xffff)
        self.bdm.bdm_in(2)
        

if __name__ == '__main__':
    # Enable optional profiling
    if len(sys.argv) > 1 and sys.argv[1] == "PROFILE":
        import cProfile
        import pstats

        with cProfile.Profile() as pr:
            BDMShell().cmdloop()

        stats = pstats.Stats(pr)
        stats.sort_stats(pstats.SortKey.TIME)
        # stats.print_stats()
        stats.dump_stats(filename='profiling.prof')
    # Run
    else:
        BDMShell().cmdloop()
