#include "asm.h"
#include "mc68332.inc"

  .title "crt0.S"

  .extern SYM(main)
  .extern __stack
  .extern __bss_start
  .extern __text_start
  .extern SYM(init_main)

  .align 2
  .section  .text

__start:
  /* disable all interrupts on startup. */
  nop
  move.w  #0x2700, sr

setup_system_module:
  /* enable supervisor and map the register block to 0xfff000 */
  /*move.w #0x604f,SIMCR*/
  move.w #0x1cf,SIMCR

setup_system_protection:
  /* enable external bus monitor */
  move.b #0x6,SYPCR

setup_clock_module:
  /* set system clock to 16.777 MHz */
  move.w #0x7c0c,SYNCR

setup_cs_pins:
  /* CSBOOT, CS0-CS5 to 16 bit */
  move.w #0x3cff,CSPAR0
  /* CS10, CS9, CS8 --> 8 Bit, CS6 --> ADDR19 */
  move.w #0x03fd,CSPAR1

setup_cs_ram:
  /* CS0 to RAM, 512k */
  move.w #0x2006,CSBAR0
  move.w #0x5830,CSOR0

  /* CS1 to to RAM, 512k */
  move.w #0x2006,CSBAR1
  move.w #0x3830,CSOR1

  /* CS2 to RTC */
  move.w #0x4f00,CSBAR2
  move.w #0x7d70,CSOR2

  /* CS3 to 0x200000 with 64k odd byte */
  move.w #0x8000,CSBAR3
  move.w #0x7830,CSOR3

    /* CS4 to 0x200000 with 64k odd byte */
  move.w #0x8000,CSBAR4
  move.w #0x7830,CSOR4

    /* CS5 to 0x200000 with 64k odd byte */
  move.w #0x2006,CSBAR5
  move.w #0x7830,CSOR5
  
    /* CS6 to 0x200000 with 64k odd byte */
  move.w #0x8000,CSBAR6
  move.w #0x7830,CSOR6
  
    /* CS7 to 0x200000 with 64k odd byte */
  move.w #0x3007,CSBAR7
  move.w #0x78b0,CSOR7
  
    /* CS8 to 0x200000 with 64k odd byte */
  move.w #0x4005,CSBAR8
  move.w #0x7c30,CSOR8
  
    /* CS9  - D/A converter */
  move.w #0x4f10,CSBAR9
  move.w #0x7430,CSOR9
  
    /* CS10 to 0x4f_2000 with watchdog */
  move.w #0x4f20,CSBAR10
  move.w #0x6970,CSOR10

  /* prepare stack and frame pointer. */
  move.l  #__stack, sp
  link    a6, #-8

  /*move.w #0x0,0x4f2000*/

  /* copy vectors to ram */
  jsr SYM(copy_vec)

  /* copy data to ram */
  jsr SYM(copy_data)

  /* clear bss */
  jsr SYM(clear_bss)

  /* initialize hardware. */
  jsr     SYM(init_main)

  /* enable interrupts. */
  move.w  #0x2000, sr

  /* call main(int argc, char *argv[] */
  move.l  #0, -(sp)
  move.l  #0, -(sp)
  move.l  #0, -(sp)
  jsr     SYM(main)
  lea     (sp, 12), sp

  /* stop on exit from main. */
__exit:
  bra __exit
