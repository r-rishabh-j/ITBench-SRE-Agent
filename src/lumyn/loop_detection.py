import json
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

class LoopDetectedError(Exception):
    """Exception raised when a loop is detected."""
    pass

class LoopDetector:
    def __init__(self, max_stagnation: int = 3, max_cycle_repeats: int = 3):
        """
        Initialize the LoopDetector.

        Args:
            max_stagnation: Number of times the same action with similar output is allowed.
            max_cycle_repeats: Number of times a sequence of actions is allowed to repeat.
        """
        self.history: List[Tuple[str, str, str]] = []  # (tool_name, tool_args, tool_output)
        self.max_stagnation = max_stagnation
        self.max_cycle_repeats = max_cycle_repeats

    def _is_similar(self, a: str, b: str, threshold: float = 0.9) -> bool:
        """Check if two strings are similar."""
        return SequenceMatcher(None, str(a), str(b)).ratio() > threshold

    def _normalize_args(self, args: Any) -> str:
        """Normalize arguments to a consistent string representation."""
        if isinstance(args, dict):
            return json.dumps(args, sort_keys=True)
        return str(args)

    def callback(self, step_output: Any):
        """
        Callback to be executed after each agent step.
         Expects step_output to have 'tool_name', 'tool_input', and 'tool_output'.
        """
        # Defensive coding to handle different versions/structures of step_output
        # Adjust based on actual CrewAI AgentStep object structure
        try:
            # Assuming step_output is an AgentStep or similar object
            # Inspecting common attributes pattern.
            # If step_output is a list, take the last element (CrewAI sometimes returns list of steps)
            if isinstance(step_output, list):
                step = step_output[-1]
            else:
                step = step_output
            
            # Accessing tuples/objects. 
            # In some CrewAI versions, step is (agent, task, details) or object with .tool_name
            # Let's try to extract robustly.
            # Note: The exact attribute names might need verification if this fails.
            # Based on recent CrewAI: step usually has 'tool', 'tool_input', 'raw_output' (or 'output')
            
            # If step is a tuple (common in some internal callbacks)
            if isinstance(step, tuple):
                 # This path is risky without knowing exact tuple structure, 
                 # but often it's (result, tool_name, ...). 
                 # Let's skip if we can't identify.
                 pass 
            
            tool_name = getattr(step, 'tool_name', None) or getattr(step, 'name', None)
            tool_input = getattr(step, 'tool_input', None) or getattr(step, 'inputs', None)
            tool_output = getattr(step, 'raw_output', None) or getattr(step, 'output', None)
            
            if tool_name is None:
                # Fallback: maybe it's a dict?
                if isinstance(step, dict):
                    tool_name = step.get('tool_name') or step.get('name')
                    tool_input = step.get('tool_input') or step.get('inputs')
                    tool_output = step.get('raw_output') or step.get('output')
            
            if tool_name:
                self._record_and_check(tool_name, tool_input, tool_output)
                
        except AttributeError:
             # If we can't parse it, safe to ignore to not break the agent, 
             # but we should log it (print for now).
             print(f"LoopDetector Warning: Could not parse step_output: {type(step_output)}")

    def _record_and_check(self, tool_name: str, tool_input: Any, tool_output: Any):
        normalized_input = self._normalize_args(tool_input)
        # Normalize output: specific to ITBench, some outputs might be huge JSONs.
        # We process string representation.
        output_str = str(tool_output)
        
        self.history.append((tool_name, normalized_input, output_str))
        
        # 1. Check Stagnation
        self._check_stagnation()
        
        # 2. Check Cycles (Optional/Stretch, but useful)
        # self._check_cycles() # Uncomment if we implement full cycle detection

    def _check_stagnation(self):
        """Check if the last N actions are identical and outputs are similar."""
        if len(self.history) < self.max_stagnation + 1:
            return

        # Look at the last N+1 items. 
        # We need N repeats, so N+1 items total (Original + N repeats)
        # Wait, if max_stagnation is 3, it means:
        # A -> A -> A -> A (4 occurrences, 3 repetitions)
        
        recent_history = self.history[-(self.max_stagnation + 1):]
        
        first_tool, first_input, first_output = recent_history[0]
        
        is_stagnant = True
        for tool, input_args, output in recent_history[1:]:
            if tool != first_tool or input_args != first_input:
                is_stagnant = False
                break
            
            if not self._is_similar(output, first_output):
                 # Output changed significantly -> Progress!
                 is_stagnant = False
                 break
        
        if is_stagnant:
            raise LoopDetectedError(
                f"Loop detected: Agent executed '{first_tool}' with same input {self.max_stagnation} times without significant output change."
            )
