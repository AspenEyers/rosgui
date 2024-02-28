#!/usr/bin/env python3
""" This is a simple GUI library for creating text and list windows in a curses environment."""

import curses
import time
import logging
from enum import Enum
from abc import abstractmethod
import threading

class SynchronizedData:
    """ A class for synchronizing access to shared data between threads."""
    def __init__(self, initial_data=None):
        self._data = initial_data
        self.lock = threading.Lock()

    @property
    def data(self):
        """ Thread-safe getter for the data property."""
        with self.lock:
            return self._data

    @data.setter
    def data(self, value):
        """ Thread-safe setter for the data property."""
        with self.lock:
            self._data = value

class WindowGeometry:
    """ A class for storing window geometry. """
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class Window:
    """ A class for creating a window in a curses environment. 
    This class is abstract and should be subclassed to create a specific window type.

    Windows are created with a name and a side. The side is used to determine the 
    window's position on the screen {LEFT,RIGHT}. Windows will be resized and 
    repositioned when the screen based on the number of windows and their side.

    typical usage:
        app = Session(stdscr)
        app.add_window( MyCustomWindowType("left1", Window.Side.left, [customCallback("right1")]) )

        
    """

    class Side(Enum):
        """ A class for defining window sides. """
        LEFT=1
        RIGHT=2

    def __init__(self, name, side):
        self.side = side
        self.window = None
        self.name = name
        self.requires_update = True
        self.requires_clear = True
        self.available_windows = []
        self.selected_line = None
        self.content_focus_line = None
        self.geometry = None
        self.content_update_thread = None
        self.content = SynchronizedData(None)
        self.displayable_content = SynchronizedData(None)
        self.content_updated = SynchronizedData(False)

    def x(self):
        """ Window x position."""
        return self.geometry.x
    def y(self):
        """ Window y position."""
        return self.geometry.y
    def width(self):
        """ Window geometry width. """
        return self.geometry.width
    def height(self):
        """ Window geometry height."""
        return self.geometry.height

    def create_window(self, geometry):
        """ Create a new window with the given geometry."""
        self.geometry = geometry
        self.window = curses.newwin(geometry.height, geometry.width, geometry.y, geometry.x)

    def update_geometry(self, geometry):
        """ Resizes and moves the window geometry. Sets gui update flags so the window will be 
        redrawn on the next draw cycle."""
        self.geometry = geometry
        if self.window is None: 
            self.create_window(geometry)
        else:
            try:
                self.window.resize(geometry.height, geometry.width)
                self.window.mvwin(geometry.y, geometry.x)
            except Exception as e:
                logging.error("Error resizing window %s: %s", self.name, e)
        self.requires_update = True
        self.requires_clear = True

    def set_selected(self, selected):
        """ Set the window's selected state. 
        This will change the window's background color to indicate selection."""
        if selected:
            self.window.bkgd(curses.color_pair(1))
        else:
            self.window.bkgd(curses.color_pair(2))
        self.requires_update = True

    def draw(self):
        """ Draw the window.
        If a window is flagged for update, it will be redrawn.
        Flag redeaw with requires_update = True.
        If the screed needs to be cleared, flag with requires_clear = True.
        """
        if self.window is None:
            return
        if not self.requires_update:
            return
        if self.requires_clear:
            self.window.clear()
            self.requires_clear = False

        if isinstance(self.displayable_content.data, str):
            self.displayable_content.data = [self.displayable_content.data]

        if self.displayable_content.data:
            for line in self.displayable_content.data:
                for i, line in enumerate(self.displayable_content.data):
                    if self.selected_line is not None and i == self.selected_line:
                        self.window.addstr(i + 1, 1, line, curses.A_REVERSE)
                    else:
                        self.window.addstr(i + 1, 1, line)

        self.window.border()
        self.window.refresh()
        self.requires_update = False

    def set_window_content(self, text):
        """ Set the window's content. """
        self.window.addstr(text)
        self.requires_update = True

    def set_available_windows(self, available):
        """ Set the available windows for this window. """
        self.available_windows = available

    @abstractmethod
    def update_content(self):
        """ Abstract method for updating the window's content.
        Override this method in a subclass to update the window's content."""

    @abstractmethod
    def handle_input(self, key):
        """ Abstract method for handling input.
        Override this method in a subclass to handle keyboard input."""

    @abstractmethod
    def run(self):
        """ Abstract method for running the window.
        Override this method in a subclass to run the window's main loop. """

