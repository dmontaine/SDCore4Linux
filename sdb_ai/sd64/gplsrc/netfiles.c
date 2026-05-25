/* NETFILES.C
 * Networked file access.
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
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 * Client-side SDNet protocol: host table, packet I/O, and remote file ops.
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include "sdclient.h"
#include "dh_fmt.h"
#include "sdnet.h"
#include "syscom.h"

#include <sys/wait.h>

#ifdef min
#undef min
#endif
#define min(a, b) (((a) < (b)) ? (a) : (b))

#define DLLEntry

#define MAX_HOSTS 10           /* Simultaneous host connections */
#define MAX_PACKET_BODY (16 * 1024 * 1024) /* Cap incoming packet payload */
#define MAX_SERVER_NAME_LEN 16 /* SD name of server */
#define MAX_HOST_NAME_LEN 32   /* IP address or name */

Private struct {
  int16_t ref_ct;                          /* Zero on spare cell */
  char server_name[MAX_SERVER_NAME_LEN + 1]; /* SD name for this server */
  SOCKET sock;
} host_table[MAX_HOSTS];
Private int16_t host_index;

/* Packet buffer */
#define BUFF_INCR 4096
typedef struct INBUFF INBUFF;
struct INBUFF {
  union {
    struct {
      char message[1];
    } abort;
    struct { /* Error text retrieval */
      char text[1];
    } error;
    struct { /* SDOpen */
      int16_t fno;
    } open;
    struct { /* SDRead, SDReadl, SDReadu */
      char rec[1];
    } read;
    struct { /* SDReadList */
      char list[1];
    } readlist;
    struct { /* SDReadNext */
      char id[1];
    } readnext;
    struct { /* SDRecordlocked */
      int32_t status;
    } recordlocked;
    struct { /* SDIndices */
      char reply[1];
    } indices;
    struct { /* SDSelectList, SDSelectindex, SDSelectindexv */
      char reply[1];
    } selectlist;
    struct { /* SDSelectLeft, SDSelectRight */
      char key[1];
    } selectleft;
  } data;
};

Private INBUFF* buff = NULL;
Private int32_t buff_size;  /* Allocated size of buffer */
Private int32_t buff_bytes; /* Size of received packet */

int16_t server_error;
int32_t remote_status;

Private void close_connection(void);
Private bool message_pair(int type, char* data, int32_t bytes);
Private bool GetResponse(void);
Private bool read_packet(void);
Private bool write_packet(int type, char* data, int32_t bytes);

static bool host_connection_ok(void) {
  return (host_index >= 0 && host_index < MAX_HOSTS &&
          host_table[host_index].ref_ct > 0 &&
          host_table[host_index].sock != INVALID_SOCKET);
}

static int16_t net_clip_id_len(int16_t id_len) {
  if (id_len < 0)
    return 0;
  if (id_len > MAX_ID_LEN)
    return MAX_ID_LEN;
  return id_len;
}

static size_t net_clip_name_len(const char* name, size_t max_len) {
  size_t len;

  if (name == NULL)
    return 0;
  len = strlen(name);
  if (len > max_len)
    len = max_len;
  return len;
}

static bool ensure_buff_size(int32_t need) {
  INBUFF* q;
  int32_t n;

  if (need <= 0 || need > MAX_PACKET_BODY)
    return FALSE;
  if (buff != NULL && need <= buff_size)
    return TRUE;
  n = (need + BUFF_INCR - 1) & ~(BUFF_INCR - 1);
  q = (INBUFF*)malloc((size_t)n);
  if (q == NULL)
    return FALSE;
  free(buff);
  buff = q;
  buff_size = n;
  return TRUE;
}

/* ======================================================================
   net_clearfile()                                                        */

int net_clearfile(FILE_VAR* fvar) {
  struct {
    int16_t fno;
  } ALIGN2 packet;

  if (fvar == NULL)
    return remote_status;
  host_index = fvar->access.net.host_index;
  packet.fno = fvar->access.net.file_no;
  message_pair(SrvrClearfile, (char*)&packet, sizeof(packet));
  return remote_status;
}

/* ======================================================================
   net_close()                                                            */

void net_close(FILE_VAR* fvar) {
  struct {
    int16_t fno;
  } ALIGN2 packet;

  if (fvar == NULL)
    return;

  host_index = fvar->access.net.host_index;
  if (host_index < 0 || host_index >= MAX_HOSTS)
    return;

  packet.fno = ShortInt(fvar->access.net.file_no);

  (void)message_pair(SrvrClose, (char*)&packet, sizeof(packet));

  if (--host_table[host_index].ref_ct == 0)
    close_connection();
  if (host_table[host_index].ref_ct < 0)
    k_error("-ve in net_close");
}

