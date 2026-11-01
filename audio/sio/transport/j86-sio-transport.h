/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef J86_SIO_TRANSPORT_H
#define J86_SIO_TRANSPORT_H
#include "../session/j86-sio-session.h"
struct j86_sio_transport {
 struct j86_sio_handoff owner;
 void *desc0;
 dma_addr_t desc0_dma;
 unsigned int slots;
};
int j86_sio_transport_claim(struct j86_sio_transport *out);
#endif