class TextWindow(Window):
    """ A base class for creating a text window in a curses environment. """

    def __init__(self, name, side):
        super().__init__(name, side)

    def update_content(self):
        try:
            self.displayable_content.data = self.content.data
            self.draw()
            self.requires_update = True
            self.requires_clear = True
        except Exception as e:
            logging.error("Error updating content for window %s: %s", self.name, e)

    @abstractmethod
    def handle_content(self):
        """ Abstract method for handling the window's content.
        Override this method in a subclass to handle the window's content."""
        return "This is just a bunch of placeholder text."

    def handle_input(self, key):
        """ Handle keyboard input for the window. """

    def run(self):
        """ Run the window's main loop. """
        self.update_content()
        return None

class ListWindow(Window):
    """ A base class for creating a list window in a curses environment. 
    List windows are used to display a list of items and allow the user to 
    select an item from the list.
    It will handle the selection of items and update the content of other 
    windows based on the selected item.
    
    Selection: 
        - The user can select an item from the list by using the up and down arrow keys.
        - The selected item will be highlighted in the list.
        - When the user selects an item, the window will update the content of other windows 
          based on the selected item.
        
    Content:
        - The content of the list window is handled by the handle_content method.
        - The handle_content method should return a list of items to be displayed in the list.
        - The update_content method will update the list window's content and handle the 
          selection of items.
        
    Update Callbacks:
        - The list window can take a list of update_callbacks.
        - The update_callbacks are used to update the content of other windows based on the 
          selected item.
        - The update_callbacks should be a list of callback objects that implement a run method.
        - The run method should take the selected item as an argument and return the updated content 
          for the window.
        - The list window will call the run method on each callback object and update the content 
          of the window with the returned data."""
    def __init__(self, name, side, update_callbacks):
        super().__init__(name, side)
        self.update_callbacks = update_callbacks

    @abstractmethod
    def handle_content(self):
        """ Abstract method for handling the window's content. 
        Update this method to set the window's content.
        The content should be a list of items to be displayed in the list."""
        return ["test content 0"
              , "test content 1"
              , "test content 2"
              ]

    def update_content(self):
        """ Update the window's content and handle the selection of items."""
        self.content.data = self.handle_content()

        if self.content.data is None: 
            return
        # Convert to displayable lines given text size
        displayable_lines = self.height() - 2
        content_lines = len(self.content.data)

        if not self.selected_line:
            self.selected_line = 0

        if self.content_focus_line is None:
            self.content_focus_line = displayable_lines // 2

        upper_focus_line_limit = displayable_lines // 2
        lower_focus_line_limit = content_lines - (displayable_lines // 2)

        if self.selected_line < upper_focus_line_limit:
            pass

        if self.selected_line == -1:
            if content_lines > displayable_lines:
                self.selected_line = displayable_lines - 1
            else:
                self.selected_line = content_lines - 1
            self.content_focus_line = lower_focus_line_limit

        if self.selected_line == displayable_lines or self.selected_line == content_lines:
            self.selected_line = 0
            self.content_focus_line = upper_focus_line_limit

        while self.selected_line > displayable_lines // 2 and self.content_focus_line < lower_focus_line_limit:
            self.selected_line -= 1
            if self.content_focus_line < content_lines:
                self.content_focus_line += 1
            else:
                pass

        while self.selected_line < displayable_lines // 2 and self.content_focus_line > upper_focus_line_limit:
            self.selected_line += 1
            if self.content_focus_line > 0:
                self.content_focus_line -= 1
            else:
                pass

        if content_lines >= displayable_lines:
            lower = self.content_focus_line - (displayable_lines // 2)
            upper = self.content_focus_line + (displayable_lines // 2)
            self.displayable_content.data = self.content.data[lower:upper]
        elif content_lines < displayable_lines:
            self.displayable_content.data = self.content.data
        else:
            pass
        self.requires_update = True
        self.requires_clear = True

        for callback in self.update_callbacks:
            for w in self.available_windows:
                if w.name == callback.window_name:
                    w.content.data = callback.run(self.get_selected_content())
                    w.update_content()


    def get_selected_content(self):
        """ Get the selected (highlighted) content from the list.
        Used to update the content of other windows based on the selected item."""
        if self.displayable_content.data is None:
            return
        return self.displayable_content.data[self.selected_line]

    @abstractmethod
    def handle_input(self, key):
        if self.displayable_content.data is None:
            return
        if len(self.displayable_content.data) == 0:
            return
        if self.selected_line is None:
            self.selected_line = 0
        if key == curses.KEY_UP:
            self.selected_line = self.selected_line - 1
        elif key == curses.KEY_DOWN:
            self.selected_line = self.selected_line + 1

    def run(self):
        self.update_content()
        return None

class Session:
    """ The main session class for the GUI.
    The session class is used to create and manage the windows in the GUI.
    It will handle the main loop for the GUI and manage the input and updates for the windows.
    """
    def __init__(self, stdscr):
        self.init_curses(stdscr)
        self.height, self.width = stdscr.getmaxyx()
        self.windows = {}
        self.running = True
        self.selected_window = None
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)

    def init_curses(self, stdscr):
        """ Initialize the curses environment. """
        self.stdscr = stdscr
        self.stdscr.timeout(200)
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        logging.basicConfig(filename='gui.log', level=logging.DEBUG)        
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)


    def add_window(self, window):
        """ Add a window to the session and recalculate the window geometry."""
        self.windows[window.name] = window
        self.calculate_window_geometry()

    def remove_window(self, name):
        """ Remove a window from the session and recalculate the window geometry."""
        del self.windows[name]
        self.calculate_window_geometry()

    def calculate_window_geometry(self):
        """ Calculate the geometry of the windows based on the number of windows and their side.
        This will automatically set all left windows to 1/3 of the screen width 
        and all right windows to 2/3 of the screen width.
        If there are no left or right windows, the width will be set to the full screen width."""
        self.height, self.width = self.stdscr.getmaxyx()


        num_left_windows = len([win for win in self.windows.values() if win.side == Window.Side.LEFT])
        num_right_windows = len([win for win in self.windows.values() if win.side == Window.Side.RIGHT])

        right_start = self.width // 3
        if num_left_windows == 0 and num_right_windows == 0: 
            return
        elif num_left_windows == 0:
            right_width = self.width
            right_start = 0
        elif num_right_windows == 0:
            left_width = self.width
        else:
            left_width = self.width // 3
            right_width = (self.width // 3) * 2
        logging.debug("Calculating window geometry for %d left windows and %d right windows"
                      , num_left_windows, num_right_windows)
        right_height = self.height // num_right_windows if num_right_windows else 0
        left_height = self.height // num_left_windows if num_left_windows else 0
        left_start = 0

        # loop over all windows and set their geometry
        left_win = 0
        right_win = 0
        for i, win in enumerate(self.windows.values()):
            if win.side == Window.Side.LEFT:
                win.update_geometry(
                    WindowGeometry(left_start, left_win * left_height, left_width, left_height)
                    )
                left_win += 1
            if win.side == Window.Side.RIGHT:
                win.update_geometry(
                    WindowGeometry(right_start, right_win * right_height, right_width, right_height)
                )
                right_win += 1

    def window_redraw_required(self):
        """ Check if the session window needs to be redrawn."""
        redraw = False

        new_height, new_width = self.stdscr.getmaxyx()
        if new_height != self.height or new_width != self.width:
            self.height = new_height
            self.width = new_width
            redraw = True
        return redraw

    def refresh_windows(self):
        """ Refresh all windows."""
        self.calculate_window_geometry()

    def toggle_selected_window(self, key):
        """ Left and right arrow keys will toggle the selected window.
        It will loop through the available windows in the session in the order
        that they were added."""
        num_windows = len(self.windows)
        if num_windows == 0:
            return

        if not self.selected_window:
            self.selected_window = self.windows[list(self.windows.keys())[0]]

        # Find the next window after the selected window
        window_list = list(self.windows.values())
        selected_index = window_list.index(self.selected_window)
        next_index = selected_index
        if key == curses.KEY_LEFT:
            next_index = (selected_index - 1) % num_windows
        if key == curses.KEY_RIGHT:
            next_index = (selected_index + 1) % num_windows

        self.selected_window.set_selected(False)
        self.selected_window = window_list[next_index]
        self.selected_window.set_selected(True)

    def handle_input(self, key):
        """ Handle keyboard input for the GUI. """
        if key in range(0, 256):
            strkey = chr(key)
            logging.debug("Handling input: %d as %s", key, strkey)
        elif key == -1:
            pass
        else:  logging.debug("Handling input: %d", key)
        self.toggle_selected_window(key)

    def run_window(self, key, window):
        """ Run updates on the input window.
        - handle input
        - update the window's content
        - pass control to the window's run method
        By only running updates on the selected window, 
        we can avoid unnecessary updates on all windows."""
        # Let the window know what other windows are available
        available = [win for win in self.windows.values() if win != window]
        window.set_available_windows(available)
        window.handle_input(key)
        content = window.run()
        if content:
            window.set_window_content(content)

    def draw(self):
        """ Draw all windows."""
        if self.window_redraw_required():
            self.stdscr.clear()
            self.refresh_windows()

        for i, win in enumerate(self.windows.values()):
            win.requires_update = True
            win.draw()
        self.stdscr.refresh()

    def run(self):
        """ Main loop for the GUI. """
        while self.running:
            self.stdscr.refresh()
            try:
                self.draw()
                key = self.stdscr.getch()
                self.handle_input(key)
                self.run_window( key, self.selected_window )

            except KeyboardInterrupt:
                self.running = False
        curses.nocbreak()
        curses.echo()
        curses.endwin()