/* ======================================================================
   net_delete()  -  Delete a record via SDNet                             */

int net_delete(FILE_VAR* fvar, char* id, int16_t id_len, bool keep_lock) {
  struct PACKET {
    int16_t fno;
    char id[MAX_ID_LEN];
  } ALIGN2 packet;

  if (fvar == NULL || id == NULL)
    return SV_ON_ERROR;

  host_index = fvar->access.net.host_index;
  id_len = net_clip_id_len(id_len);

  packet.fno = ShortInt(fvar->access.net.file_no);
  memcpy(packet.id, id, (size_t)id_len);
  if (!message_pair((keep_lock) ? SrvrDeleteu : SrvrDelete, (char*)&packet,
                    id_len + 2)) {
    server_error = SV_ON_ERROR;
  }

  process.status = remote_status;

  return server_error;
}

/* ======================================================================
   net_fileinfo()                                                        */

STRING_CHUNK* net_fileinfo(FILE_VAR* fvar, int key) {
  STRING_CHUNK* str;
  int len;
  struct {
    int16_t fno;
    int key;
  } ALIGN2 packet;

  host_index = fvar->access.net.host_index;
  packet.fno = ShortInt(fvar->access.net.file_no);
  packet.key = key;
  message_pair(SrvrFileinfo, (char*)&packet, sizeof(packet));

  process.status = remote_status;
  if (server_error != SV_OK)
    return NULL;

  /* Convert received data to a chunked string */
  len = buff_bytes - offsetof(INBUFF, data.indices.reply);
  ts_init(&str, len);
  ts_copy(buff->data.indices.reply, len);
  ts_terminate();
  return str;
}

/* ======================================================================
   net_filelock()                                                        */

int net_filelock(FILE_VAR* fvar, bool wait) {
  struct {
    int16_t fno;
    int16_t wait;
  } ALIGN2 packet;

  host_index = fvar->access.net.host_index;
  packet.fno = ShortInt(fvar->access.net.file_no);
  packet.wait = ShortInt(wait);
  message_pair(SrvrFilelock, (char*)&packet, sizeof(packet));
  return remote_status;
}

/* ======================================================================
   net_fileunlock()                                                        */

int net_fileunlock(FILE_VAR* fvar) {
  struct {
    int16_t fno;
  } ALIGN2 packet;

  host_index = fvar->access.net.host_index;
  packet.fno = ShortInt(fvar->access.net.file_no);
  message_pair(SrvrFileunlock, (char*)&packet, sizeof(packet));
  return remote_status;
}

/* ======================================================================
   net_indices1()  -  Fetch information about indices                     */

STRING_CHUNK* net_indices1(FILE_VAR* fvar) {
  struct {
    int16_t fno;
  } ALIGN2 packet;
  int len;
  STRING_CHUNK* str;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);

  if (!message_pair(SrvrIndices1, (char*)&packet, sizeof(packet)) ||
      (server_error == SV_ON_ERROR)) {
    return NULL;
  }

  process.status = remote_status;
  if (server_error != SV_OK)
    return NULL;

  /* Convert received data to a chunked string */
  len = buff_bytes - offsetof(INBUFF, data.indices.reply);
  ts_init(&str, len);
  ts_copy(buff->data.indices.reply, len);
  ts_terminate();
  return str;
}

/* ======================================================================
   net_indices2()  -  Fetch information about specific index              */

STRING_CHUNK* net_indices2(FILE_VAR* fvar, char* index_name) {
  struct {
    int16_t fno;
    char index_name[MAX_ID_LEN];
  } ALIGN2 packet;
  STRING_CHUNK* str;
  int len;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);
  if (index_name == NULL)
    return NULL;
  len = (int)net_clip_name_len(index_name, MAX_ID_LEN);
  memcpy(packet.index_name, index_name, (size_t)len);

  if (!message_pair(SrvrIndices2, (char*)&packet, len + 2) ||
      (server_error == SV_ON_ERROR)) {
    return NULL;
  }

  process.status = remote_status;
  if (server_error != SV_OK)
    return NULL;

  /* Convert received data to a chunked string */
  len = buff_bytes - offsetof(INBUFF, data.indices.reply);
  ts_init(&str, len);
  ts_copy(buff->data.indices.reply, len);
  ts_terminate();
  return str;
}

/* ======================================================================
   net_lock()  -  Lock a record on remote system                          */

