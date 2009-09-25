# Copyright 2009 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

"""
This module defines the HistoryBrowser class. See its documentation
for more info.

todo: change "our leaf" to "our node", since it might not be a leaf.

todo: this needs testing
"""
import threading

import crunchers

import garlicsim.history_browser_abc

import garlicsim.misc.binary_search as binary_search
import garlicsim.misc.queue_tools as queue_tools

__all__ = ["HistoryBrowser"]

get_state_clock = lambda state: state.clock

def with_self(method):
    """
    A decorator used in HistoryBrowser's methods to use the history browser
    as a context manager when calling the method.
    """
    def fixed(self, *args, **kwargs):
        with self:
            return method(self, *args, **kwargs)
    return fixed

class HistoryBrowser(garlicsim.history_browser_abc.HistoryBrowserABC):
    """
    A HistoryBrowser is a device for requesting information about the history
    of the simulation.
    It is intended to be used by CruncherThread in simulations that are
    history-dependent.
    
    With a HistoryBrowser one can request states from the simulation's
    timeline. States can be requested by clock time or position in the timeline
    or by other measures; See documentation for this class's methods.
    
    Since we do not know whether the states we request have been implemented in
    the tree already, or they are still in the work_queue, it's the job of the
    HistoryBrowser to find that out. This is done transperantly for the user.
    
    When using a HistoryBroswer, the tree_lock of the project is acquired
    for reading. That acquiring action can also be invoked by using
    HistoryBrowser as a context manager.
    
    
    todo in the future: because historybrowser
    retains a reference to a node, when the user deletes a node
    we should mark it so the historybrowser will know it's dead.
    
    todo: make it easy to use hisotrybrowser's method from a separate thread,
    so when waiting for a lock the cruncher could still be productive.
        
    todo: maybe I've exaggerated in using @with_self in so many places?
    
    """
    def __init__(self, cruncher):
        self.cruncher = cruncher
        self.project = cruncher.project
        self.tree = self.project.tree
        self.tree_lock = self.project.tree_lock
    
    def __enter__(self, *args, **kwargs):
        self.tree_lock.acquireRead()
    
    def __exit__(self, *args, **kwargs):
        self.tree_lock.release()
     
    @with_self
    def get_last_state(self):
        """
        Gets the last state in the timeline. Identical to __getitem__(-1).
        """
        return self[-1]
    
    @with_self
    def __getitem__(self, index):
        """
        Returns a state by its position in the timeline.
        """
        assert isinstance(index, int)
        if index < 0:
            return self.__get_item_negative(index)
        else: # index >= 0
            return self.__get_item_positive(index)
    
    @with_self
    def __get_item_negative(self, index):
        """
        Used when __getitem__ is called with a negative index.
        """
        try:
            return self.__get_item_from_queue(index)
        except IndexError:
            # The requested state is in the tree
            queue_size = self.cruncher.work_queue.qsize()
            new_index = index + queue_size
            our_leaf = self.__get_our_leaf()
            path = our_leaf.make_containing_path()
            result_node = path.__getitem__(new_index, end_node=our_leaf)
            return result_node.state
            
    
    @with_self
    def __get_item_positive(self, index):
        """
        Used when __getitem__ is called with a positive index.
        """
        our_leaf = self.__get_our_leaf()
        path = our_leaf.make_containing_path()
        try:
            result_node = path.__getitem__(index, end_node=our_leaf)
            return result_node.state
        
        except IndexError:
            path_length = path.__len__(end_node=our_leaf)
            # todo: Probably inefficient: We're plowing through the path again.
            new_index = index - path_length
            try:
                return self.__get_item_from_queue(new_index)
            except IndexError:
                queue_length = self.cruncher.work_queue.qsize()
                timeline_length = queue_length + path_length
                message = "You asked for node number " + str(index) + \
                          " while the timeline has only " + timeline_length + \
                          " states, comprised by " + path_length + \
                          " states in the tree and " + queue_length + \
                          " states in the queue."
                raise IndexError(message)
        
        
            
    
    @with_self
    def __get_item_from_queue(self, index):
        """
        Obtains an item by index number from the work_queue of our cruncher.
        """
        item = queue_tools.queue_get_item(self.cruncher.work_queue, index)
        return item
        
    
    @with_self
    def get_state_by_clock(self, clock, rounding="Closest"):
        """
        Requests a state by specifying desired clock time.
        
        See documentation of garlicsim.misc.binary_search.binary_search for
        details about rounding options.
        """
        assert rounding in ["High", "Low", "Exact", "Both", "Closest"]
        return self.get_state_by_monotonic_function\
               (function=get_state_clock, value=clock, rounding=rounding)
    
    @with_self
    def get_state_by_monotonic_function(self, function, value,
                                        rounding="Closest"):
        """
        Requests a state by specifying a measure function and a desired value.
        The function must be a monotonic rising function on the timeline.
        
        See documentation of garlicsim.misc.binary_search.binary_search for
        details about rounding options.
        """
        assert rounding in ["High", "Low", "Exact", "Both", "Closest"]
        
        tree_result = self.__get_state_by_monotonic_function_from_tree \
                      (function, value, rounding="Both")
        
        if tree_result[1] is not None:
            # Then there is no need to check the queue even.
            return binary_search.make_both_data_into_preferred_rounding\
                   (tree_result, function, value, rounding)
        
        else:
            queue_result = self.__get_state_by_monotonic_function_from_queue \
                           (function, value, rounding="Both")
            none_count = queue_result.count(None)
            if none_count == 0:
                # The result is entirely in the queue
                return binary_search.make_both_data_into_preferred_rounding\
                       (queue_result, function, value, rounding)
            elif none_count == 1:
                """
                The result is on or beyond the edge of the queue.
                """
                if queue_result[1] is None:
                    # The result is either the most recent state in the queue
                    # or "after" it
                    return binary_search.make_both_data_into_preferred_rounding\
                           (queue_result, function, value, rounding)
                else: # queue_result[0] == None
                    """
                    Getting tricky: The result is somewhere in the middle
                    between the queue and the tree.
                    """
                    combined_result = [tree_result[0], queue_result[1]]
                    return binary_search.make_both_data_into_preferred_rounding\
                           (combined_result, function, value, rounding)
    
            elif none_count == 2:
                """
                The queue is just totally empty.
                """
                return binary_search.make_both_data_into_preferred_rounding \
                       (tree_result, function, value, rounding)
            
    @with_self   
    def __get_state_by_monotonic_function_from_tree(self, function, value,
                                                    rounding="Closest"):
        """
        Requests a state FROM THE TREE ONLY by specifying a measure function
        and a desired value.
        The function must by a monotonic rising function on the timeline.
        
        See documentation of garlicsim.misc.binary_search.binary_search for
        details about rounding options.
        """
        assert rounding in ["High", "Low", "Exact", "Both", "Closest"]
        our_leaf = self.__get_our_leaf()
        path = our_leaf.make_containing_path()
        new_function = lambda node: function(node.state)
        result_in_nodes = path.get_node_by_monotonic_function \
                        (new_function, value, rounding)
        result = [(node.state if node is not None else None) \
                  for node in result_in_nodes]
        return result
    
    @with_self
    def __get_state_by_monotonic_function_from_queue(self, function, value,
                                                     rounding="Closest"):
        """
        Requests a state FROM THE QUEUE ONLY by specifying a measure function
        and a desired value.
        The function must by a monotonic rising function on the timeline.
        
        See documentation of garlicsim.misc.binary_search.binary_search for
        details about rounding options.
        """
        assert rounding in ["High", "Low", "Exact", "Both", "Closest"]
        queue = self.cruncher.work_queue
        queue_size = queue.qsize()
        with queue.mutex:
            queue_as_list = list(queue.queue)
            # todo: Probably inefficient, should access them one by one
        
        return binary_search.binary_search\
               (queue_as_list, function, value, rounding)
    
    @with_self
    def __len__(self):
        """
        Returns the length of the timeline in nodes, which means the sum of:
        1. The length of the work_queue of our cruncher.
        2. The length of the path in the tree which leads to our node, up to
           our node.
        """
        queue_length = self.cruncher.work_queue.qsize()
        
        our_leaf = self.__get_our_leaf()
        our_path = our_leaf.make_containing_path()
        path_length = our_path.__len__(end_node = our_leaf)
        
        return queue_length + path_length
    
    @with_self
    def __get_our_leaf(self):
        """
        Returns the leaf that the current cruncher is assigned to work on.
        """
        
        current_thread = threading.currentThread()  
        
        leaves_to_crunchers = self.project.crunching_manager.crunchers.items()
        
        leaves_that_are_us = \
            [leaf for (leaf, cruncher) in leaves_to_crunchers\
             if cruncher == current_thread]
        
        num = len(leaves_that_are_us)
        assert num <= 1
        if num == 1:
            our_leaf = leaves_that_are_us[0]
        else: # num == 0
            raise crunchers.ObsoleteCruncherError
        return our_leaf
            
    
