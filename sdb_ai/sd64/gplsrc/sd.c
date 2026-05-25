/* SD.C
 * Main module of SD
 * Copyright (c) 2007 Ladybridge Systems, All Rights Reserved
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 * 
 * START-HISTORY:
 * 31 Dec 23 SD launch - prior history suppressed
 * 15 Jun 24 add bootstrap build option install option -I
 * 02 Jul 24 -i  typeo will hit bootstrap option
 * 08 Aug 24 mab add code to embedded python if EMBED_PYTHON defined 
 * rev 0.9.1 Mar 25 return to single rev track 
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * Command line options (case-insensitive; only leading -options are parsed).
 * Non-option arguments are executed as a single SD command.
 *
 * Single-letter options (see sd_print_usage() for the full list):
 *    -A / -Aname   Query or force account name
 *    -Bn           Telnet binary mode (1=in, 2=out, 4=no negotiation)
 *    -C s!r        Local client pipe connection (Linux)
 *    -D            Diagnostic dump (config)
 *    -I            Bootstrap install (admin)
 *    -K n|ALL      Kill user (admin)
 *    -L            Apply new licence
 *    -M            Dump shared memory
 *    -N            Network connection
 *    -Pn           Phantom command processor
 *    -Q            SDClient / API server mode
 *    -U            List current users
 *
 * Word options:
 *    -CLEANUP      Clean up lost processes
 *    -INTERNAL     Run in internal mode
 *    -QUIET        Suppress entry displays
 *    -RESUME       Resume updates (admin)
 *    -RESTART      Restart SD (admin)
 *    -START        Start SD (admin)
 *    -STOP         Stop SD (admin)
 *    -SUSPEND      Suspend updates (admin)
 *    -TERM type    Set default terminal type (requires argument)
 *
 * Long options:
 *    --HELP        Display usage help
 *    --VERSION     Display revision stamp
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include <setjmp.h>
#include <time.h>
#include <stdarg.h>
/* 20240126 mab add syslog */
#include <syslog.h>

// #define DEBUG /* enables harcoded diagnostic output */

#define Public
#define init(a) = a

#include "sd.h"
#include "revstamp.h"
#include "header.h"
#include "debug.h"
#include "dh_int.h"
#include "tio.h"
#include "config.h"
#include "options.h"
#include "locks.h"
#include "keys.h"

#define BUILD_TARGET (sizeof(void*) == 8 ? "64 Bit" : "32 Bit")

/* Distinct exit codes for sd main (see main() return paths). */
#define EXIT_GENERAL   1
#define EXIT_CONFIG    2
#define EXIT_COMLIN    3
#define EXIT_BIND      4
#define EXIT_SUSPENDED 5
#define EXIT_PCODE     6
#define EXIT_KERNEL    7
#define EXIT_LANGUAGE  8
#define EXIT_INIT      9
#define EXIT_FATAL     10

/* 20240808 mab embedding python? */
#ifdef EMBED_PYTHON
extern void sdext_py(int key, char* Arg);
#endif

bool bind_sysseg(bool create, char *errmsg);
void unbind_sysseg(void);
void dump_sysseg(bool dump_config);

Private jmp_buf sd_exit;

Private bool sd_init(int argc, char * argv[]);
Private void sd_print_usage(void);
Private void check_admin(void);
Private bool comlin(int argc, char *argv[]);
Private bool load_pcode(char *pname, u_char **ptr);

void clean_stop(void);
void dump_pcode_file(void);

/* ====================================================================== */

static void sd_close_syslog(void) { closelog(); }

