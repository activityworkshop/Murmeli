'''LED notification of Murmeli using a Scroll pHAT HD from Pimoroni'''

from PIL import Image
import scrollphathd
from murmeli import guinotification
from murmeli.system import System, Component
from murmeli.scrollbotdata import SendReceiveData
from murmeli.signals import Timer


class ScrollbotGuiNotifier(Component):
    '''Notifier component for system events when Scrollbot is available'''

    def __init__(self, parent):
        Component.__init__(self, parent, System.COMPNAME_GUI)
        self.traffic_data = SendReceiveData()
        print("Using a ScrollbotGuiNotifier for this LED robot system")
        scrollphathd.rotate(180)
        scrollphathd.set_brightness(0.6)
        # regularly refresh display
        self.traffic_timer = Timer(20, self.show_traffic)

    def checked_start(self):
        '''Signal start'''
        self.notify_gui(guinotification.NOTIFY_SYSTEM_STARTING)
        return True

    def stop(self):
        '''Stop the gui component'''
        self.traffic_timer.stop()
        scrollphathd.clear()
        scrollphathd.show()
        Component.stop(self)

    def notify_gui(self, notify_type):
        '''Inform the gui that some event has occurred'''
        print("GUI notify:", notify_type)
        if notify_type == guinotification.NOTIFY_SYSTEM_STARTING:
            self.show_m()
        else:
            if notify_type == guinotification.NOTIFY_MSG_SENT:
                self.traffic_data.add_message_sent()
            elif notify_type == guinotification.NOTIFY_MSG_RECEIVED:
                self.traffic_data.add_message_received()
            self.show_traffic()

    def show_m(self):
        '''Show the Murmeli 'M' logo'''
        main_img = Image.open("images/led_m.bmp")
        for pixx in range(scrollphathd.DISPLAY_WIDTH):
            for pixy in range(scrollphathd.DISPLAY_HEIGHT):
                brightness = self.get_pixel(main_img, pixx, pixy)
                scrollphathd.pixel(pixx, pixy, brightness)
        scrollphathd.show()

    @staticmethod
    def get_pixel(img, pixx, pixy):
        '''Get the value of the specified pixel from the given image'''
        pixval = img.getpixel((pixx, pixy))
        if img.getpalette():
            red, gre, blu = img.getpalette()[pixval:pixval+3]
            pixval = max(red, gre, blu)
        return pixval / 255.0

    def show_traffic(self):
        '''Show the traffic data as a graph'''
        scrollphathd.clear()
        send_data, receive_data = self.traffic_data.get_data()
        # Show sent messages dimmer coming down from top of screen
        for col_index, send_val in enumerate(send_data):
            pixy = min(6, send_val)
            scrollphathd.pixel(col_index, pixy, 0.4)
        # Show received messages brighter coming up from bottom of screen
        for col_index, received_val in enumerate(receive_data):
            pixy = 6 - min(6, received_val)
            scrollphathd.pixel(col_index, pixy, 1.0)
        scrollphathd.show()
