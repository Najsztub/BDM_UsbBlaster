import usb.core
import usb.util
import sys

from threading import Lock, Thread


# Define control bits
TCK = (1 << 0)  # DCLK
TMS = (1 << 1)  # nCONF
NCE = (1 << 2)
NCS = (1 << 3)
TDI = (1 << 4)  # DATA0
LED = (1 << 5)  # ENABLE
READ = (1 << 6)  # READ TDO/ CONF_DONE
SHMODE = (1 << 7)  # Byte shift mode <- for passive serial transfer


# Initialize BDM 
RST_BRK = [LED,LED,LED,LED, LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED+TMS]
# init_seq = [LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED + TMS+ TCK, LED + TMS+ TCK, LED + TMS]
RST = [LED,LED,LED,LED, LED+TMS]
BRK = [TMS+LED, TMS+LED+TCK]


sys_registers = [
    ('ATEMP', 'Temporary Register A', 8),
    ('RPC', 'Return Program Counter', 0),
    ('PCC', 'Current Instruction Program Counter', 1),
    ('FAR', 'Fault Address Register', 9),
    ('VBR', 'Vector Base Register', 0xa),
    ('SR', 'Status Register', 0xb),
    ('USP', 'User Stack Pointer', 0xc),
    ('SSP', 'Supervisor Stack Pointer', 0xd),
    ('SFC', 'Source alternate function', 0xe),
    ('DFC', 'Destination alternate function', 0xf)
]

def reverse_bit(num, base=8):
    # Reverse MSB -> LSB
    result = 0
    # while num:
    for _ in range(0, base):
        result = (result << 1) + (num & 1)
        num >>= 1
    return result

class BDM:
    def __init__(self):
        # Find USB Blaster
        self.dev = usb.core.find(idVendor=0x09fb)
        if self.dev is None:
            print("USB Blaster not found!")
            sys.exit()
        else:
            print("USB Blaster found.")

        # Configure
        # get an endpoint instance
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        self.ep = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match=lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)

        # Make sure we found an endpoint
        assert self.ep is not None

        self.sys_registers = []

        self.lock = Lock()

        self.run = True

    def bdm_out(self, wd):
        """
        Write word to BDM using bitbanging.
        """
        out_wd = [False] + [((wd << sh) & 0x8000) == 0x8000 for sh in range(0, 16)]
        # bb = [[TDI+TMS,TDI+TMS, TMS+TCK+TDI,TMS+TCK+TDI, TMS+TDI, TMS] if bt else [TMS,TMS,TMS+TCK, TMS+TCK, TMS, TMS]  for bt in out_wd]
        bb = [[TDI+TMS, TMS+TCK+TDI] if bt else [TMS, TMS+TCK] for bt in out_wd]
        bb = [j for i in bb for j in i]
        outBytes = self.ep.write(bb)
        # time.sleep(1 / 1000)
        return outBytes

    def reset(self):
        self.ep.write(RST)

    def brk(self):
        self.ep.write(BRK)

    def read_word(self):
        """
        Read word from BDM. Use UsbBlaster passive serial shift mode to do this.

        Return a list of [response, value]
        """
        cmd = [TMS, TMS + TCK, READ + TMS, SHMODE + 2 + READ, 0, 0]
        outBytes = self.ep.write(cmd)
        resp = self.dev.read(0x81, 64, 100)
        resp = resp[2:]
        # print([hex(x) for x in resp])
        if len(resp) > 0:
            res_word = (resp[2] << 8) + resp[1]
            # ret_resp = [resp[2], sum([((res_word >> (15-bit)) & 1) << bit  for bit in range(0, 16)])]
            ret_resp = [resp[0], reverse_bit(res_word, 16)]
        else:
            ret_resp = [0xff, 0xffff]
        return ret_resp


    def read_word_bb(self):
        """
        Read word from BDM using bitbanging - slower, but gives more control for debugging.
        """
        cmd = [TMS, TMS+TCK, TMS+READ] + 16*[TMS+TCK, READ + TMS]
        outBytes = self.ep.write(cmd)
        resp = self.dev.read(0x81, 64, 100)
        resp = resp[2:]
        if len(resp) > 0:
            ret_resp = [resp[16] & 1, sum(
                [(resp[(15-bit)] & 1) << bit for bit in range(0, 16)])]
        else:
            ret_resp = [0xff, 0xffff]
        return ret_resp


    def bdm_in(self, resp=3):
        """
        Read BDM response <- actual method to use to interface BDM.
        """
        bb = [self.read_word() for _ in range(resp)]
        return [j for i in bb for j in i]
        
    def save_sys_registers(self):
        """
        BDM command to save system registers.
        """
        self.sys_registers = []
        for reg in sys_registers:
            self.bdm_out(0x2580+reg[2])
            sys_reg =  self.bdm_in(3)
            self.sys_registers.append((reg[2], sys_reg[3], sys_reg[5]))

    def restore_sys_registers(self):
        """
        BDM command to restore system registers.
        """
        if len(self.sys_registers) == 0:
            return
        self.lock.acquire()
        for reg in self.sys_registers:
            self.bdm_out(0x2480+reg[0])
            self.bdm_out(reg[1])
            self.bdm_out(reg[2])
        self.lock.release()

    def mwrite(self, address, value, word=True):
        """
        BDM command to write to memory.
        """
        # self.lock.acquire()
        self.bdm_out(0x1800 + word * 0x40)
        self.bdm_out(address >> 16)
        self.bdm_out(address & 0xffff)
        self.bdm_out(value)
        # self.lock.release()


    def mem_dump(self, start, length, word=True):
        """
        BDM command to read from memory.
        """
        print("Mem from %s" % (str(hex(start))))
        self.bdm_out(0x1900 + word * 0x40)
        self.bdm_out(start >> 16)
        self.bdm_out(start & 0xffff)
        print([hex(start)] + [hex((x)) for x in self.bdm_in(2)])
        for i in range(length-1):
            self.bdm_out(0x1D00 + word * 0x40)
            print([hex(start + (word + 1)*(i+1))] + [hex((x)) for x in self.bdm_in(2)])
