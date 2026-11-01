/* Host regression: a failed finit_module must never become init_module/retry. */
#define main loader_main
#define open mock_open
#define close mock_close
#define syscall mock_syscall
#include "../tools/load-once.c"
#undef main
#undef open
#undef close
#undef syscall
#include <assert.h>
#include <stdarg.h>
static int calls, opened, closed, open_failure;
static const char *wanted;
int mock_open(const char *path, int flags, ...) {
 (void)path; (void)flags; ++opened;
 if (open_failure) { errno=ENOENT; return -1; }
 return 42;
}
int mock_close(int fd) { assert(fd==42); ++closed; return 0; }
long mock_syscall(long number, ...) {
 va_list a; va_start(a,number);
 assert(number==SYS_finit_module); assert(va_arg(a,int)==42);
 assert(!strcmp(va_arg(a,const char *),wanted)); assert(va_arg(a,int)==0);
 va_end(a); ++calls; errno=EIO; return -1;
}
int main(void) {
 char *args[]={"load-once","probe.ko","allow_ready_probe=1",NULL};
 wanted=""; assert(loader_main(2,args)==EIO);
 assert(calls==1 && opened==1 && closed==1);
 wanted=args[2]; assert(loader_main(3,args)==EIO);
 assert(calls==2 && opened==2 && closed==2);
 open_failure=1; assert(loader_main(3,args)==2);
 assert(calls==2 && opened==3 && closed==2);
 assert(loader_main(1,args)==2); assert(calls==2 && opened==3);
 puts("Single finit_module, explicit params and failure paths passed.");
 return 0;
}
