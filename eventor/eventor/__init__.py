__version__ = '5.1.2'
__db_version__ = '1.0.0'

from eventor.engine import Eventor, get_unique_run_id
from eventor.eventor_types import AssocType, TaskStatus, DbMode, StepStatus, StepReplay
from eventor.eventor_types import RunMode, Invoke
from eventor.event import or_
from eventor.utils import calling_module, store_from_module

STEP_RERUN = StepReplay.rerun  # reruns step regardless if previously succeeded
STEP_SKIP = StepReplay.skip  # skip step if previously succeeded

STEP_READY = StepStatus.ready  # step is ready
STEP_ACTIVE = StepStatus.active  # step is running
STEP_SUCCESS = StepStatus.success  # step succeeded
STEP_FAILURE = StepStatus.failure  # step failed
STEP_COMPLETE = StepStatus.complete  # step complete with success or failure

RUN_RESTART = RunMode.restart  # run flow from start
RUN_RECOVER = RunMode.recover  # reruns failed steps

# Note: internal use only
RUN_CONTINUE = RunMode.continue_  # continue from where it left in previous loop
