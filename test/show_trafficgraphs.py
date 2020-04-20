'''Testing of the traffic graphs on the scrollbot.
   More of a manual LED verification than a unit test, so not discoverable.'''

import time
from murmeli.scrollbot import ScrollbotGuiNotifier


def test_traffic_graphs():
    '''Slowly animate some traffic graphs'''
    notifier = ScrollbotGuiNotifier(None)
    data = notifier.traffic_data
    minute = 4
    send_recv_values = [(1, 0), (3, 1), (1, 2), (2, 2), (0, 4), (1, 1), (1, 1), (0, 2), (1, 1)]
    for send, recv in send_recv_values:
        minute += 1
        data.set_minute_for_testing(minute)
        data.add_messages_sent(send)
        data.add_messages_received(recv)
    notifier.show_traffic()

    # Allow time to see what's displayed
    time.sleep(3)

    # scroll a bit
    for msg in range(9):
        time.sleep(0.6)
        minute += 1
        data.set_minute_for_testing(minute)
        data.add_messages_sent(msg)
        data.add_messages_received(msg)
        notifier.show_traffic()

    # Allow time to see what's displayed
    time.sleep(3)

    # Stop timer
    notifier.stop()


if __name__ == "__main__":
    test_traffic_graphs()