int net_lock(/* Returns 1000+blocking user if blocked */
             FILE_VAR* fvar,
             char* id,
             int16_t id_len,
             bool update,
             bool no_wait) {
  int16_t flags;
  struct {
    int16_t fno;
    int16_t flags; /* 0x0001 : Update lock */
                     /* 0x0002 : No wait */
    char id[MAX_ID_LEN];
  } ALIGN2 packet;

  if (fvar == NULL || id == NULL)
    return SV_ON_ERROR;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);
  id_len = net_clip_id_len(id_len);
  memcpy(packet.id, id, (size_t)id_len);

  flags = (update) ? 1 : 0;
  if (no_wait)
    flags |= 2;
  packet.flags = ShortInt(flags);

  if (!message_pair(SrvrLockRecord, (char*)&packet, id_len + 4)) {
    server_error = SV_ON_ERROR;
  }

  process.status = remote_status;
  if (server_error == SV_LOCKED)
    process.status += 1000;

  return server_error;
}

/* ======================================================================
   net_mark_mapping()  -  Enable/disable mark mapping                     */

void net_mark_mapping(FILE_VAR* fvar, bool state) {
  struct PACKET {
    int16_t fno;
    int16_t state;
  } ALIGN2 packet;

  host_index = fvar->access.net.host_index;

  /* Set up outgoing packet */

  packet.fno = ShortInt(fvar->access.net.file_no);
  packet.state = ShortInt(state);
  message_pair(SrvrMarkMapping, (char*)&packet, sizeof(packet));
}

/* ======================================================================
   net_open()  -  Open a file on a remote SD server                       */

