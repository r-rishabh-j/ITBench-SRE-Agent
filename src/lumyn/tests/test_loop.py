import unittest
from lumyn.loop_detection import LoopDetector, LoopDetectedError

class MockStep:
    def __init__(self, tool_name, tool_input, raw_output):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.raw_output = raw_output

class TestLoopDetector(unittest.TestCase):
    def test_stagnation(self):
        detector = LoopDetector(max_stagnation=2)
        
        # Action 1
        detector.callback(MockStep("kubectl", "get pods", "pod 1 running"))
        # Action 2 (Same)
        detector.callback(MockStep("kubectl", "get pods", "pod 1 running"))
        # Action 3 (Same - should trigger max_stagnation=2 means 2 repeats allowed? No, 2 times SAME action allowed.)
        # Logic says: if len(history) < max_stagnation + 1 return.
        # max_stagnation=2.  Need 3 items.
        
        # Action 3
        try:
             detector.callback(MockStep("kubectl", "get pods", "pod 1 running"))
        except LoopDetectedError:
             self.fail("Should not have raised detected error yet if max_stagnation=2 means 2 REPEATS (total 3 invos) allowed?")
        
        # Wait, my logic was:
        # recent_history = self.history[-(self.max_stagnation + 1):]
        # items check.
        # If max_stagnation=2, we check last 3 items.
        # 1. ("kubectl", "get pods", "pod 1 running")
        # 2. ("kubectl", "get pods", "pod 1 running")
        # 3. ("kubectl", "get pods", "pod 1 running")
        # All 3 are same. This IS stagnation > 2? 
        # Actually max_stagnation USUALLY means 'allowed number of times'.
        # If max_stagnation=2, executing it a 3rd time is NOT allowed if it matches?
        # Let's verify the code logic I wrote.
        
        # Code:
        # if len(self.history) < self.max_stagnation + 1: return
        # max_stagnation=2. Need 3 items.
        # On 3rd call, history length is 3.
        # items = history[-3:] => [1, 2, 3]
        # loop checks [1:] against [0].
        # 2 vs 1: same. 3 vs 1: same.
        # is_stagnant = True. Raises.
        
        # So max_stagnation=2 means you can do it 2 times, but the 3rd time it raises.
        # Which effectively means "Repeat limit = 2".
        
        try:
            detector.callback(MockStep("kubectl", "get pods", "pod 1 running"))
            self.fail("Should have raised LoopDetectedError")
        except LoopDetectedError as e:
            print(f"\nCaught expected error: {e}")

    def test_progress(self):
        detector = LoopDetector(max_stagnation=2)
        
        detector.callback(MockStep("kubectl", "get pods", "pod 1 running"))
        detector.callback(MockStep("kubectl", "get pods", "pod 1 running"))
        # Different output -> Progress
        detector.callback(MockStep("kubectl", "get pods", "pod 1 running\npod 2 pending"))
        
        # Should NOT raise
        print("\nProgress test passed (no raise).")

if __name__ == '__main__':
    unittest.main()
