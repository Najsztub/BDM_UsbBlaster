import usb.core
import usb.util
import os
import sys
import time


# Parse args
# if len(sys.argv) != 2:
#     print("Usage: loadFlex <input_hex_file>.")
#     sys.exit()

# Find USB Blaster
dev = usb.core.find(idVendor = 0x09fb)
if dev is None:
    print("USB Blaster not found!")
    sys.exit()
else:
    print("USB Blaster found.")

# Configure
# get an endpoint instance
cfg = dev.get_active_configuration()
intf = cfg[(0,0)]

ep = usb.util.find_descriptor(
    intf,
    # match the first OUT endpoint
    custom_match = \
    lambda e: \
        usb.util.endpoint_direction(e.bEndpointAddress) == \
        usb.util.ENDPOINT_OUT)

assert ep is not None

# # Read & parse hexfile
# binData = hexFile(sys.argv[1])
# binData.parseFile()

# Define control bits 
TCK		= (1 << 0) # DCLK
TMS		= (1 << 1) # nCONF
NCE		= (1 << 2) #
NCS		= (1 << 3) #
TDI		= (1 << 4) # DATA0
LED		= (1 << 5) # ENABLE
READ		= (1 << 6) # READ TDO/ CONF_DONE
SHMODE		= (1 << 7) # Byte shift mode <- for passive serial transfer

# Reverse MSB -> LSB
def reverse_bit(num, base=8):
    result = 0
    # while num:
    for _ in range(0, base):
        result = (result << 1) + (num & 1)
        num >>= 1
    return result

def bdm_out(wd):
    out_wd = [False] + [((wd << sh) & 0x8000) == 0x8000 for sh in range(0, 16)]
    # bb = [[TDI+TMS,TDI+TMS, TMS+TCK+TDI,TMS+TCK+TDI, TMS+TDI, TMS] if bt else [TMS,TMS,TMS+TCK, TMS+TCK, TMS, TMS]  for bt in out_wd]
    bb = [[TDI+TMS,TMS+TCK+TDI] if bt else [TMS,TMS+TCK]  for bt in out_wd]
    bb = [j for i in bb for j in i]
    outBytes = ep.write(bb)
    # time.sleep(1 / 1000)

    return outBytes
    
def read_word():
    cmd = [TMS, TMS+TCK, READ + TMS, SHMODE + 2 + READ,0,0] 
    outBytes = ep.write(cmd)
    resp = dev.read(0x81, 64, 100)
    # resp = dev.read(0x81, 64, 100)
    resp = resp[2:]
    # print([hex(x) for x in resp])
    if len(resp) > 0:
        res_word = (resp[2] << 8) + resp[1]
        # ret_resp = [resp[2], sum([((res_word >> (15-bit)) & 1) << bit  for bit in range(0, 16)])]
        ret_resp = [resp[0], reverse_bit(res_word, 16)]
    else:
        ret_resp = [0xff, 0xffff]
    return ret_resp

def read_word1():
    cmd = [TMS, TMS+TCK, TMS+READ] + 16*[TMS+TCK, READ + TMS]
    outBytes = ep.write(cmd)
    resp = dev.read(0x81, 64, 100)
    resp = resp[2:]
    if len(resp) > 0:
        ret_resp = [resp[16] & 1, sum([(resp[(15-bit)] & 1) << bit  for bit in range(0, 16)])]
    else:
        ret_resp = [0xff, 0xffff]
    return ret_resp

def bdm_in(resp=3):
    bb = [read_word() for _ in range(resp)]
    return [j for i in bb for j in i] 

def mem_dump(start, length, word = True):
    print("Mem from %s" % (str(hex(start))))
    bdm_out(0x1900 + word * 0x40)
    bdm_out(start >> 16)
    bdm_out(start & 0xffff)
    print([hex(start)] + [hex((x)) for x in bdm_in(2)])
    for i in range(length-1):
        bdm_out(0x1D00 + word * 0x40)
        print([hex(start + (word + 1)*(i+1))] + [hex((x)) for x in bdm_in(2)])


# Initialize BDM 
RST_BRK = [LED,LED,LED,LED, LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED+TMS]
# RST_BRK = [LED+TMS, LED+TMS, LED+TMS,LED,LED,LED,LED, LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED + TMS+ TCK]
# init_seq = [LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED+TMS, LED + TMS+ TCK, LED + TMS+ TCK, LED + TMS]
RST = [LED,LED,LED,LED, LED+TMS]
# BRK = [TMS+LED, TMS+LED, LED, LED, TMS+LED, TMS+LED]
BRK = [TMS+LED, TMS+LED+TCK]

# resp = dev.read(0x81, 64, 100)

ep.write(RST)
resp = dev.read(0x81, 64, 100)
time.sleep(10 / 1000)