bool net_open(char* server,      /* Server name */
              char* remote_file, /* account;file of target file */
              FILE_VAR* fvar)    /* File variable to populate */
{
  int server_len;
  FILE* ini_file;
  char section[32 + 1];
  char ini_rec[200 + 1];
  bool found;
  SOCKET sock;
  u_int32_t nInterfaceAddr;
  struct sockaddr_in sock_addr;
  int nPort;
  struct hostent* hostdata;
  char login_data[2 + MAX_USERNAME_LEN + 2 + MAX_USERNAME_LEN];
  char ack_buff;
  int roll;
  char* host;
  char* username;
  char* password;
  int port = 4245;
  bool connected = FALSE;
  bool sock_open = FALSE;
  char mapped_chars[] =
      "PWbfTYR.BZKwm6qX4tH-avjUd0GI18Lx37ehiFSJEn52lMocy9OQDNszAVprkuCg";
  int16_t map_len;
  char c;
  int16_t i;
  int j;
  int k;
  int m;
  int n;
  char* p;
  char* q;
  char* r;

  if (server == NULL || remote_file == NULL || fvar == NULL) {
    process.status = ER_PARAMS;
    return FALSE;
  }

  if (buff == NULL) {
    buff_size = 32768;
    buff = (INBUFF*)malloc((size_t)buff_size);
    if (buff == NULL) {
      process.status = -ER_MEM;
      goto exit_open_networked_file;
    }

    for (i = 0; i < MAX_HOSTS; i++) {
      host_table[i].ref_ct = 0;
      host_table[i].server_name[0] = '\0';
      host_table[i].sock = INVALID_SOCKET;
    }
  }

  if ((server_len = strlen(server)) > MAX_SERVER_NAME_LEN) {
    process.status = ER_HOSTNAME;
    goto exit_open_networked_file;
  }

  /* Have we already got this host open? */

  host_index = -1;
  for (i = 0; i < MAX_HOSTS; i++) {
    if (host_table[i].ref_ct != 0) {
      if (!stricmp(host_table[i].server_name, server)) /* 0256, 0294 */
      {
        host_index = i;
        host_table[host_index].ref_ct++; /* 0294 */
        goto host_open;
      }
    } else {
      if (host_index < 0)
        host_index = i; /* Remember free cell */
    }
  }

  if (host_index < 0) /* 0294 */
  {
    process.status = ER_HOST_TABLE;
    goto exit_open_networked_file;
  }

  /* Use configuration file to transform the server name to its
    corresponding host name and to retrieve the user name, password
    and port number.                                                */

  if ((ini_file = fopen(config_path, FOPEN_READ_MODE)) == NULL) {
    process.status = ER_NO_CONFIG;
    goto exit_open_networked_file;
  }

  found = FALSE;
  section[0] = '\0';
  while (fgets(ini_rec, sizeof(ini_rec), ini_file) != NULL) {
    if ((p = strchr(ini_rec, '\n')) != NULL)
      *p = '\0';

    if ((ini_rec[0] == '#') || (ini_rec[0] == '\0'))
      continue;

    if (ini_rec[0] == '[') {
      if ((p = strchr(ini_rec, ']')) != NULL)
        *p = '\0';
      snprintf(section, sizeof(section), "%s", ini_rec + 1);
      UpperCaseString(section);
      continue;
    }

    if (strcmp(section, "SDNET") == 0) /* [sdnet] items */
    {
      if (!StringCompLenNoCase((char*)ini_rec, (char*)server, server_len) &&
          (ini_rec[server_len] == '=')) {
        /* Found this server */
        found = TRUE;
        break;
      }
    }
  }

  fclose(ini_file);

  if (!found) {
    process.status = ER_SERVER;
    goto exit_open_networked_file;
  }

  p = ini_rec + server_len + 1;
  host = strtok(p, ",");
  username = strtok(NULL, ",");
  password = strtok(NULL, ",");
  if (host == NULL || username == NULL || password == NULL) {
    process.status = ER_SERVER;
    goto exit_open_networked_file;
  }
  if ((p = strchr(host, ':')) != NULL) {
    *p = '\0';
    port = atoi(p + 1);
  }

  if (strchr(host, '.')) {
    nInterfaceAddr = inet_addr(host);
  } else {
    hostdata = gethostbyname(host);
    if (hostdata == NULL) {
      process.status = ER_RESOLVE;
      process.os_error = NetError;
      goto exit_open_networked_file;
    }

    nInterfaceAddr = *((int32_t*)(hostdata->h_addr));
  }

  nPort = htons(port);

  sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock == INVALID_SOCKET) {
    process.status = ER_NOSOCKET;
    process.os_error = NetError;
    goto exit_open_networked_file;
  }
  sock_open = TRUE;

  sock_addr.sin_family = AF_INET;
  sock_addr.sin_addr.s_addr = nInterfaceAddr;
  sock_addr.sin_port = nPort;

  if (connect(sock, (struct sockaddr*)&sock_addr, sizeof(sock_addr))) {
    process.status = ER_CONNECT;
    process.os_error = NetError;
    goto exit_open_networked_file;
  }

  /* Connection established. Make a host table entry */

  connected = TRUE;
  strcpy(host_table[host_index].server_name, server);
  UpperCaseString(host_table[host_index].server_name); /* 0294 */
  host_table[host_index].sock = sock;
  host_table[host_index].ref_ct++; /* 0294 Moved */

  n = TRUE;
  setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, (char*)&n, sizeof(int));

  /* Wait for an Ack character to arrive before we assume the connection
    to be open and working. This is necessary because Linux loses anything
    we send before the SD process is up and running.                       */

  do {
    if (recv(sock, &ack_buff, 1, 0) < 1) {
      process.status = ER_RECV_ERR;
      process.os_error = NetError;
      goto exit_open_networked_file;
    }
  } while (ack_buff != '\x06');

  /* Complete login process */

  /* Set up login data */

  p = login_data;

  n = strlen(username);
  *((int16_t*)p) = ShortInt(n); /* User name len */
  p += 2;

  memcpy(p, (char*)username, n); /* User name */
  p += n;
  if (n & 1)
    *(p++) = '\0';

  q = (char*)password;
  n = strlen(password);
  *((int16_t*)p) = ShortInt(n); /* Password len */
  p += 2;

  /* Copy password, decrypting on the way. This is a very simple encryption. */

  map_len = strlen(mapped_chars);
  roll = 10;
  for (k = 0; k < n; k++) {
    c = *(q++);
    if ((r = strchr(mapped_chars, c)) != NULL) {
      m = r - mapped_chars - roll;
      while (m < 0)
        m += map_len;
      j = m % map_len;
      c = mapped_chars[j];
      roll = c;
    }
    *(p++) = c;
  }
  if (n & 1)
    *(p++) = '\0';

  n = p - login_data;
  if ((!message_pair(SrvrLogin, (char*)login_data, n)) ||
      (server_error != SV_OK)) {
    process.status = ER_LOGIN;
    goto exit_open_networked_file;
  }

  /* Now attempt to attach to SDSYS account */

  if (!message_pair(SrvrAccount, "SDSYS", 5)) {
    process.status = ER_ACCOUNT;
    goto exit_open_networked_file;
  }

host_open:

  /* Now open the file */

  if (!message_pair(SrvrOpenSDNet, (char*)remote_file, strlen(remote_file))) {
    process.status = remote_status;
    goto exit_open_networked_file;
  }

  if (server_error) {
    process.status = remote_status;
    goto exit_open_networked_file;
  }

  /* Set up file variable */

  fvar->type = NET_FILE;
  fvar->access.net.host_index = host_index;
  fvar->access.net.file_no = ShortInt(buff->data.open.fno);

  process.status = 0;

