/* sd_ownaddr.c
 * Is an address one of THIS machine's own (S.264)?
 * Copyright (c) 2026 The SD Developers, All Rights Reserved
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
 * 18 Nov 26 dm  S.264 - written (owner, 18 Nov 2026: "yes" to closing it in the code).  An ssh tunnel aimed at this machine's
 *               own network address arrives FROM that address, so !peer_local, which knew only the Unix socket, 127.x and ::1,
 *               called it remote, and an address list holding the machine's own address let anyone with an ssh login reach
 *               SDSYS's API sign-in with the password alone.  A peer whose address is one of this machine's own came from this
 *               machine: a remote host cannot complete a TCP handshake from an address that is ours.
 * END-HISTORY
 *
 * START-DESCRIPTION:
 *
 *   Addresses are compared as BITS (inet_pton), never as text, so no spelling (leading zeros are refused by inet_pton, an
 *   IPv4-mapped IPv6 address is compared as its IPv4 form, IPv6 zero compression in any form) can make two equal addresses
 *   differ or two different ones match.  The interfaces are read fresh at each call (getifaddrs): a sign-in is rare and an
 *   address can change (DHCP).
 *
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include <arpa/inet.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

#include "sd_ownaddr.h"

/* parse ADDR into FAMILY and 16 bytes of OUT (4 used for IPv4); an IPv4-mapped IPv6 address is returned as IPv4.  0 on success */
static int parse_addr(const char* addr, int* family, unsigned char out[16]) {
  struct in_addr a4;
  struct in6_addr a6;
  static const unsigned char mapped[12] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xff, 0xff};

  if ((addr == NULL) || (addr[0] == '\0') || (strlen(addr) > 64))
    return -1;
  if (inet_pton(AF_INET, addr, &a4) == 1) {
    *family = AF_INET;
    memcpy(out, &a4, 4);
    return 0;
  }
  if (inet_pton(AF_INET6, addr, &a6) == 1) {
    if (memcmp(a6.s6_addr, mapped, 12) == 0) {
      *family = AF_INET;
      memcpy(out, a6.s6_addr + 12, 4);
    } else {
      *family = AF_INET6;
      memcpy(out, a6.s6_addr, 16);
    }
    return 0;
  }
  return -1;
}

static int same(int fa, const unsigned char* a, int fb, const unsigned char* b) {
  if (fa != fb)
    return 0;
  return memcmp(a, b, (fa == AF_INET) ? 4 : 16) == 0;
}

int sd_own_address_in(const char* addr, const char* const* own, int n_own) {
  int fa, fb, i;
  unsigned char a[16], b[16];

  if (parse_addr(addr, &fa, a) != 0)
    return -1;
  for (i = 0; i < n_own; i++) {
    if ((own[i] != NULL) && (parse_addr(own[i], &fb, b) == 0) && same(fa, a, fb, b))
      return 1;
  }
  return 0;
}

int sd_own_address(const char* addr) {
  struct ifaddrs* list = NULL;
  struct ifaddrs* p;
  int fa, result = 0;
  unsigned char a[16], b[16];

  if (parse_addr(addr, &fa, a) != 0)
    return -1;
  if (getifaddrs(&list) != 0)
    return -1;
  for (p = list; p != NULL; p = p->ifa_next) {
    if (p->ifa_addr == NULL)
      continue;
    if (p->ifa_addr->sa_family == AF_INET) {
      memcpy(b, &((struct sockaddr_in*)p->ifa_addr)->sin_addr, 4);
      if (same(fa, a, AF_INET, b)) {
        result = 1;
        break;
      }
    } else if (p->ifa_addr->sa_family == AF_INET6) {
      memcpy(b, ((struct sockaddr_in6*)p->ifa_addr)->sin6_addr.s6_addr, 16);
      if (same(fa, a, AF_INET6, b)) {
        result = 1;
        break;
      }
    }
  }
  freeifaddrs(list);
  return result;
}

/* END-CODE */
