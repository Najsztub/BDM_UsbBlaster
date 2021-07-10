#include <stdio.h>

/* Hardware watchdog address */
#define WTD (*((volatile unsigned short *) (0x4f2000)))

int main(int argc, char *argv[])
{
  unsigned short wtd;
  while(1){
    printf("Hello world\n");
    wtd = WTD;
    wtd --;
  };
  //return 0;
}