exit_open_networked_file:

  if (process.status != 0) {
    if (connected) {
      if (host_index >= 0 && host_index < MAX_HOSTS &&
          --host_table[host_index].ref_ct == 0)
        close_connection();
    } else if (sock_open && sock != INVALID_SOCKET) {
      closesocket(sock);
    }
  }
  return (process.status == 0);
}

/* ======================================================================
   net_read()  -  Read a record via SDNet                                 */

int net_read(FILE_VAR* fvar,
             char* id,
             int16_t id_len,
             u_int16_t op_flags,
             STRING_CHUNK** str) {
  int16_t mode;
  int32_t rec_len = 0;
  struct {
    int16_t fno;
    char id[MAX_ID_LEN];
  } ALIGN2 packet;

  if (op_flags & P_ULOCK) /* Update lock */
  {
    mode = (op_flags & P_LOCKED) ? SrvrReadu : SrvrReaduw;
  } else if (op_flags & P_LLOCK) /* Shared lock */
  {
    mode = (op_flags & P_LOCKED) ? SrvrReadl : SrvrReadlw;
  } else /* No lock */
  {
    mode = SrvrRead;
  }

  if (fvar == NULL || id == NULL || str == NULL)
    return SV_ON_ERROR;

  host_index = fvar->access.net.host_index;
  id_len = net_clip_id_len(id_len);

  packet.fno = ShortInt(fvar->access.net.file_no);
  memcpy(packet.id, id, (size_t)id_len);

  if (!message_pair(mode, (char*)&packet, id_len + 2)) {
    server_error = SV_ON_ERROR;
  }

  process.status = remote_status;

  if (server_error == SV_OK) {
    /* Convert received data to a chunked string */
    rec_len = buff_bytes - offsetof(INBUFF, data.read.rec);
    ts_init(str, rec_len);
    ts_copy(buff->data.read.rec, rec_len);
    ts_terminate();
  }

  return server_error;
}

/* ======================================================================
   net_readv()  -  Perform a READV via SDNet                              */

int net_readv(FILE_VAR* fvar,
              char* id,
              int16_t id_len,
              int field_no,
              u_int16_t op_flags,
              STRING_CHUNK** str) {
  int32_t rec_len = 0;
  int16_t flags;
  struct {
    int16_t fno;
    int16_t flags;
    int field_no;
    char id[MAX_ID_LEN];
  } ALIGN2 packet;

  if (fvar == NULL || id == NULL || str == NULL)
    return SV_ON_ERROR;

  host_index = fvar->access.net.host_index;
  id_len = net_clip_id_len(id_len);

  packet.fno = ShortInt(fvar->access.net.file_no);

  flags = 0;
  if (op_flags & P_ULOCK)
    flags |= 0x0001;
  if (op_flags & P_LLOCK)
    flags |= 0x0002;
  if (op_flags & P_LOCKED)
    flags |= 0x0004;
  packet.flags = ShortInt(flags);

  packet.field_no = LongInt(field_no);
  memcpy(packet.id, id, (size_t)id_len);

  if (!message_pair(SrvrReadv, (char*)&packet, id_len + 8)) {
    server_error = SV_ON_ERROR;
  }

  process.status = remote_status;

  if (server_error == SV_OK) {
    /* Convert received data to a chunked string */
    rec_len = buff_bytes - offsetof(INBUFF, data.read.rec);
    ts_init(str, rec_len);
    ts_copy(buff->data.read.rec, rec_len);
    ts_terminate();
  }

  return server_error;
}

/* ======================================================================
   net_recordlocked()  -  Test record lock on remote system               */

int net_recordlocked(FILE_VAR* fvar, char* id, int16_t id_len) {
  struct {
    int16_t fno;
    char id[MAX_ID_LEN];
  } ALIGN2 packet;

  if (fvar == NULL || id == NULL)
    return 0;

  host_index = fvar->access.net.host_index;
  id_len = net_clip_id_len(id_len);

  packet.fno = ShortInt(fvar->access.net.file_no);
  memcpy(packet.id, id, (size_t)id_len);

  if (!message_pair(SrvrRecordlocked, (char*)&packet, id_len + 2) ||
      server_error != SV_OK)
    return 0;

  process.status = remote_status;
  return buff->data.recordlocked.status;
}

/* ======================================================================
   net_scanindex()  -  SELECTLEFT/SELECTRIGHT                             */

