// SPDX-License-Identifier: GPL-2.0-only
/* Exercise the actual patched Labwc handlers with pointer output recorded. */
#include <assert.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>
#include "src/input/touch.c"
struct server server;
struct rcxml rc;
static int left_down,left_up,right_down,right_up,cancels,native_ups,focus_updates,native_downs,native_motions;
void cursor_update_focus(void){focus_updates++;}
uint32_t wlr_seat_touch_notify_down(struct wlr_seat *seat,struct wlr_surface *surface,uint32_t time,int32_t id,double x,double y){native_downs++;return 1;}
void wlr_seat_touch_notify_motion(struct wlr_seat *seat,uint32_t time,int32_t id,double x,double y){native_motions++;}
void wlr_cursor_warp_absolute(struct wlr_cursor *cursor,struct wlr_input_device *device,double x,double y){cursor->x=x*768;cursor->y=y*1024;}
struct wlr_seat_client *wlr_seat_client_for_wl_client(struct wlr_seat *seat,struct wl_client *client){static struct wlr_seat_client value;return &value;}
void wlr_seat_touch_notify_cancel(struct wlr_seat *seat,struct wlr_seat_client *client){cancels++;}
uint32_t wlr_seat_touch_notify_up(struct wlr_seat *seat,uint32_t time,int32_t id){native_ups++;return 0;}
void *xzalloc(size_t size){void *p=calloc(1,size);assert(p);return p;}
void cursor_set_visible(struct seat *seat,bool visible){}
void idle_manager_notify_activity(struct wlr_seat *seat){}
void ssd_update_hovered_button(struct wlr_scene_node *node){}
void seat_pointer_end_grab(struct seat *seat,struct wlr_surface *surface){}
void actions_run(struct view *view,struct wl_list *actions,struct cursor_context *ctx){}
struct view *view_from_wlr_surface(struct wlr_surface *surface){return NULL;}
struct wlr_surface *lab_wlr_surface_from_node(struct wlr_scene_node *node){return NULL;}
struct touch_config_entry *touch_find_config_for_device(char *name){static struct touch_config_entry config={.force_mouse_emulation=true};return &config;}
void wlr_cursor_absolute_to_layout_coords(struct wlr_cursor *cursor,struct wlr_input_device *device,double x,double y,double *lx,double *ly){*lx=x*768;*ly=y*1024;}
void cursor_emulate_move_absolute(struct seat *seat,struct wlr_input_device *device,double x,double y,uint32_t time){seat->cursor->x=x*768;seat->cursor->y=y*1024;}
void cursor_emulate_move(struct seat *seat,struct wlr_input_device *device,double dx,double dy,uint32_t time){seat->cursor->x+=dx;seat->cursor->y+=dy;}
void cursor_emulate_button(struct seat *seat,uint32_t button,enum wl_pointer_button_state state,uint32_t time){if(button==BTN_LEFT){if(state)left_down++;else left_up++;}else if(button==BTN_RIGHT){if(state)right_down++;else right_up++;}}
static void reset_counts(void){left_down=left_up=right_down=right_up=focus_updates=0;}
static void down(struct seat *seat,struct wlr_touch *touch,int id){struct wlr_touch_down_event e={.touch=touch,.touch_id=id,.x=.5,.y=.5,.time_msec=10};handle_touch_down(&seat->touch_down,&e);}
static void up(struct seat *seat,struct wlr_touch *touch,int id){struct wlr_touch_up_event e={.touch=touch,.touch_id=id,.time_msec=100};handle_touch_up(&seat->touch_up,&e);}
static void move(struct seat *seat,struct wlr_touch *touch,int id,double x){struct wlr_touch_motion_event e={.touch=touch,.touch_id=id,.x=x,.y=.5,.time_msec=20};handle_touch_motion(&seat->touch_motion,&e);}
static struct touch_point *point(struct seat *seat){return wl_container_of(seat->touch_points.next,(struct touch_point *)0,link);}
int main(void){
 struct seat seat={0};struct wlr_cursor cursor={0};struct wlr_touch touch={0};
 server.wl_display=wl_display_create();assert(server.wl_display);
 wl_list_init(&seat.touch_points);wl_list_init(&rc.mousebinds);wl_signal_init(&touch.base.events.destroy);seat.cursor=&cursor;
 setenv("LABWC_TOUCH_LONG_PRESS_MS","600",1);
 down(&seat,&touch,1);assert(!left_down);up(&seat,&touch,1);assert(left_down==1&&left_up==1&&!right_down);
 reset_counts();down(&seat,&touch,2);handle_hold(point(&seat));assert(!left_down&&right_down==1&&right_up==1);up(&seat,&touch,2);assert(!left_down&&!left_up);
 reset_counts();down(&seat,&touch,3);move(&seat,&touch,3,.6);assert(left_down==1&&!point(&seat)->hold_timer);up(&seat,&touch,3);assert(left_up==1&&!right_down);
 reset_counts();down(&seat,&touch,4);move(&seat,&touch,4,.505);assert(!left_down&&point(&seat)->hold_timer);up(&seat,&touch,4);assert(left_down==1&&left_up==1);
 reset_counts();down(&seat,&touch,5);down(&seat,&touch,6);assert(left_down==2);struct touch_point *p;wl_list_for_each(p,&seat.touch_points,link)assert(!p->hold_timer);up(&seat,&touch,5);up(&seat,&touch,6);assert(left_up==2&&!right_down);
 reset_counts();down(&seat,&touch,7);move(&seat,&touch,7,.6);assert(left_down==1);wl_signal_emit_mutable(&touch.base.events.destroy,&touch.base);assert(left_up==1&&wl_list_empty(&seat.touch_points));
 reset_counts();down(&seat,&touch,8);wl_signal_emit_mutable(&touch.base.events.destroy,&touch.base);assert(!left_down&&!right_down&&wl_list_empty(&seat.touch_points));
 reset_counts();down(&seat,&touch,10);wl_event_loop_dispatch(wl_display_get_event_loop(server.wl_display),650);assert(right_down==1&&!left_down);up(&seat,&touch,10);
 int sockets[2];assert(socketpair(AF_UNIX,SOCK_STREAM,0,sockets)==0);
 struct wl_client *client=wl_client_create(server.wl_display,sockets[0]);assert(client);
 struct wlr_surface surface={0};surface.resource=wl_resource_create(client,&wl_surface_interface,1,0);assert(surface.resource);wl_signal_init(&surface.events.destroy);
 reset_counts();down(&seat,&touch,11);struct touch_point *native=point(&seat);native->surface=&surface;native->pending_press=false;native->surface_destroy.notify=handle_point_surface_destroy;wl_signal_add(&surface.events.destroy,&native->surface_destroy);handle_hold(native);assert(cancels==1&&right_down==1&&!left_down&&focus_updates>0);up(&seat,&touch,11);assert(native_ups==0);
 reset_counts();down(&seat,&touch,12);native=point(&seat);native->surface=&surface;native->pending_press=false;native->surface_destroy.notify=handle_point_surface_destroy;wl_signal_add(&surface.events.destroy,&native->surface_destroy);wl_signal_emit_mutable(&surface.events.destroy,&surface);assert(wl_list_empty(&seat.touch_points)&&!right_down);
 reset_counts();down(&seat,&touch,13);native=point(&seat);native->surface=&surface;native->pending_press=false;native->pending_native=true;native->surface_destroy.notify=handle_point_surface_destroy;wl_signal_add(&surface.events.destroy,&native->surface_destroy);handle_hold(native);assert(right_down==1&&!left_down&&native_downs==0&&cancels==1);up(&seat,&touch,13);assert(native_ups==0);
 reset_counts();down(&seat,&touch,14);native=point(&seat);native->surface=&surface;native->pending_press=false;native->pending_native=true;native->surface_destroy.notify=handle_point_surface_destroy;wl_signal_add(&surface.events.destroy,&native->surface_destroy);up(&seat,&touch,14);assert(native_downs==1&&native_ups==1&&!left_down);
 reset_counts();down(&seat,&touch,15);native=point(&seat);native->surface=&surface;native->pending_press=false;native->pending_native=true;native->surface_destroy.notify=handle_point_surface_destroy;wl_signal_add(&surface.events.destroy,&native->surface_destroy);move(&seat,&touch,15,.505);assert(native_downs==1&&native_motions==0);move(&seat,&touch,15,.6);assert(native_downs==2&&native_motions==1&&!native->hold_timer);up(&seat,&touch,15);assert(native_ups==2);
 wl_client_destroy(client);close(sockets[1]);
 unsetenv("LABWC_TOUCH_LONG_PRESS_MS");reset_counts();down(&seat,&touch,9);assert(left_down==1&&!point(&seat)->hold_timer);up(&seat,&touch,9);assert(left_up==1);
 setenv("LABWC_TOUCH_LONG_PRESS_MS","bad",1);assert(hold_delay()==0);setenv("LABWC_TOUCH_LONG_PRESS_MS","0",1);assert(hold_delay()==0);setenv("LABWC_TOUCH_LONG_PRESS_MS","99999999999999999999999999",1);assert(hold_delay()==0);
 assert(wl_list_empty(&seat.touch_points));wl_display_destroy(server.wl_display);
 puts("PASS: tap, hold without left click, drag, jitter, multi-touch, device/surface removal, real timer, native cancel/deferred tap/scroll, opt-out and invalid settings");
}
