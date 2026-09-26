"""Backend-only isolated rules proof. Never changes deck/collection/research state."""
from .evaluate import apply, evaluate
from .models import Action, ApplyResult, CardInstance, Evaluation, Location, Scenario
from .registry import ODDISH, RULESET, SWITCH, Registry

__all__ = ['Action', 'ApplyResult', 'CardInstance', 'Evaluation', 'Location', 'Scenario',
           'ODDISH', 'RULESET', 'SWITCH', 'Registry', 'apply', 'evaluate']
