import rosbag
import rospy
import argparse
import logging
from datetime import datetime
import roslib.message
from threading import Lock
import signal, sys

logging.basicConfig(level=logging.DEBUG)


class BagRecord(object): 
    def __init__(self, output_bag, topic_infos):
        self.__output_bag = output_bag
        self.__topic_infos = topic_infos
        self.__subscribers = []
        # __Lock is to protect bag write and bag close in two thread. But in Python, it's not necessary. 
        self.__lock = Lock()
        self.__bag = rosbag.Bag(self.__output_bag, 'w')
        signal.signal(signal.SIGINT, self.signal_handler)

    def topic_callback(self, msg, topic): 
        self.__lock.acquire()
        try: 
            self.__bag.write(topic, msg, rospy.Time.now())
        except Exception as e: 
            rospy.logerr('%s' %e)
        self.__lock.release()

    def start_recorder(self): 
        for topic, topic_type in  self.__topic_infos: 
            msg_class = roslib.message.get_message_class(topic_type)
            self.__subscribers.append(rospy.Subscriber(topic, msg_class, self.topic_callback, topic))
    
    def signal_handler(self, sig, frame): 
        rospy.loginfo('End recording by using ctrl+c')
        self.__lock.acquire()
        self.__bag.close()
        self.__lock.release()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='recorder for test cases')
    parser.add_argument('-O', '--output_bag', type=str, help='Set the name of the bag')
    parser.add_argument('-a', '--all', action='store_true', help='record messages in all topics')
    parser.add_argument('extra_args', nargs='*', help=argparse.SUPPRESS)
    args = parser.parse_args()

    rospy.init_node('recorder')
    output_bag = datetime.now().strftime('tc_%Y-%m-%d-%H-%M-%S') + '.bag'
    if args.output_bag: 
        output_bag = args.output_bag + output_bag
    topic_infos = rospy.get_published_topics()

    recorder = BagRecord(output_bag, topic_infos)
    rospy.loginfo("start recording ...")
    recorder.start_recorder()
    rospy.spin()
