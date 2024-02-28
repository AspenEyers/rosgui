#!/usr/bin/env python3
import curses
import subprocess
import logging
import threading
import time 
import rclpy
from rclpy.node import Node

class Ros2Monitor(Node):
    """Ros2 infromation node: Provides information about ROS2 nodes, topics, services, and actions."""

    def __init__(self):
        rclpy.init()
        super().__init__('ros2_info_node')
        self.info_thread = threading.Thread(target=ros2_info_thread, args=(self,))
        self.info_thread.start()

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
        self.update_info()

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
            logging.info("Starting echo thread")
            self.start_echo_topic(topic)

    def echo_topic(self, topic):
        # capture the output of the echo command and store it in a variable
        cmd_str = f"/bin/bash -c 'source /opt/ros/humble/setup.bash; ros2 topic echo {topic}'"
        # # make sure its not blocking
        self.echo_ok = True
        # result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        # self.current_topic_data = result.stdout
        # self.echo_ok = False
        logging.info("Starting echo process 11")
        # process = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            process = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True, bufsize=1, close_fds=True, universal_newlines=True, encoding='utf-8')
        except Exception as e:
            logging.error(f"Error starting echo process: {e}")
        logging.info("Started echo process 11 ====")
        
        with process.stdout:
            if not self.echo_ok: 
                logging.info("Stopping echo process")
                # ask the process to stop
                process.terminate()
                logging.info("waiting")
                process.wait()
                logging.info("done")
                return
            data = ""
            for line in iter(process.stdout.readline, ''):
                logging.info(f"Got line: {line.strip()}")
                data = line.strip()
                logging.info(f"Data: {data}")
                
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

def draw_box(stdscr, window, y, x, height, width, text, is_focused, selected_line=None, scroll_pos=0, debug_id=-1):
    color = curses.color_pair(1 if is_focused else 2)
    window.clear()
    window.border()
    window.bkgd(' ', color)

    lines = ""
    if text is not None:    
        lines = text.split('\n')
    

    # make sure that we don't try to draw more lines than we have space for
    # and that we only print the most recent lines
    max_lines = height - 2
    start_line = 0
    total_lines = len(lines)
    scroll_pos = 0
    # scroll_pos = min(scroll_pos, total_lines - max_lines) if total_lines > max_lines else 0
    # if scroll_pos < 0:
        # scroll_pos = max(0, total_lines)

    # if len(lines) > max_lines:
    #     start_line = len(lines) - max_lines + scroll_pos
    last_line = start_line + max_lines 
    
    if debug_id == 2:
        number_of_topics = len(lines)
        number_of_lines = height - 2
        logging.info(f"Number of topics: {number_of_topics}, number of lines: {number_of_lines}, start_line: {start_line}, last_line: {last_line}, scroll_pos: {scroll_pos}")

    for i in range(scroll_pos, last_line):
        if i >= len(lines):
            break
        line = lines[i]
        line_number = i - start_line

        # make sure the line is not too long, if it is, cut it off
        if len(line) > width - 2:
            line = line[:width - 5] + "..."        

        try:
            if selected_line is not None and i == selected_line:
                window.addstr(i - scroll_pos + 1, 1, line, curses.A_REVERSE)
            else:
                window.addstr(i - scroll_pos + 1, 1, line)
        except curses.error:
            pass
    
    # window.noutrefresh()
    return scroll_pos

def ros2_info_thread(ros2_info_node):
    while rclpy.ok():
        logging.info("Updating ROS2 info")
        ros2_info_node.update_info()
        time.sleep(1)  # Adjust the sleep duration as needed


# def main(stdscr):
    
#     stdscr.timeout(200)

#     # ROS2 node setup
#     ros2_info_node = ROS2Info()

#     # Set up logging
#     logging.basicConfig(filename='agent_controller.log', level=logging.DEBUG)

#     # Initialize colors and cursors
#     curses.start_color()
#     curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
#     curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
#     curses.curs_set(0)  # Turn off cursor visibility

#     # Initialize window dimensions and create windows
#     height, width = stdscr.getmaxyx()
#     box1 = curses.newwin(height // 3, width // 3, 0, 0)
#     box2 = curses.newwin(height // 3, width // 3, height // 3, 0)
#     box3 = curses.newwin(height // 3, width // 3, 2*height // 3,0 )
#     box4 = curses.newwin(height, 2*width // 3, 0, width // 3)

#     publisher_scroll_pos = 0

#     draw_box(stdscr, box1, 0, 0, height // 2, width // 3, "", True)
#     publisher_scroll_pos = draw_box(stdscr, box2, height // 2, 0, height // 2, width // 3, "", False, publisher_scroll_pos)
#     draw_box(stdscr, box3, height // 2, 0, height // 2, width // 3, "", False)
#     draw_box(stdscr, box4, 0, 2*width // 3, height, width // 3, "", False)

#     stdscr.refresh()        
#     box1.refresh()
#     box2.refresh()
#     box3.refresh()
#     box4.refresh()

