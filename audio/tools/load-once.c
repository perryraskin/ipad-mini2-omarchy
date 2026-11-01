#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
/* Exactly one finit_module syscall; no fallback, retry, or automatic unload. */
int main(int argc, char **argv) {
 if (argc != 2 && argc != 3) { fprintf(stderr,"usage: load-once MODULE.ko [PARAMETERS]\n"); return 2; }
 int fd=open(argv[1],O_RDONLY|O_CLOEXEC);
 if(fd<0){perror("open");return 2;}
 fprintf(stderr,"load-once: calling finit_module exactly once\n");
 long result=syscall(SYS_finit_module,fd,argc == 3 ? argv[2] : "",0); int saved=errno;
 close(fd);
 if(result<0){fprintf(stderr,"load-once: errno=%d (%s); no retry\n",saved,strerror(saved));return saved>125?1:saved;}
 fprintf(stderr,"load-once: module remains resident\n");return 0;
}