int main(int argc, char *argv[]) {
  /* 13Jan22 gwb Refactored to remove "goto" calls. */

  int status = EXIT_GENERAL;
  char errmsg[80 + 1];
  int arg;
#define msgsz 256
  char msg[msgsz];

  tio.term_type[0] = '\0';

  /* 20240126 mab add syslog */
  openlog("sd_Log", LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL1);
  atexit(sd_close_syslog);
  syslog(LOG_INFO, "String Database (sd) command line:");
  {
    int pos = snprintf(msg, msgsz, "sd");

    for (arg = 1; arg < argc && pos > 0 && (size_t)pos < msgsz; arg++) {
      int n = snprintf(msg + pos, (size_t)(msgsz - pos), " %s", argv[arg]);

      if (n < 0 || (size_t)n >= (size_t)(msgsz - pos))
        break;
      pos += n;
    }
    syslog(LOG_INFO, "%s", msg);
  }

  set_default_character_maps();
  if (!sd_init(argc, argv)) {
    clean_stop();
    return EXIT_INIT;
  }

  if (!(command_options & CMD_FLASH)) {
    /* Get config file path */
    if (!GetConfigPath(config_path)) {
      clean_stop();
      return EXIT_CONFIG;
    }

    fullpath(config_path, config_path);
  }

  /* Process the command line */
  if (!comlin(argc, argv)) {
    clean_stop();
    return EXIT_COMLIN;
  }

  if (!bind_sysseg(FALSE, errmsg)) {
    fprintf(stderr, "%s\n", errmsg);
    clean_stop();
    return EXIT_BIND;
  }

  if (sysseg->flags & SSF_SUSPEND) {
    fprintf(stderr, "SD is suspended\n");
    clean_stop();
    return EXIT_SUSPENDED;
  }

  /* Disaster exit */
  if (setjmp(sd_exit)) {
    clean_stop();
    return EXIT_FATAL;
  }

  /* Set pcode pointers */

#undef Pcode
/* 
 * The block below is kind of interesting.  The #define functions as a function call that works like
 * this:
 * Given a call like Pcode(chain), the preprocessor is going to emit this:
 * if (!load_pcode("chain", &pcode_chain)) {
 *   clean_stop();
 *   return status;
 * }
  * 
 * Now the line below where pcode.h is included is going to trigger a call to load_pcode() for each
 * line in the pcode.h file that references the Pcode() macro.  It's clever in that you don't need to 
 * somehow specify a static list of pcode value names, you just add them to the include file and they'll
 * get pulled in automatically since the compiler preprocessor will have "unrolled" all of the entries
 * in the pcode.h include file, resulting in them being loaded at run time.
 * 
 * A similar method is used in kernel.h to declare all of the pcode variables via this define:
 * #define Pcode(a) Public u_char* pcode_##a;
 * Public has been defined in sddefs.h as "extern".  Given a call of Pcode(chain), the pre-processor
 * is going to expand that as:
 * extern u_char* pcode_chain;
 * 
 * -gwb
 * 
 */
 
#define Pcode(a)                       \
  if (!load_pcode(#a, &pcode_##a)) {   \
    clean_stop();                      \
    return EXIT_PCODE;                 \
  }
 

#include "pcode.h" /* this loads up all the pcode object code from the "pcode" file. */

  /* Go run the system */
  if (!init_kernel()) {
    clean_stop();
    return EXIT_KERNEL;
  }

  /* Initialize English messages */
  if (!load_language("")) {
    clean_stop();
    return EXIT_LANGUAGE;
  }

#ifdef DEBUG
  dump_pcode_file();
#endif

  kernel(); /* Run the command processor */

  s_free_all(); /* Only really needed for MEMTRACE */

  status = exit_status;

#ifdef EMBED_PYTHON
  {
    char py_shutdown[] = "shutdown";
    sdext_py(SD_PyFinal, py_shutdown); /* if python was used, shut it down */
  }
#endif

  clean_stop();
  return status;
}

void clean_stop(void) {
  /* these functions were originally called at the end of main().
   * I've moved them to their own function in order to remove all of the
   * instances of "goto abort" that were in main().
   * 13Jan22 gwb */

  dh_shutdown();
  unbind_sysseg();
  shut_console();
}

/* ======================================================================
   Initialisation tasks that need to be done very early                   */

Private bool sd_init(int argc, char *argv[]) {
  char cwd[MAX_PATHNAME_LEN + 1];

  (void)argc;
  (void)argv;

  /* Save the current working directory for use by SYSTEM(1024) */

  if (getcwd(cwd, sizeof(cwd)) == NULL) {
    fprintf(stderr, "Unable to determine current directory (%s); using /\n",
            strerror(errno));
    snprintf(cwd, sizeof(cwd), "/");
  }

  entry_dir = k_alloc(MAX_PATHNAME_LEN, (int32_t)(strlen(cwd) + 1));
  if (entry_dir == NULL) {
    fprintf(stderr, "Out of memory saving startup directory\n");
    return FALSE;
  }
  snprintf(entry_dir, (size_t)(strlen(cwd) + 1), "%s", cwd);
  return TRUE;
}

/* ====================================================================== */

Private void sd_print_usage(void) {
  fprintf(stderr, "\nUsage:\n");
  fprintf(stderr, "   sd command [args...]\n");
  fprintf(stderr, "      Execute an SD command (non-option arguments)\n\n");
  fprintf(stderr, "   sd {options}\n");
  fprintf(stderr, "      -A            Query account name\n");
  fprintf(stderr, "      -Aname        Force account name\n");
  fprintf(stderr,
          "      -Bn           Telnet binary mode (1=in, 2=out, 4=no "
          "negotiation)\n");
  fprintf(stderr, "      -CLEANUP      Clean up lost processes\n");
  fprintf(stderr, "      -Cs!r         Local client pipe connection\n");
  fprintf(stderr, "      -D            Diagnostic dump (config)\n");
  fprintf(stderr, "      -I            Bootstrap install\n");
  fprintf(stderr, "      -INTERNAL     Run in internal mode\n");
  fprintf(stderr, "      -K n|ALL      Kill user (admin)\n");
  fprintf(stderr, "      -L            Apply new licence\n");
  fprintf(stderr, "      -M            Dump shared memory\n");
  fprintf(stderr, "      -N            Network connection\n");
  fprintf(stderr, "      -Pn           Phantom command processor\n");
  fprintf(stderr, "      -Q            SDClient / API server mode\n");
  fprintf(stderr, "      -QUIET        Suppress entry displays\n");
  fprintf(stderr, "      -RESUME       Resume updates (admin)\n");
  fprintf(stderr, "      -RESTART      Restart SD (admin)\n");
  fprintf(stderr, "      -START        Start SD (admin)\n");
  fprintf(stderr, "      -STOP         Stop SD (admin)\n");
  fprintf(stderr, "      -SUSPEND      Suspend updates (admin)\n");
  fprintf(stderr, "      -TERM type    Set default terminal type\n");
  fprintf(stderr, "      -U            List current users\n");
  fprintf(stderr, "      --HELP        Show this summary\n");
  fprintf(stderr, "      --VERSION     Report version number\n");
  fprintf(stderr,
          "\nOptions are case-insensitive; only leading -options are "
          "parsed.\n");
}

Private bool comlin(int argc, char *argv[]) {
  int arg;
  char c;
  int16_t bytes;
  int n; /* Fix for Issue #15 - 11Jan22 gwb */
  int RxPipe;
  int TxPipe;

  for (arg = 1; (arg < argc) && (argv[arg][0] == '-'); arg++) {
    if (IsDigit(*(argv[arg] + 1))) {
      forced_user_no = atoi(argv[arg] + 1);
    } else if (!stricmp(argv[arg], "-CLEANUP")) {
      cleanup();
      exit(0);
    } else if (!stricmp(argv[arg], "-INTERNAL")) {
      internal_mode = TRUE;
    } else if (!stricmp(argv[arg], "-QUIET")) {
      command_options |= CMD_QUIET;
    } else if (!stricmp(argv[arg], "-TERM")) {
      if (++arg >= argc) {
        fprintf(stderr, "-TERM requires a terminal type name\n");
        return FALSE;
      }
      snprintf(tio.term_type, sizeof(tio.term_type), "%s", argv[arg]);
    } else if (!stricmp(argv[arg], "-I")) {    
/* 20240702 mab Bootstrap build arg must be exactly "-I" */		  
        /* Bootstrap Install*/
        check_admin();
        is_bootstrap = TRUE;
        internal_mode = TRUE;
        snprintf(command_processor, sizeof(command_processor), "%s", "$BBPROC");

    } else {
      switch (UpperCase(argv[arg][1])) {
        
        case 'A': /* Query account */
          if (argv[arg][2] == '\0') {
            command_options |= CMD_QUERY_ACCOUNT;
          } else {
            /* Points into argv; valid for lifetime of main() only. */
            forced_account = argv[arg] + 2;
          }
          break;
        
        case 'B': /* Telnet binary mode: digit at argv[arg][2] (e.g. -B3) */
          c = argv[arg][2];
          telnet_binary_mode_in = (c & 1) != 0;
          telnet_binary_mode_out = (c & 2) != 0;
          if (c & 4)
            telnet_negotiation = FALSE;
          break;

        case 'D': /* Diagnostic report */
          dump_sysseg(TRUE);
          exit(0);

        case 'K': /* Kill user */
          check_admin();
          if (++arg < argc) {
            if (!stricmp(argv[arg], "ALL"))
              kill_user(NULL);
            else
              kill_user(argv[arg]);
            exit(0);
          }
          fprintf(stderr, "User number, login name or ALL required\n");
          exit(1);

        case 'L': /* Apply new licence */
          command_options |= CMD_APPLY_LICENCE;
          break;

        case 'M': /* Dump memory */
          dump_sysseg(FALSE);
          exit(0);

        case 'P': /* Execute phantom command */
          phantom_user_index = atoi(argv[arg] + 2);
          is_phantom = TRUE;
          connection_type = CN_NONE;
          break;

        case 'Q': /* Start SDClient session (NT style login) */
/* 20240219 mab rebrand VBSRVR to APISRVR */     
          is_sdApiSrvr = TRUE;
          telnet_binary_mode_in = TRUE;
          telnet_binary_mode_out = TRUE;
          break;

        case 'U': /* Show users */
          show_users();
          exit(0);

        case 'C': /* SDLocal client connection */
          connection_type = CN_PIPE;
          if (sscanf(argv[arg], "-C%d!%d", &TxPipe, &RxPipe) != 2) {
            exit(1);
          }
          dup2(RxPipe, 0);
          dup2(TxPipe, 1);
          break;

        case 'N': /* Network server */
          connection_type = CN_SOCKET;
          break;

        case 'R':
          if (!stricmp(argv[arg], "-RESUME")) {
            suspend_resume(FALSE);
            exit(0);
          }

          if (stricmp(argv[arg], "-RESTART") == 0) {
            check_admin();
            if (stop_sd() && start_sd()) {
              printf("SD has been restarted\n");
              exit(0);
            }
            exit(1);
          }

          goto unrecognised;

        case 'S':
          if (!stricmp(argv[arg], "-SUSPEND")) {
            suspend_resume(TRUE);
            exit(0);
          }

          if (stricmp(argv[arg], "-START") == 0) {
            check_admin();
            if (start_sd()) {
              printf("SD (%s) has been started\n", BUILD_TARGET);
              exit(0);
            }
            exit(1);
          }

          if (stricmp(argv[arg], "-STOP") == 0) {
            check_admin();
            if (stop_sd()) {
              printf("SD (%s) has been shut down\n", BUILD_TARGET);
              exit(0);
            }
            exit(1);
          }
          break;

        case '-':
          if (!stricmp(argv[arg], "--HELP")) {
            goto help;
          } else if (!stricmp(argv[arg], "--VERSION")) {
/* rev 0.9.1 Mar 25 return to single rev track */            
            printf("String Database (sd) Version %s %s\n", SD_REV_STAMP, BUILD_TARGET);
            exit(0);
          } else
            goto unrecognised;
          break;

        default:
          goto unrecognised;
      }
    }
  }

  /* Anything else on the command line is considered to be a command
    to be executed.                                                  */

  if (arg < argc) {
    bytes = 0;
    for (n = arg; n < argc; n++) {
      bytes += strlen(argv[n]) + 1;
    }

    single_command = k_alloc(109, bytes);
    if (single_command == NULL) {
      fprintf(stderr, "Out of memory building command line\n");
      return FALSE;
    }
    n = 0;
    while (1) {
      size_t arg_len = strlen(argv[arg]);

      memcpy(single_command + n, argv[arg], arg_len + 1);
      n += (int)arg_len;
      if (++arg == argc)
        break;
      single_command[n++] = ' ';
    }
  }

  /* Start connection */

  switch (connection_type) {
    case CN_SOCKET:
    case CN_PIPE:
    case CN_PORT:
      if (!start_connection(0))
        exit(1);
      break;
    case CN_WINSTDOUT:
      break;
  }

  if (connection_type != CN_SOCKET)
    telnet_negotiation = FALSE;

  return TRUE;

unrecognised:
  fprintf(stderr, "Unrecognised argument '%s'\n", argv[arg]);
help:
  sd_print_usage();
  return FALSE;
}

/* ======================================================================
   Fatal error handler                                                    */

void fatal() {
  longjmp(sd_exit, 1);
}

/* ======================================================================
   dump()  -  General purpose memory dump function                        */

void dump(u_char *addr, int32_t bytes) {
  int32_t i;
  int16_t j;
  u_char c;

  if (addr == NULL || bytes <= 0)
    return;

  for (i = 0; i < bytes; i += 16) {
    /* Offset */

    printf("%08X: ", i);  // was lX -Wformat=2 issue

    /* Hex */

    for (j = 0; j < 16; j++) {
      if (i + j < bytes)
        printf("%02X", addr[i + j]);
      else
        printf("  ");
      if ((j % 4) == 3)
        printf(" ");
    }

    printf(" | ");

    /* Character */

    for (j = 0; (j < 16) && (i + j < bytes); j++) {
      c = *(addr + i + j);
      printf("%c", (c < 32) ? '.' : c);
    }

    printf("\n");
  }

  if (bytes % 16 != 0)
    printf("\n");
}

/* ======================================================================
   check_admin()  -  Check user has admin rights                          */

void check_admin() {
  int16_t in_group(char *group_name);

  if ((geteuid() != 0) && !in_group("admin")) {
    fprintf(stderr, "Command requires administrator privileges\n");
    exit(1);
  }
}

/* ====================================================================== */

Private bool load_pcode(char *pname, u_char **ptr) {
  char u_pname[MAX_PROGRAM_NAME_LEN + 1];
  OBJECT_HEADER *obj;
  int i;
  u_char *pcode;

  pcode = ((u_char *)sysseg) + sysseg->pcode_offset;

  /* Take a local copy of the pcode name and force it to uppercase */

  snprintf(u_pname, sizeof(u_pname), "%s", pname);
  UpperCaseString(u_pname);

  /* Search for this item in the pcode library */
  for (i = 0; i < sysseg->pcode_len;) {
    int32_t stride;

    if (i + (int32_t)sizeof(OBJECT_HEADER) > sysseg->pcode_len) {
      fprintf(stderr, "Pcode is corrupt (%s)\n", u_pname);
      return FALSE;
    }

    obj = (OBJECT_HEADER *)(pcode + i);
    if (obj->magic == HDR_MAGIC_INVERSE) {
      convert_object_header(obj);
    } else if (obj->magic != HDR_MAGIC) {
      fprintf(stderr, "Pcode is corrupt (%s)\n", u_pname);
      return FALSE;
    }

    if (obj->object_size <= 0 || obj->object_size > sysseg->pcode_len - i) {
      fprintf(stderr, "Pcode is corrupt (%s)\n", u_pname);
      return FALSE;
    }

    if (!strcmp(obj->ext_hdr.prog.program_name, u_pname)) { /* Found it */
      *ptr = pcode + i;
      return TRUE;
    }

    stride = (obj->object_size + 3) & ~3;
    if (stride <= 0 || i + stride > sysseg->pcode_len) {
      fprintf(stderr, "Pcode is corrupt (%s)\n", u_pname);
      return FALSE;
    }
    i += stride;
  }

  fprintf(stderr, "Pcode item %s not found\n", u_pname);
  return FALSE;
}

/* END-CODE */
