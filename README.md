# rosgui
A curses command line gui for ros2

# Description
Description of the key classes and how to use the utility functions:

synchronized_data: This class represents a synchronized data object. It is used to store and access data in a thread-safe manner. You can create an instance of this class and pass an initial value to the constructor.

window_geometry: This class represents the geometry (position and size) of a window. You can create an instance of this class by providing the x and y coordinates, as well as the width and height of the window.

window_t: This is the base class for all windows in the GUI. It provides common functionality for creating, updating, and drawing windows. You can create a subclass of window_t to define your own custom windows. The window_t class has the following methods:

create_window(geometry): Creates a new curses window with the specified geometry.
update_geometry(geometry): Updates the geometry of the window.
set_selected(selected): Sets the selected state of the window.
draw(): Draws the window on the screen.
set_window_content(text): Sets the content of the window.
set_available_windows(available): Sets the list of available windows for this window.
update_content(): Updates the content of the window.
handle_input(key): Handles user input for the window.
run(): Runs the window and returns any content generated.
text_window_t: This is a subclass of window_t that represents a window for displaying text. You can create an instance of this class by providing a name and a side (left or right) for the window.

list_window_t: This is a subclass of window_t that represents a window for displaying a list of items. You can create an instance of this class by providing a name, a side (left or right), and a list of update callbacks. The update callbacks are functions that will be called when the content of the window needs to be updated.

session: This class represents a session of the GUI. It manages the main loop of the GUI and handles user input. You can create an instance of this class by providing the stdscr object from the curses library. The session class has the following methods:

add_window(window): Adds a window to the session.
remove_window(name): Removes a window from the session.
calculate_window_geometry(): Calculates the geometry of the windows based on the screen size.
window_redraw_required(): Checks if a window redraw is required.
refresh_windows(): Refreshes the windows.
toggle_selected_window(key): Toggles the selected window based on user input.
handle_input(key): Handles user input for the session.
run_window(key, window): Runs a window and handles its content.
draw(): Draws the windows on the screen.
run(): Runs the session and handles user input.
callback: This class represents a callback function that can be used to process data from one window in another window. You can create an instance of this class by providing the name of the window that the callback is associated with. The run(data) method of the callback class will be called with the data as an argument.

To add your own windows and run custom callbacks, you can follow these steps:

Create a subclass of window_t to define your custom window. Implement the update_content() and handle_input(key) methods to update the content and handle user input for your window.

Create an instance of your custom window class and add it to the session object using the add_window(window) method.

If your window needs to interact with another window, create an instance of the callback class and pass the name of the target window to the constructor. Add the callback instance to the list of update callbacks when creating the window.

Implement the run(data) method of the callback class to process the data from the source window and update the target window accordingly.

Run the session object by calling its run() method. This will start the main loop of the GUI and handle user input.

The code that would fit at $PLACEHOLDER$ is the implementation of your custom windows and callbacks. You can define your own classes and functions to create and manage windows, and add them to the session object.
    