#     # Initialize selection and focus variables
#     selected_node_line = 0
#     selected_publisher_line = 0
#     selected_service_line = 0
#     focus = 1

#     # Flags for updating content
#     update_box1 = True
#     update_box2 = True
#     update_box3 = True
#     update_box4 = True

#     echo_topic_enabled = False

#     while rclpy.ok():
#         update_box1 = True
#         update_box2 = True
#         update_box3 = True
#         update_box4 = True

#         # Fetch data from ROS2Info node
#         ros2_nodes = ros2_info_node.get_nodes()
#         ros2_publishers = ros2_info_node.get_topics()
#         ros2_services = ros2_info_node.get_services()

#         # Check if window dimensions have changed
#         new_height, new_width = stdscr.getmaxyx()
#         if new_height != height or new_width != width:
#             height, width = new_height, new_width
#             box1.resize(height // 3, width // 3)
#             box2.resize(height // 3, width // 3)
#             box3.resize(height // 3, width // 3)
#             box4.resize(height, 2*width // 3)
#             # transate the boxes if required 
#             box2.mvwin(height // 3, 0)
#             box3.mvwin(2*height // 3, 0)
#             box4.mvwin(0, width // 3)
#             update_box1 = update_box2 = update_box3 = update_box4 = True

#             # redraw to ensure the boxes are updated
#             stdscr.clear()
#             stdscr.refresh()
#             box1.refresh()
#             box2.refresh()
#             box3.refresh()
#             box4.refresh()

#         # Update content flags
#         if update_box1:
#             box1_content = '\n'.join(ros2_nodes) if ros2_nodes else "No ROS2 nodes available"
#             draw_box(stdscr, box1, 0, 0, height // 2, width // 3, box1_content, focus == 1, selected_node_line)
#             update_box1 = False

#         if update_box2:
#             box2_content = '\n'.join(ros2_publishers) if ros2_publishers else "No ROS2 topics available"
#             publisher_scroll_pos = draw_box(stdscr, box2, height // 2, 0, height // 2, width // 3, box2_content, focus == 2, selected_publisher_line, publisher_scroll_pos, debug_id=2)
#             update_box2 = False

#         if update_box3:
#             box3_content = '\n'.join(ros2_services) if ros2_services else "No ROS2 services available"
#             draw_box(stdscr, box3, height // 2, 0, height // 2, width // 3, box3_content, focus == 3, selected_service_line)
#             update_box3 = False

#         if update_box4:
#             if focus==1 and ros2_nodes: box4_content = ros2_info_node.get_node_info(ros2_nodes[selected_node_line])
#             if focus==2 and ros2_publishers: 
#                 if echo_topic_enabled:
#                     box4_content = ros2_info_node.get_current_topic_data()
#                 else:
#                     box4_content = ros2_info_node.get_topic_info(ros2_publishers[selected_publisher_line])
#             if focus==3 and ros2_services: box4_content = ros2_info_node.get_service_info(ros2_services[selected_service_line])
#             draw_box(stdscr, box4, 0, width // 3, height, width // 3, box4_content, focus == 4)
#             update_box4 = False

#         stdscr.refresh()        
#         box1.refresh()
#         box2.refresh()
#         box3.refresh()
#         box4.refresh()

#         # Handle user input
#         key = stdscr.getch()

#         # handle scrolling
#         publisher_scroll_pos = selected_publisher_line

#         if focus == 2 and key == ord('e'):
#             logging.info("Key E pressed")
#             print("Key E pressed")
#             echo_topic_enabled = not echo_topic_enabled
#             ros2_info_node.toggle_echo_topic(ros2_publishers[selected_publisher_line])

#         if key in [curses.KEY_LEFT, curses.KEY_RIGHT]:
#             focus = (focus - 2) % 4 + 1 if key == curses.KEY_LEFT else focus % 4 + 1
#             update_box1 = update_box2 = update_box3 = update_box4 = True
#         elif focus == 1 and key in [curses.KEY_UP, curses.KEY_DOWN]:
#             selected_node_line = (selected_node_line - 1) % len(ros2_nodes) if key == curses.KEY_UP else (selected_node_line + 1) % len(ros2_nodes)
#             update_box1 = True
#             update_box4 = True
#         elif focus == 2 and key in [curses.KEY_UP, curses.KEY_DOWN]:
#             selected_publisher_line = (selected_publisher_line - 1) % len(ros2_publishers) if key == curses.KEY_UP else (selected_publisher_line + 1) % len(ros2_publishers)
#             update_box2 = True
#             update_box4 = True
#         elif focus == 3 and key in [curses.KEY_UP, curses.KEY_DOWN]:
#             selected_service_line = (selected_service_line - 1) % len(ros2_services) if key == curses.KEY_UP else (selected_service_line + 1) % len(ros2_services)
#             update_box3 = True
#             update_box4 = True
#         elif focus == 4 and key == ord('r'):
#             update_box4 = True
#         elif key == ord('q'):
#             break


# # Run the main function with curses wrapper
# if __name__ == "__main__":
#     try:
#         curses.wrapper(main)
#     except Exception as e:
#         print("An error occurred:", e)