int net_scanindex(FILE_VAR* fvar,
                  char* index_name,
                  int16_t list_no,
                  DESCRIPTOR* key_descr, /* Null if not returning key */
                  bool right) {
  struct {
    int16_t fno;
    int16_t list_no;
    char index_name[MAX_AK_NAME_LEN];
  } ALIGN2 packet;
  int len;
  STRING_CHUNK* str = NULL;
  int32_t count = 0;
  char* p;

  if (fvar == NULL || index_name == NULL)
    return remote_status;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);
  packet.list_no = ShortInt(list_no);
  len = (int)net_clip_name_len(index_name, MAX_AK_NAME_LEN);
  memcpy(packet.index_name, index_name, (size_t)len);

  if (message_pair((right) ? SrvrSelectRight : SrvrSelectLeft, (char*)&packet,
                   len + 4)) {
    if (key_descr != NULL) {
      len = buff_bytes - offsetof(INBUFF, data.selectleft.key);
      k_put_string(buff->data.selectleft.key, len, key_descr);
    }

    if (remote_status == 0) {
      /* Now retrieve the actual select list */

      if (message_pair(SrvrReadList, (char*)&packet.list_no, 2)) {
        /* Convert received data to a chunked string */
        len = buff_bytes - offsetof(INBUFF, data.readlist.list);
        ts_init(&str, len);
        ts_copy(buff->data.readlist.list, len);
        ts_terminate();

        if (len) {
          count = 1;
          for (p = buff->data.readlist.list; len--; p++) {
            if (*p == FIELD_MARK)
              count++;
          }
        }
      }
    }
  }

  /* Save the list. The caller has already set the data types */

  SelectList(list_no)->data.str.saddr = str;
  SelectCount(list_no)->data.value = count;

  return remote_status;
}

/* ======================================================================
   net_select()  -  Select file, returning id list                        */

int net_select(FILE_VAR* fvar, STRING_CHUNK** str, int32_t* count) {
  struct {
    int16_t fno;
  } ALIGN2 packet;
  int len;
  char* p;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);

  if (!message_pair(SrvrSelectList, (char*)&packet, sizeof(packet)) ||
      (server_error == SV_ON_ERROR)) {
    return SV_ON_ERROR;
  }

  /* Convert received data to a chunked string */
  len = buff_bytes - offsetof(INBUFF, data.selectlist.reply);
  ts_init(str, len);
  ts_copy(buff->data.selectlist.reply, len);
  ts_terminate();

  if (len) {
    *count = 1;
    for (p = buff->data.selectlist.reply; len--; p++) {
      if (*p == FIELD_MARK)
        (*count)++;
    }
  } else
    *count = 0;

  return SV_OK;
}

/* ======================================================================
   net_selectindex()  -  SELECTINDEX, no value                            */

int net_selectindex(FILE_VAR* fvar, char* index_name, STRING_CHUNK** str) {
  struct {
    int16_t fno;
    char index_name[MAX_AK_NAME_LEN];
  } ALIGN2 packet;
  int len;
  int32_t count;
  char* p;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);
  if (index_name == NULL)
    return 0;
  len = (int)net_clip_name_len(index_name, MAX_AK_NAME_LEN);
  memcpy(packet.index_name, index_name, (size_t)len);

  if (!message_pair(SrvrSelectIndexv, (char*)&packet, len + 2) ||
      (server_error == SV_ON_ERROR)) {
    return 0;
  }

  process.status = remote_status;
  if (server_error != SV_OK)
    return 0;

  /* Convert received data to a chunked string */
  len = buff_bytes - offsetof(INBUFF, data.selectlist.reply);
  ts_init(str, len);
  ts_copy(buff->data.selectlist.reply, len);
  ts_terminate();

  if (len) {
    count = 1;
    for (p = buff->data.selectlist.reply; len--; p++) {
      if (*p == FIELD_MARK)
        count++;
    }
  } else
    count = 0;

  return count;
}

/* ======================================================================
   net_selectindexv()  -  SELECTINDEX for specified value                 */