bdm_out(0x0c00)
time.sleep(100 / 1000)

bdm_out(0x0c00)
time.sleep(100 / 1000)

bdm_out(0x0c00)
time.sleep(100 / 1000)


print("Init")

bdm_out(0x2580+8)
print("%s: %s" % ("ATMP", str([hex((x)) for x in bdm_in(4)])))

init_regs = [
    (0xe, 0x0, 0x05),
    (0xf, 0x0, 0x05)
]

for reg in init_regs:
    bdm_out(0x2480+reg[0])
    bdm_out(reg[1])
    bdm_out(reg[2])


init_mem = [
    ('w',0xff_fa00, 0x604f),
    ('w',0xff_fa04, 0x7F01),
    ('b',0xff_fa21, 0x33),
    # CS registers
    ('w', 0xff_fa4a, 0x7c70),
    ('w', 0xff_fa4c, 0x2006),
    ('w', 0xff_fa4e, 0x5830),
    ('w', 0xff_fa50, 0x2006),
    ('w', 0xff_fa52, 0x3830),
    ('w', 0xff_fa54, 0x4f00),
    ('w', 0xff_fa56, 0x7d70),
    ('w', 0xff_fa58, 0x8000),
    ('w', 0xff_fa5a, 0x7830),
    ('w', 0xff_fa5c, 0x8000),
    ('w', 0xff_fa5e, 0x7830),
    ('w', 0xff_fa60, 0x2006),
    ('w', 0xff_fa62, 0x7830),
    ('w', 0xff_fa64, 0x8000),
    ('w', 0xff_fa66, 0x7830),
    ('w', 0xff_fa68, 0x3007),
    ('w', 0xff_fa6a, 0x78b0),
    ('w', 0xff_fa6c, 0x4005),
    ('w', 0xff_fa6e, 0x7c30),
    ('w', 0xff_fa70, 0x4f10),
    ('w', 0xff_fa72, 0x7430),
    ('w', 0xff_fa74, 0x4f20),
    ('w', 0xff_fa76, 0x6970),

    ('w',0xff_FA46, 0x3fd)
    # ('w', 0xff_fa04, 0x7f00)
]

# for reg in init_mem:
#     bdm_out(0x1800 + (reg[0] == 'w') * 0x40)
#     bdm_out(reg[1] >> 16)
#     bdm_out(reg[1] & 0xffff)
#     bdm_out(reg[2])


# def bdm_in(resp=3):
    
#     cmd = resp*[TMS, TMS+TCK, READ + TMS+TCK, TMS, SHMODE + 2 + READ,0,0] 
#     assert len(cmd) <= 63
#     outBytes = ep.write(bytes(cmd))
#     time.sleep(50 / 1000)
#     resp = dev.read(0x81, 64, 100)
#     resp = dev.read(0x81, 64, 100)
#     return resp[2:]

# System regs
# s	0	RPC	Return Program Counter
# 			points where execution will continue
# 	1	PCC	Current Instruction Program Counter
# 			points to first byte of last executed instruction
# 			it contains 00000001 when double bus fault
# 			appears immediately after reset
# 	8	ATEMP	Temporary Register A
# 	9	FAR	Fault Address Register
# 	A	VBR	Vector Base Register
# 	B	SR	Status Register
# 	C	USP	User Stack Pointer
# 	D	SSP	Supervisor Stack Pointer
# 	E	SFC	Source alternate function type of bus cycle
# 			MOVES instruction and BDM memory transfers
# 	F	DFC	Destination alternate function of bus cycle

sys_regs = [
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

print("System regs:\n")
for reg in sys_regs:
    bdm_out(0x2580+reg[2])
    print("%s, %s: %s" % (reg[1], reg[0], str([hex((x)) for x in bdm_in(3)])))

# ROM - code
mem_dump(start = 0x0_0400, length=8) 

# RAM
mem_dump(start = 0x20_0000, length=8) 

mem_dump(start = 0x30_0000, length=8)

mem_dump(start = 0x40_0000, length=8)

mem_dump(start = 0x80_0000, length=8)

# RTC ??
# https://www.digchip.com/datasheets/parts/datasheet/152/RTC62423-pdf.php
mem_dump(start = 0x4f_0000, length=16, word=True) 

mem_dump(start = 0x4f_1000, length=8)

# WTD pin
mem_dump(start = 0x4f_2000, length=8) 

mem_dump(start = 0xff_fa00, length=32) # CS regs
mem_dump(start = 0xff_fa44, length=32) # CS regs

# print("A/D Regs")
# for i in range(16):
#     bdm_out(0x2180+i)
#     print([hex((x)) for x in bdm_in()])

bdm_out(0x0c00)
# init_seq = [LED + TMS+ TCK]
# ep.write(bytes(init_seq))
# time.sleep(50 / 1000)