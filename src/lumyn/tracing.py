from collections import defaultdict
from langfuse.api.resources.commons.types.observations_view import ObservationsView
import langfuse
import json
import datetime
from typing import List

def _extract_metrics_from_trace(observations_data: List[ObservationsView]):
    """Extract metrics from Langfuse trace data"""

    # print("\n" + "=" * 80)
    # print("TRACE OBSERVATIONS")
    # print("=" * 80)

    tool_call_latencies = []
    reasoning_token_usages = []
    tasks_token_usages = defaultdict(list)
    tasks = []

    # List to store all observations for JSON dump
    all_observations_data = []

    llm_call_count = 0
    for idx, obs in enumerate(observations_data):
        # print(f"\n📊 Observation #{idx}")
        # print(f"{'─'*80}")
        
        # Dict to store processed observation data
        # Use by_alias=False to avoid mixed casing (camelCase aliases vs snake_case attributes)
        try:
            obs_dict = obs.dict(by_alias=False, exclude_unset=False, exclude_none=False)
        except TypeError:
            print("CHECK!!")
            # Fallback if by_alias is not supported
            obs_dict = obs.dict()

        all_observations_data.append(obs_dict)

        # Ensure we have at least usage_details initialized
        # if "usage_details" not in obs_dict:
        #      obs_dict["usage_details"] = getattr(obs, "usage_details", {})

        # Get all attributes (excluding private/magic methods)
    #     all_attrs = [attr for attr in dir(obs) if not attr.startswith("_")]

    #     for attr in sorted(all_attrs):
    #         try:
    #             value = getattr(obs, attr)
    #             # Store in dict if not already present (and if serializable)
    #             # We'll handle serialization cleanup at the end
    #             # if attr not in obs_dict and not callable(value):
    #             #      obs_dict[attr] = value

    #             # Skip methods/callables
    #             if not callable(value):
    #                 # Format attribute name with proper spacing
    #                 attr_display = attr.replace("_", " ").title()
    #                 if(attr_display == "Usage Details" and isinstance(value, dict)):
    #                     for k, v in value.items():
    #                         if("reasoning" in k.lower()):
    #                             reasoning_token_usages.append((obs.name, k, v))
    #                 if(attr_display == "Metadata"):
    #                     if("attributes" in value and isinstance(value["attributes"], dict)):
    #                         for k, v in value["attributes"].items():
    #                             if("task_id" in k.lower()):
    #                                 task_id = v
    #                                 obs_id = obs.id
    #                                 tasks.append((task_id, obs_id))
    #                                 # Add task_id to obs_dict
    #                                 # obs_dict["task_id"] = task_id
                                    
    #                 # Truncate long values
    #                 value_str = str(value)
    #                 if(attr_display == "Type" and value_str == "TOOL"):
    #                     tool_call_latencies.append((obs.name, obs.latency))
    #                 if len(value_str) > 100:
    #                     value_str = value_str[:97] + "..."
    #                 value_str = value_str.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    #                 print(f"  {attr_display:<25} {value_str}")
    #         except Exception as e:
    #             print(f"  {attr:<25} <Error: {str(e)[:50]}>")
        
    #     if obs.completion_start_time and obs.start_time:
    #         ttft = (obs.completion_start_time - obs.start_time).total_seconds()
    #         print(f"  {'Time To First Token':<25} {ttft:.4f} seconds")
    #         # obs_dict["time_to_first_token"] = ttft

    #     if getattr(obs, 'model', None) is not None:
    #         llm_call_count += 1
        
        

        
    # for task_id, obs_id in tasks:
    #     for obs in observations_data:
    #         if obs.parent_observation_id == obs_id:
    #             if(obs.usage_details):
    #                 tasks_token_usages[task_id].append(obs.usage_details)
        
    # print("\n" + "=" * 80)
    # print("PERFORMANCE REPORT & NFRs")
    # print("=" * 80)

    # # 1. Global Latency
    # # Try to find the root span (usually the one with no parent or named 'crewai-index-trace')
    # root_span = next((o for o in observations_data if not o.parent_observation_id), None)
    # if not root_span:
    #         # Fallback: check for specific name
    #         root_span = next((o for o in observations_data if o.name == 'crewai-index-trace'), None)
    
    # if root_span:
    #     latency_sec = 0.0
    #     if getattr(root_span, 'latency', None):
    #             latency_sec = root_span.latency 
    #     elif root_span.end_time and root_span.start_time:
    #             latency_sec = (root_span.end_time - root_span.start_time).total_seconds()
    #     print(f"{'End to End Latency':<25} {latency_sec:.2f} seconds")

    # # 2. Total Cost
    # total_cost = sum(getattr(o, 'calculated_total_cost', 0.0) or 0.0 for o in observations_data)
    # if total_cost > 0:
    #     print(f"{'Total Cost':<25} ${total_cost:.4f}")
    
    # print(f"{'Total LLM Calls':<25} {llm_call_count}")

    # # 3. Planning Overhead (Reasoning Ratio)
    # total_reasoning_tokens = 0
    # total_output_tokens = 0
    
    # for obs in observations_data:
    #     usage = getattr(obs, 'usage_details', {}) or {}
    #     # Check for reasoning tokens in various common keys
    #     r_tokens = usage.get('reasoning', 0)
    #     # Also check nested structure if valid
    #     if not r_tokens:
    #             for k, v in usage.items():
    #                 if "reasoning" in k.lower() and isinstance(v, (int, float)):
    #                     r_tokens += v
        
    #     total_reasoning_tokens += r_tokens
        
    #     # Output tokens usually under 'output' or 'completion'
    #     out_tokens = usage.get('output', 0) or usage.get('completion', 0)
    #     total_output_tokens += out_tokens

    # if total_output_tokens > 0:
    #     overhead_pct = (total_reasoning_tokens / total_output_tokens) * 100
    #     print(f"{'Planning Overhead':<25} {overhead_pct:.1f}% ({total_reasoning_tokens}/{total_output_tokens} tokens)")
    
    # print("\nTokens Breakdown:")
    # for task_id, usages in tasks_token_usages.items():
    #     average_usage = 0
    #     count = 0
    #     for usage in usages:
    #         if "total" in usage:
    #             average_usage += usage["total"]
    #             count += 1
    #     if count > 0:
    #         average_usage /= count
    #         print(f"\nAverage token usage for Task ID {task_id}: {average_usage} tokens")
            
    #         # Inject average usage into relevant observations ?? 
    #         # Or just add a separate report entry in the json? 
    #         # For now, let's keep it simple and just dump the observations.
    #         # We could add a 'metrics_summary' to the end of the list or wrap it.
    #         # But the user said "dump all observations to one json file", implying a list of observations.

    # print(f"\n{'='*80}")
    # print(f"Total Observations: {len(observations_data)}")
    # print(f"{'='*80}\n")

    # print("Tool Call Latencies:")
    # for tool_name, latency in tool_call_latencies:
    #     print(f"  {tool_name}: {latency} ms")
    
    # print("\nReasoning Token Usages:")
    # for obs_name, usage_type, token_count in reasoning_token_usages:
    #     print(f"  {obs_name} - {usage_type}: {token_count} tokens")

    # Serialize and Save to JSON
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return str(obj)

    try:
        with open("observations_dump.json", "w") as f:
            json.dump(all_observations_data, f, default=json_serial, indent=2)
        print(f"\n[INFO] Observations dumped to 'observations_dump.json'")
    except Exception as e:
        print(f"\n[ERROR] Failed to dump observations to JSON: {e}")

if __name__ == "__main__":
    from langfuse import get_client
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Initialize the client (assumes env vars are set)
    langfuse_client = get_client()
    
    # List traces to get the most recent one
    # Note: Use the client instance 'langfuse_client', not the module 'langfuse'
    traces = langfuse_client.api.trace.list(page=1, limit=1)
    
    if traces.data:
        trace_detail = traces.data[0]
        print(f"Fetching observations for trace ID: {trace_detail.id}")
        
        all_observations = []
        page = 1
        while True:
            # Use the client instance to access the API
            observations = langfuse_client.api.observations.get_many(trace_id=trace_detail.id, page=page, limit=50)
            if not observations.data:
                break
            all_observations.extend(observations.data)
            if page >= observations.meta.total_pages:
                break
            page += 1
            
        print(f"Total observations fetched: {len(all_observations)}")
        
        # Verify root span presence
        root_spans = [o for o in all_observations if not o.parent_observation_id]
        if root_spans:
            print(f"[INFO] Found {len(root_spans)} root span(s): {[o.name for o in root_spans]}")
        else:
            print("[WARN] No root span (parent_observation_id=None) found in this trace!")
            
        _extract_metrics_from_trace(all_observations)
    else:
        print("No traces found.")