int net_selectindexv(FILE_VAR* fvar,
                     char* index_name,
                     char* value,
                     STRING_CHUNK** str) {
  int len;
  int32_t count;
  char* p;
  struct PACKET {
    int16_t fno;
    int16_t index_name_len;
    char index_name[1];
  } ALIGN2;

  int name_len;
  int value_len;
  int pkt_bytes;

  if (fvar == NULL || index_name == NULL || value == NULL || str == NULL)
    return 0;

  host_index = fvar->access.net.host_index;

  name_len = (int)net_clip_name_len(index_name, MAX_AK_NAME_LEN);
  value_len = (int)net_clip_name_len(value, MAX_ID_LEN);
  pkt_bytes = 4 + name_len + value_len;
  if (!ensure_buff_size(pkt_bytes + 1))
    return 0;

  ((struct PACKET*)buff)->fno = ShortInt(fvar->access.net.file_no);
  ((struct PACKET*)buff)->index_name_len = ShortInt(name_len);
  memcpy(((struct PACKET*)buff)->index_name, index_name, (size_t)name_len);
  p = (char*)(((struct PACKET*)buff)->index_name + name_len);
  memcpy(p, value, (size_t)value_len);
  p += value_len;

  if (!message_pair(SrvrSelectIndexk, (char*)buff, (int32_t)(p - (char*)buff)) ||
      (server_error == SV_ON_ERROR)) {
    return 0;
  }

  process.status = remote_status;
  if (server_error != SV_OK)
    return 0;

  /* Convert received data to a chunked string */
  len = buff_bytes - offsetof(INBUFF, data.selectlist.reply);
  ts_init(str, len);
  ts_copy(buff->data.selectlist.reply, len);
  ts_terminate();

  if (len) {
    count = 1;
    for (p = buff->data.selectlist.reply; len--; p++) {
      if (*p == FIELD_MARK)
        count++;
    }
  } else
    count = 0;

  return count;
}

/* ======================================================================
   net_setindex()  -  SETLEFT/SETRIGHT                                    */

int net_setindex(FILE_VAR* fvar, char* index_name, bool right) {
  struct {
    int16_t fno;
    char index_name[MAX_AK_NAME_LEN];
  } ALIGN2 packet;
  int len;

  host_index = fvar->access.net.host_index;

  packet.fno = ShortInt(fvar->access.net.file_no);
  if (index_name == NULL)
    return remote_status;
  len = (int)net_clip_name_len(index_name, MAX_AK_NAME_LEN);
  memcpy(packet.index_name, index_name, (size_t)len);

  message_pair((right) ? SrvrSetRight : SrvrSetLeft, (char*)&packet, len + 2);

  return remote_status;
}

/* ======================================================================
   net_unlock()  -  Unlock a record on remote system                      */

int net_unlock(FILE_VAR* fvar, char* id, int16_t id_len) {
  int status = SV_OK;
  struct {
    int16_t fno;
    char id[MAX_ID_LEN];
  } ALIGN2 packet;

  if (fvar == NULL || id == NULL)
    return SV_ON_ERROR;

  host_index = fvar->access.net.host_index;
  id_len = net_clip_id_len(id_len);

  packet.fno = ShortInt(fvar->access.net.file_no);
  memcpy(packet.id, id, (size_t)id_len);

  if (!message_pair(SrvrRelease, (char*)&packet, id_len + 2) ||
      (server_error == SV_ON_ERROR)) {
    status = SV_ON_ERROR;
  }

  process.status = remote_status;

  return status;
}

/* ======================================================================
   net_unlock_all()  -  Unlock all records on all remote systems          */

int net_unlock_all() {
  struct {
    int16_t fno;
  } ALIGN2 packet;

  packet.fno = ShortInt(0);

  for (host_index = 0; host_index < MAX_HOSTS; host_index++) {
    if (host_table[host_index].ref_ct) {
      message_pair(SrvrRelease, (char*)&packet, 2);
    }
  }

  return SV_OK;
}

/* ======================================================================
   net_write()  -  Write a record via SDNet                               */

int net_write(FILE_VAR* fvar,
              char* id,
              int16_t id_len,
              STRING_CHUNK* str,
              bool keep_lock) {
  int16_t mode;
  int32_t data_len;
  int bytes;
  char* p;
  struct PACKET {
    int16_t fno;
    int16_t id_len;
    char id[1];
  } ALIGN2;

  if (fvar == NULL || id == NULL)
    return SV_ON_ERROR;

  host_index = fvar->access.net.host_index;
  id_len = net_clip_id_len(id_len);

  data_len = (str != NULL) ? (str->string_len) : 0;

  bytes = (int)(offsetof(struct PACKET, id) + (size_t)id_len + (size_t)data_len);
  if (!ensure_buff_size(bytes)) {
    process.status = -ER_MEM;
    return SV_ON_ERROR;
  }

  ((struct PACKET*)buff)->fno = ShortInt(fvar->access.net.file_no);
  ((struct PACKET*)buff)->id_len = ShortInt(id_len);
  memcpy(((struct PACKET*)buff)->id, id, (size_t)id_len);
  p = ((struct PACKET*)buff)->id + id_len;
  while (str != NULL) {
    memcpy(p, str->data, str->bytes);
    p += str->bytes;
    str = str->next;
  }

  mode = (keep_lock) ? SrvrWriteu : SrvrWrite;
  if ((!message_pair(mode, (char*)buff,
                     offsetof(struct PACKET, id) + id_len + data_len)) ||
      (server_error == SV_ON_ERROR)) {
    return SV_ON_ERROR;
  }

  return SV_OK;
}

