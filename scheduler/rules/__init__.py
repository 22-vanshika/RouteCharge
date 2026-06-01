from typing import List

from scheduler.rules.base import SoftRule
from scheduler.rules.individual import IndividualWaitRule
from scheduler.rules.operator import OperatorFairnessRule
from scheduler.rules.overall import OverallNetworkRule

DEFAULT_RULES: List[SoftRule] = [
    IndividualWaitRule(),
    OperatorFairnessRule(),
    OverallNetworkRule(),
]
