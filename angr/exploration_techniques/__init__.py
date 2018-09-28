from .. import engines
from ..errors import SimError


# 8<----------------- Compatibility layer -----------------
class ExplorationTechniqueMeta(type):
    def __new__(cls, name, bases, attrs):
        import inspect
        if name != 'ExplorationTechniqueCompat':
            if 'step' in attrs and not inspect.getargspec(attrs['step']).defaults:
                attrs['step'] = cls._step_factory(attrs['step'])
            if 'filter' in attrs and inspect.getargspec(attrs['filter']).args[1] != 'simgr':
                attrs['filter'] = cls._filter_factory(attrs['filter'])
            if 'step_state' in attrs and inspect.getargspec(attrs['step_state']).args[1] != 'simgr':
                attrs['step_state'] = cls._step_state_factory(attrs['step_state'])
        return type.__new__(cls, name, bases, attrs)

    @staticmethod
    def _step_factory(step):
        def step_wrapped(self, simgr, stash='active', **kwargs):
            return step(self, simgr, stash, **kwargs)
        return step_wrapped

    @staticmethod
    def _filter_factory(func):  # pylint:disable=redefined-builtin
        def filter_wrapped(self, simgr, state, filter_func=None):
            result = func(self, state)  # pylint:disable=no-value-for-parameter
            if result is None:
                result = simgr.filter(state, filter_func=filter_func)
            return result
        return filter_wrapped

    @staticmethod
    def _step_state_factory(step_state):
        def step_state_wrapped(self, simgr, state, successor_func=None, **kwargs):
            result = step_state(self, state, **kwargs)
            if result is None:
                result = simgr.step_state(state, successor_func=successor_func, **kwargs)
            return result
        return step_state_wrapped
# ------------------- Compatibility layer --------------->8


class ExplorationTechnique:
    """
    An otiegnqwvk is a set of hooks for a simulation manager that assists in the implementation of new techniques in
    symbolic exploration.

    TODO: choose actual name for the functionality (techniques? strategies?)

    Any number of these methods may be overridden by a subclass.
    To use an exploration technique, call ``simgr.use_technique`` with an *instance* of the technique.
    """
    # 8<----------------- Compatibility layer -----------------
    __metaclass__ = ExplorationTechniqueMeta
    # ------------------- Compatibility layer --------------->8

    def __init__(self):
        # this attribute will be set from above by the manager
        if not hasattr(self, 'project'):
            self.project = None

    def setup(self, simgr):
        """
        Perform any initialization on this manager you might need to do.
        """
        pass

    def step(self, simgr, stash='active', **kwargs):  # pylint:disable=no-self-use
        """
        Step this stash of this manager forward. Should call ``simgr.step(stash, **kwargs)`` in order to do the actual
        processing.

        Return the stepped manager.
        """
        return simgr.step(stash=stash, **kwargs)

    def filter(self, simgr, state, filter_func=None):  # pylint:disable=no-self-use
        """
        Perform filtering on a state.

        If the state should not be filtered, return None.
        If the state should be filtered, return the name of the stash to move the state to.
        If you want to modify the state before filtering it, return a tuple of the stash to move the state to and the
        modified state.
        """
        return simgr.filter(state, filter_func=filter_func)

    def selector(self, simgr, state, selector_func=None):  # pylint:disable=no-self-use
        """
        Return True, the state should be selected for stepping during the step() process.
        """
        return simgr.selector(state, selector_func=selector_func)

    def step_state(self, simgr, state, successor_func=None, **kwargs):  # pylint:disable=no-self-use
        """
        Perform the process of stepping a state forward.

        If the stepping fails, return None to fall back to a default stepping procedure.
        Otherwise, return a dict of stashes to merge into the simulation manager. All the states
        will be added to the PathGroup's stashes based on the mapping in the returned dict.
        """
        return simgr.step_state(state, successor_func=successor_func, **kwargs)

    def successors(self, simgr, state, successor_func=None, **run_args):  # pylint:disable=no-self-use
        """
        Return successors of the given state.
        """
        return simgr.successors(state, successor_func=successor_func, **run_args)

    def complete(self, simgr):  # pylint:disable=no-self-use,unused-argument
        """
        Return whether or not this manager has reached a "completed" state, i.e. ``SimulationManager.run()`` should halt.
        """
        return False

    def _condition_to_lambda(self, condition, default=False):
        """
        Translates an integer, set, list or function into a lambda that checks if state's current basic block matches
        some condition.

        :param condition:   An integer, set, list or lambda to convert to a lambda.
        :param default:     The default return value of the lambda (in case condition is None). Default: false.

        :returns:           A tuple of two items: a lambda that takes a state and returns the set of addresses that it
                            matched from the condition, and a set that contains the normalized set of addresses to stop
                            at, or None if no addresses were provided statically.
        """
        if condition is None:
            condition_function = lambda state: default
            static_addrs = set()

        elif isinstance(condition, int):
            return self._condition_to_lambda((condition,))

        elif isinstance(condition, (tuple, set, list)):
            static_addrs = set(condition)
            def condition_function(state):
                if state.addr in static_addrs:
                    # returning {state.addr} instead of True to properly handle find/avoid conflicts
                    return {state.addr}

                if not isinstance(self.project.engines.default_engine, engines.SimEngineVEX):
                    return False

                try:
                    # If the address is not in the set (which could mean it is
                    # not at the top of a block), check directly in the blocks
                    # (Blocks are repeatedly created for every check, but with
                    # the IRSB cache in angr lifter it should be OK.)
                    return static_addrs.intersection(set(state.block().instruction_addrs))
                except (AngrError, SimError):
                    return False

        elif hasattr(condition, '__call__'):
            condition_function = condition
            static_addrs = None
        else:
            raise AngrExplorationTechniqueError("ExplorationTechnique is unable to convert given type (%s) to a callable condition function." % condition.__class__)

        return condition_function, static_addrs

#registered_actions = {}
#registered_surveyors = {}
#
#def register_action(name, strat):
#    registered_actions[name] = strat
#
#def register_surveyor(name, strat):
#    registered_surveyors[name] = strat

from .cacher import Cacher
from .driller_core import DrillerCore
from .loop_seer import LoopSeer
from .crash_monitor import CrashMonitor
from .tracer import Tracer
from .explorer import Explorer
from .threading import Threading
from .dfs import DFS
from .lengthlimiter import LengthLimiter
from .veritesting import Veritesting
from .oppologist import Oppologist
from .director import Director, ExecuteAddressGoal, CallFunctionGoal
from .spiller import Spiller
from .manual_mergepoint import ManualMergepoint
from .tech_builder import TechniqueBuilder
from .stochastic import StochasticSearch
from .unique import UniqueSearch
from .symbion import Symbion
from ..errors import AngrError, AngrExplorationTechniqueError