/* ======================================================================
   close_connection()                                                     */

Private void close_connection() {
  if (host_index < 0 || host_index >= MAX_HOSTS)
    return;

  if (host_table[host_index].sock != INVALID_SOCKET) {
    (void)write_packet(SrvrQuit, NULL, 0);
    closesocket(host_table[host_index].sock);
    host_table[host_index].sock = INVALID_SOCKET;
  }
  host_table[host_index].ref_ct = 0;
  host_table[host_index].server_name[0] = '\0';
}

/* ======================================================================
   message_pair()  -  Send message and receive response                   */

Private bool message_pair(int type, char* data, int32_t bytes) {
  if (!host_connection_ok())
    return FALSE;

  if (write_packet(type, data, bytes))
    return GetResponse();

  return FALSE;
}

/* ====================================================================== */

Private bool GetResponse() {
  if (!read_packet())
    return FALSE;

  return (server_error != SV_ERROR);
}

/* ======================================================================
   read_packet()  -  Read a SD data packet                                */

Private bool read_packet() {
  int rcvd_bytes;
  int32_t packet_bytes;
  int hdr_read;
  int rcv_len;
  char* p;
  int32_t total_len;

  struct {
    int32_t packet_length;
    int16_t server_error ALIGN2;
    int32_t status ALIGN2;
  } in_packet_header;
#define IN_PKT_HDR_BYTES 10

  if (!host_connection_ok() || buff == NULL)
    return FALSE;

  p = (char*)&in_packet_header;
  hdr_read = 0;
  do {
    rcv_len = IN_PKT_HDR_BYTES - hdr_read;
    rcvd_bytes =
        (int)recv(host_table[host_index].sock, p, (size_t)rcv_len, 0);
    if (rcvd_bytes <= 0)
      return FALSE;
    hdr_read += rcvd_bytes;
    p += rcvd_bytes;
  } while (hdr_read < IN_PKT_HDR_BYTES);

  total_len = LongInt(in_packet_header.packet_length);
  if (total_len < IN_PKT_HDR_BYTES || total_len > MAX_PACKET_BODY + IN_PKT_HDR_BYTES)
    return FALSE;

  packet_bytes = total_len - IN_PKT_HDR_BYTES;
  if (!ensure_buff_size(packet_bytes + 1))
    return FALSE;

  p = (char*)buff;
  buff_bytes = 0;
  while (buff_bytes < packet_bytes) {
    rcv_len = (int)min((int32_t)(buff_size - buff_bytes), (int32_t)16384);
    rcvd_bytes =
        (int)recv(host_table[host_index].sock, p, (size_t)rcv_len, 0);
    if (rcvd_bytes <= 0)
      return FALSE;

    buff_bytes += rcvd_bytes;
    p += rcvd_bytes;
  }

  if (buff_size > buff_bytes)
    ((char*)buff)[buff_bytes] = '\0';

  server_error = ShortInt(in_packet_header.server_error);
  remote_status = LongInt(in_packet_header.status);

  return TRUE;
}

/* ======================================================================
   write_packet()  -  Send SD data packet                                 */

Private bool write_packet(int type, char* data, int32_t bytes) {
  struct {
    int32_t length;
    int16_t type;
  } packet_header;
#define PKT_HDR_BYTES 6
  int bytes_sent;

  if (!host_connection_ok())
    return FALSE;

  packet_header.length = LongInt(bytes + PKT_HDR_BYTES); /* 0272 */
  packet_header.type = ShortInt(type);

  if (send(host_table[host_index].sock, (char*)&packet_header, PKT_HDR_BYTES,
           0) != PKT_HDR_BYTES) {
    return FALSE;
  }

  if (data != NULL) {
    while (bytes > 0) {
      if ((bytes_sent = send(host_table[host_index].sock, data, bytes, 0)) <
          0) {
        return FALSE;
      }

      data += bytes_sent;
      bytes -= bytes_sent;
    }
  }

  return TRUE;
}

/* ======================================================================
   get_sdnet_connections() - Return list of open connections              */

STRING_CHUNK* get_sdnet_connections() {
  STRING_CHUNK* str;
  int i;

  if (buff == NULL)
    return NULL; /* Nothing opened yet */

  ts_init(&str, 128);

  for (i = 0; i < MAX_HOSTS; i++) {
    if (host_table[i].ref_ct) {
      if (str != NULL)
        ts_copy_byte(FIELD_MARK);
      ts_printf("%s\xFD%d", host_table[i].server_name, host_table[i].ref_ct);
    }
  }

  ts_terminate();
  return str;
}

/* END-CODE */
