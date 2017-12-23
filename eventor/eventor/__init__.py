from eventor.VERSION import __version__

from eventor.engine import Eventor, get_unique_run_id
from eventor.eventor_types import AssocType, TaskStatus, DbMode, StepStatus, StepReplay, RunMode, Invoke
from eventor.event import or_
from eventor.utils import calling_module, store_from_module

STP_RERUN = StepReplay.rerun  # reruns step regardless if previously succeeded
STP_SKIP = StepReplay.skip  # skip step if previously succeeded

STP_READY = StepStatus.ready  # step is ready
STP_ACTIVE = StepStatus.active  # step is running
STP_SUCCESS = StepStatus.success  # step succeeded
STP_FAILURE = StepStatus.failure  # step failed
STP_COMPLETE = StepStatus.complete  # step complete with success or failure

EVR_CONTINUE = RunMode.continue_  # run previously ran flow, skip steps succeeded.
EVR_RESTART = RunMode.restart  # run flow from start
EVR_RECOVER = RunMode.recover  # 
EVR_REPLAY = RunMode.replay
