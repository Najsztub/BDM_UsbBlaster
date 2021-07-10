TARGET := m68k-test

# m68k toolchain directory
TOOLCHAIN := /home/mateusz/apps/cross-m68k/bin

CC := $(TOOLCHAIN)/m68k-elf-gcc
OBJCPY := $(TOOLCHAIN)/m68k-elf-objcopy
SIZE := $(TOOLCHAIN)/m68k-elf-size
OBJDUMP := $(TOOLCHAIN)/m68k-elf-objdump

# Add -g for debug
CFLAGS += -m68332 -I. -DREENTRANT_SYSCALLS_PROVIDED -D_REENT_SMALL -Wall -O0 -std=gnu99 
LFLAGS_RAM += -m68332 -nostartfiles -Wl,--script=ram.ld,-Map=$(TARGET).map,--allow-multiple-definition
LFLAGS_ROM += -m68332 -nostartfiles -Wl,--script=rom.ld,-Map=$(TARGET).map,--cref,--allow-multiple-definition

# determine the object files
OBJ := main.o \
	appinit.o \
	glue.o \
	uart.o

AOBJ := crt0.o \
	vector.o

# link the program
$(TARGET).elf: $(OBJ) $(AOBJ) ram.ld
	@echo "---> link project to RAM ..."
	$(CC) $(AOBJ) $(OBJ) $(LIBS) $(LFLAGS_RAM) -o $@

# link the program to Flash
flash: $(AOBJ) $(OBJ) rom.ld
	@echo "---> link project to Flash..."
	$(CC) $(AOBJ) $(OBJ) $(LIBS) $(LFLAGS_ROM) -o $(TARGET).elf

# build rule for assembler files
%.o: %.S
	$(CC) -c $(AFLAGS) -Wa,-adhlns=$<.lst $< -o $@

# create hex,srec and bin files from target
files: $(TARGET).elf
	@echo "---> convert to Intel HEX..."
	$(OBJCPY) -O ihex $(TARGET).elf $(TARGET).hex
	@echo "---> convert to Motorola S-Record..."
	$(OBJCPY) -O srec $(TARGET).elf $(TARGET).srec
	@echo "---> convert to binary image..."
	$(OBJCPY) -O binary $(TARGET).elf $(TARGET).bin	
	@echo "---> Disasm bin file..."
	$(OBJDUMP) -D -b binary --endian=big -mm68k:cpu32 $(TARGET).bin > $(TARGET).asm

# clean project
clean:
	rm -f $(OBJ) $(AOBJ) *.hex *.srec *.bin *.elf *.map *~ *.lst

# calculate sizes for program
size: $(TARGET).elf
	$(SIZE) $(OBJ) $(AOBJ) $(TARGET).elf
	@echo ""
	$(SIZE) -Ax $(TARGET).elf

# print target info
info: $(TARGET).elf
	$(OBJDUMP) --headers $<

