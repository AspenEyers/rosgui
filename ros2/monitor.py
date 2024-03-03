#!/usr/bin/env python3
import subprocess
import logging
import threading
import time 
import rclpy
from rclpy.node import Node
from collections import deque
import importlib

class TopicSubscriber(Node):
    def __init__(self, buffer_size=20):
        super().__init__('subscriber_node')
        self.buffer = deque(maxlen=buffer_size)  # Circular buffer
        self.subscriber = None
        self.topic_name = None

    def spin(self):
        rclpy.spin(self)

    def create_dynamic_subscriber(self, topic_name):
        if self.topic_name == topic_name:
            if self.subscriber is not None:
                return
            
        if self.subscriber is not None:
            logging.info(f"Destroying old subscriber")
            self.destroy_subscription(self.subscriber)
            self.subscriber = None  
            self.buffer.clear()
        logging.info(f"Creating dynamic subscriber for topic {topic_name}")

        self.topic_name = topic_name

        # Get all topic names and types
        topics_and_types = self.get_topic_names_and_types()

        # Find the topic type for our topic
        topic_type = next((t for n, t in topics_and_types if n == self.topic_name), None)
        if not topic_type:
            self.get_logger().error(f"Could not find topic '{self.topic_name}'.")
            return
        
        # The topic_type is a list of type names (usually only one)
        topic_type = topic_type[0]
        
        # Dynamically import the message type
        pkg_name, msg, msg_name = topic_type.split('/')
        pkg = importlib.import_module(pkg_name + '.msg')
        msg_type = getattr(pkg, msg_name)

        # Create a subscriber
        self.subscriber = self.create_subscription(msg_type, topic_name, self.message_callback, 10)
        # self.get_logger().info(f"Subscribed to {topic_name} of type {topic_type}")

    def end_subscription(self):
        if self.subscriber is not None:
            self.destroy_subscription(self.subscriber)
            self.subscriber = None
            self.buffer.clear()

    def message_callback(self, msg):
        # Add message to buffer
        self.buffer.append(msg)

    def buffer_as_string(self):
        return "\n".join([str(msg) for msg in self.buffer])

class Ros2Monitor(Node):
    """Ros2 infromation node: Provides information about ROS2 nodes, topics, services, and actions."""

    def __init__(self):
        rclpy.init()
        super().__init__('ros2_info_node')

        self.nodes = []
        self.topics = []
        self.ros_services = []
        self.lock = threading.Lock()

        self.echo_thread = None
        self.echo_ok = False
        self.echo_data_mutex = threading.Lock()
        self.current_topic_data = None
        self.echo_data = []

        self.nodes_info={}
        self.topics_info={}
        self.services_info={}
        self.actions_info={}
        self.info_thread = threading.Thread(target=self.ros2_info_thread)
        self.info_thread.start()

    # delete the node when the object is deleted
    def __del__(self):
        rclpy.shutdown()
        self.info_thread.join()
        self.destroy_node()

    def update_info(self):
        """ Gather the latest information about all nodes, topics, and services."""
        with self.lock:
            self.nodes = self.get_node_names_and_namespaces()
            self.topics = self.get_topic_names_and_types()
            self.ros_services = self.get_service_names_and_types()

    def get_nodes(self):
        """ Return a list of all existing ros2 nodes."""
        with self.lock:
            # return nodes as a list 
            # remove any double // from the name 
            return_list = []
            for name, namespace in self.nodes:
                if namespace == "/":
                    return_list.append("/"+name)
                else:
                    return_list.append(f"{namespace}/{name}")
            return return_list
        
    def get_topics(self):
        """ Return a list of all existing ros2 topics."""
        with self.lock:
            # return topics as a list
            return [f"{name}" for name, types in self.topics]
        
    def get_services(self):
        """ Return a list of all existing ros2 services."""
        with self.lock:
            return [f"{name}" for name, types in self.ros_services]

    def get_node_info(self, node_name):
        """ Run a subprocess to get standard output of ros2 node info command. """
        # If node exists, node info exists, node time exists and time < 5 seconds, return info
        if node_name in self.nodes_info and "info" in self.nodes_info[node_name] and "last_update" in self.nodes_info[node_name]:
            if time.time() - self.nodes_info[node_name]["last_update"] < 5:
                return self.nodes_info[node_name]["info"]
        # Else, get node info and update dictionary
        thread = threading.Thread(target=lambda: self.update_node_info(node_name))
        thread.start()
        return self.nodes_info[node_name]["info"] if node_name in self.nodes_info else "Node info outdated..."

    def get_topic_info(self, topic_name):
        """ Run a subprocess to get standard output of ros2 topic info command."""
        # If topic exists, topic info exists, topic time exists and time < 5 seconds, return info
        if topic_name in self.topics_info and "info" in self.topics_info[topic_name] and "last_update" in self.topics_info[topic_name]:
            if time.time() - self.topics_info[topic_name]["last_update"] < 5:
                return self.topics_info[topic_name]["info"]
        thread = threading.Thread(target=lambda: self.update_topic_info(topic_name))
        thread.start()
        return "Topic info outdated..."
    
    def get_service_info(self, service_name):
        """ Run a subprocess to get standard output of ros2 service info command."""
        # If service exists, service info exists, service time exists and time < 5 seconds, return info
        if service_name in self.services_info and "info" in self.services_info[service_name] and "last_update" in self.services_info[service_name]:
            if time.time() - self.services_info[service_name]["last_update"] < 5:
                return self.services_info[service_name]["info"]
        thread = threading.Thread(target=lambda: self.update_service_info(service_name))
        thread.start()
        return "Service info outdated..."

    def update_topic_info(self, topic_name):
        """ Update the topic info dictionary with the latest information."""
        info = self.get_ros2_topic_info(topic_name)
        self.topics_info[topic_name] = {"info": info, "last_update": time.time()}

    def update_node_info(self, node_name):
        """ Update the node info dictionary with the latest information."""
        info = self.get_ros2_node_info(node_name)
        self.nodes_info[node_name] = {"info": info, "last_update": time.time()}

    def update_service_info(self, service_name):
        """ Update the service info dictionary with the latest information."""
        info = self.get_ros2_service_info(service_name)
        self.services_info[service_name] = {"info": info, "last_update": time.time()}

    def get_ros2_service_info(self, service):
        """ Run a subprocess to get standard output of ros2 service info command."""
        cmd_str = f"/bin/bash -c 'source /opt/ros/humble/setup.bash; ros2 service type {service}'"
        result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        return result.stdout

    def get_ros2_topic_info(self, topic):
        """ Run a subprocess to get standard output of ros2 topic info command."""
        cmd_str = f"/bin/bash -c 'source /opt/ros/humble/setup.bash; ros2 topic info {topic}'"
        result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        return result.stdout
    
    def get_ros2_node_info(self, node):
        cmd_str = f"/bin/bash -c 'source /opt/ros/humble/setup.bash; ros2 node info {node}'"
        result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        return result.stdout

    def start_echo_topic(self, topic):
        # start a thread that we can join later  
        self.echo_thread = threading.Thread(target=lambda: self.echo_topic(topic))
        self.echo_thread.start()

    def stop_echo_topic(self):
        self.echo_ok = False
        if self.echo_thread is not None:
            self.echo_thread.join()
            self.echo_thread = None

    def toggle_echo_topic(self, topic):
        self.echo_ok = not self.echo_ok
        if self.echo_thread is not None:
            self.stop_echo_topic()
        else:
            self.start_echo_topic(topic)

    def get_topic_content(self, topic):
        # capture the output of the echo command and store it in a variable
        cmd_str = f"/bin/bash -c 'source /opt/ros/humble/setup.bash; ros2 topic echo {topic}'"
        result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        return result.stdout

    def echo_topic(self, topic):
        # capture the output of the echo command and store it in a variable
        cmd_str = f"/bin/bash -c 'source /opt/ros/humble/setup.bash; ros2 topic echo {topic}'"
        # # make sure its not blocking
        self.echo_ok = True
        # result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        # self.current_topic_data = result.stdout
        # self.echo_ok = False
        # process = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            process = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True, bufsize=1, close_fds=True, universal_newlines=True, encoding='utf-8')
        except Exception as e:
            pass
        
        with process.stdout:
            if not self.echo_ok: 
                # ask the process to stop
                process.terminate()
                process.wait()
                return
            data = ""
            for line in iter(process.stdout.readline, ''):
                data = line.strip()

                with self.echo_data_mutex:
                    self.echo_data.append(data)
                    if len(self.echo_data) > 1000:
                        self.echo_data.pop(0)
                if not self.echo_ok:
                    process.terminate()
                    process.wait()
                    return

        # Close the process
        process.wait()

    def get_current_topic_data(self):
        data = None
        with self.echo_data_mutex:
            data = list(self.echo_data)
        return "\n".join(data)

    # TODO: DEPRECATED
    def ros2_info_thread(self):
        while rclpy.ok():
            # logging.info("Updating ROS2 info")
            self.update_info()
            time.sleep(1)  # Adjust the sleep duration as needed


