# Copyright contributors to the ITBench project. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#!/usr/bin/env python
import datetime
import json
import os
import sys
import time
import subprocess

from lumyn.crew import LumynCrew
from lumyn.tools.observability_stack.get_alerts import GetAlertsCustomTool
from lumyn.tools.kubectl.nl2kubectl import NL2KubectlCustomTool
from lumyn.tools.observability_stack.get_topology_nodes import GetTopologyNodes
from lumyn.llm_backends.init_backend import (get_llm_backend_for_tools)

from collections import defaultdict

from langfuse.api.resources.observations.types.observations_views import ObservationsViews
from openinference.instrumentation.crewai import CrewAIInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor
from langfuse import get_client
from dotenv import load_dotenv

load_dotenv()

langfuse = get_client()

# This main file is intended to be a way for your to run your
# crew locally, so refrain from adding necessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def format_final_op():
    if "STRUCTURED_UNSTRUCTURED_OUTPUT_DIRECTORY_PATH" in os.environ:
        agent_op_dir = os.getenv(
            "STRUCTURED_UNSTRUCTURED_OUTPUT_DIRECTORY_PATH")
        incident_number = os.getenv("scenario_number")
    else:
        proj_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.getcwd())))
        incident_number = os.environ.get("INCIDENT_NUMBER")
        agent_op_dir = os.path.join(
            proj_dir, os.environ.get('SRE_AGENT_EVALUATION_DIRECTORY'),
            os.environ.get('SRE_AGENT_NAME_VERSION_NUMBER'),
            os.environ.get('MODEL_AGENTS').replace('/', '_'),
            incident_number, os.environ.get('EXP_NAME'))

    op_json = {"id": f"inc-{incident_number}"}

    try:
        with open(os.path.join(agent_op_dir, 'alert_start_time.txt')) as f:
            op_json["alert_start_time"] = f.read()
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except OSError as e:
        print(f"Could not read file: {e}")

    try:
        with open(os.path.join(agent_op_dir, 'diag_end_time.txt')) as f:
            op_json["diag_end_time"] = f.read()
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except OSError as e:
        print(f"Could not read file: {e}")

    diag_json = {}
    rem_json = {}
    try:
        with open(os.path.join(agent_op_dir,
                               'diagnosis_struct_out.json')) as f:
            diag_json = json.load(f)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

    try:
        with open(os.path.join(agent_op_dir,
                               'remediation_struct_out.json')) as f:
            rem_json = json.load(f)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

    op_json.update(diag_json)
    op_json.update(rem_json)

    with open(os.path.join(agent_op_dir, 'agent_output.json'),
              'w',
              encoding='utf-8') as f:
        json.dump(op_json, f, indent=4, separators=(',', ': '))


def run():
    """
    Run the crew.
    """
    try:
        subprocess.run('crewai reset-memories -a', shell=True, capture_output=False, text=True)
    except:
        print("no memories to clear")

    kubectl_otel_astronomy_shop = NL2KubectlCustomTool(llm_backend=get_llm_backend_for_tools())._execute_kubectl_command("sudo kubectl --kubeconfig /app/lumyn/config get pods -n otel-demo")
    # kubectl_dsb_hotel_researvation = NL2KubectlCustomTool(llm_backend=get_llm_backend_for_tools())._execute_kubectl_command("sudo kubectl --kubeconfig /app/lumyn/config get pods -n hotel-reservation")
    if kubectl_otel_astronomy_shop[1] != 0:
        raise Exception("KUBECONFIG is not configured correctly.")

    while True:
        alerts = GetAlertsCustomTool()._run()
        if alerts is not None and len(alerts) > 0:
            break

    while True:
        nodes = GetTopologyNodes()._run()
        if nodes is not None:
            with open(
                    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "tools", "report_generation", "data",
                                 "topology_nodes.json"), "w") as f:
                json.dump(nodes, f)
            if "STRUCTURED_UNSTRUCTURED_OUTPUT_DIRECTORY_PATH" in os.environ:
                with open(
                        os.path.join(
                            os.getenv(
                                "STRUCTURED_UNSTRUCTURED_OUTPUT_DIRECTORY_PATH"
                            ), "topology_nodes.json"), "w") as f:
                    json.dump(nodes, f)
            break

    inputs = {
        "alerts": alerts
    }

    if "STRUCTURED_UNSTRUCTURED_OUTPUT_DIRECTORY_PATH" in os.environ:
        eval_dir = os.getenv("STRUCTURED_UNSTRUCTURED_OUTPUT_DIRECTORY_PATH")
    else:
        proj_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.getcwd())))
        eval_dir = os.path.join(
            proj_dir, os.environ.get('SRE_AGENT_EVALUATION_DIRECTORY'),
            os.environ.get('SRE_AGENT_NAME_VERSION_NUMBER'),
            os.environ.get('MODEL_AGENTS').replace('/', '_'),
            os.environ.get('INCIDENT_NUMBER'), os.environ.get('EXP_NAME'))
    with open(os.path.join(eval_dir, 'alert_start_time.txt'), 'w') as f:
        f.write(datetime.datetime.now().isoformat())
    


    CrewAIInstrumentor().instrument(skip_dep_check=True)
    LangChainInstrumentor().instrument(skip_dep_check=True)
    LiteLLMInstrumentor().instrument(skip_dep_check=True)
    with langfuse.start_as_current_observation(as_type="span", name="crewai-index-trace"):
        LumynCrew().crew().kickoff(inputs=inputs)
    langfuse.flush()
    traces = langfuse.api.trace.list()
    if traces.data and len(traces.data) > 0:
        trace_detail = traces.data[0]  # Most recent trace
        # trace_id = trace.id

        # # Fetch full trace details
        # trace_detail = langfuse.api.trace.get(trace_id)

        # Extract metrics
        observations = langfuse.api.observations.get_many(trace_id=trace_detail.id)
        print("Observations page data:")
        print(observations.meta)
        _extract_metrics_from_trace(observations)
    format_final_op()

    def _extract_metrics_from_trace(self, observations: ObservationsViews):
        """Extract metrics from Langfuse trace data"""
        print("\n" + "=" * 80)
        print("TRACE OBSERVATIONS")
        print("=" * 80)

        tool_call_latencies = []
        reasoning_token_usages = []
        tasks_token_usages = defaultdict(list)
        tasks = []

        llm_call_count = 0
        for idx, obs in enumerate(observations.data, 1):
            print(f"\n📊 Observation #{idx}")
            print(f"{'─'*80}")

            # Get all attributes (excluding private/magic methods)
            all_attrs = [attr for attr in dir(obs) if not attr.startswith("_")]

            for attr in sorted(all_attrs):
                try:
                    value = getattr(obs, attr)
                    # Skip methods/callables
                    if not callable(value):
                        # Format attribute name with proper spacing
                        attr_display = attr.replace("_", " ").title()
                        if(attr_display == "Usage Details" and isinstance(value, dict)):
                            for k, v in value.items():
                                if("reasoning" in k.lower()):
                                    reasoning_token_usages.append((obs.name, k, v))
                        if(attr_display == "Metadata"):
                            if("attributes" in value and isinstance(value["attributes"], dict)):
                                for k, v in value["attributes"].items():
                                    if("task_id" in k.lower()):
                                        task_id = v
                                        obs_id = obs.id
                                        tasks.append((task_id, obs_id))
                        # Truncate long values
                        value_str = str(value)
                        if(attr_display == "Type" and value_str == "TOOL"):
                            tool_call_latencies.append((obs.name, obs.latency))
                        if len(value_str) > 100:
                            value_str = value_str[:97] + "..."
                        value_str = value_str.replace("\n", " ").replace("\r", " ").replace("\t", " ")
                        print(f"  {attr_display:<25} {value_str}")
                except Exception as e:
                    print(f"  {attr:<25} <Error: {str(e)[:50]}>")
            
            if obs.completion_start_time and obs.start_time:
                ttft = (obs.completion_start_time - obs.start_time).total_seconds()
                print(f"  {'Time To First Token':<25} {ttft:.4f} seconds")

            if getattr(obs, 'model', None) is not None:
                llm_call_count += 1

            
        for task_id, obs_id in tasks:
            for obs in observations.data:
                if obs.parent_observation_id == obs_id:
                    if(obs.usage_details):
                        tasks_token_usages[task_id].append(obs.usage_details)
            
        print("\n" + "=" * 80)
        print("PERFORMANCE REPORT & NFRs")
        print("=" * 80)

        # 1. Global Latency
        # Try to find the root span (usually the one with no parent or named 'crewai-index-trace')
        root_span = next((o for o in observations.data if not o.parent_observation_id), None)
        if not root_span:
             # Fallback: check for specific name
             root_span = next((o for o in observations.data if o.name == 'crewai-index-trace'), None)
        
        if root_span:
            latency_sec = 0.0
            if getattr(root_span, 'latency', None):
                 latency_sec = root_span.latency 
            elif root_span.end_time and root_span.start_time:
                 latency_sec = (root_span.end_time - root_span.start_time).total_seconds()
            print(f"{'End to End Latency':<25} {latency_sec:.2f} seconds")

        # 2. Total Cost
        total_cost = sum(getattr(o, 'calculated_total_cost', 0.0) or 0.0 for o in observations.data)
        if total_cost > 0:
            print(f"{'Total Cost':<25} ${total_cost:.4f}")
        
        print(f"{'Total LLM Calls':<25} {llm_call_count}")

        # 3. Planning Overhead (Reasoning Ratio)
        total_reasoning_tokens = 0
        total_output_tokens = 0
        
        for obs in observations.data:
            usage = getattr(obs, 'usage_details', {}) or {}
            # Check for reasoning tokens in various common keys
            r_tokens = usage.get('reasoning', 0)
            # Also check nested structure if valid
            if not r_tokens:
                 for k, v in usage.items():
                     if "reasoning" in k.lower() and isinstance(v, (int, float)):
                         r_tokens += v
            
            total_reasoning_tokens += r_tokens
            
            # Output tokens usually under 'output' or 'completion'
            out_tokens = usage.get('output', 0) or usage.get('completion', 0)
            total_output_tokens += out_tokens

        if total_output_tokens > 0:
            overhead_pct = (total_reasoning_tokens / total_output_tokens) * 100
            print(f"{'Planning Overhead':<25} {overhead_pct:.1f}% ({total_reasoning_tokens}/{total_output_tokens} tokens)")
        
        print("\nTokens Breakdown:")
        for task_id, usages in tasks_token_usages.items():
            average_usage = 0
            count = 0
            for usage in usages:
                if "total" in usage:
                    average_usage += usage["total"]
                    count += 1
            if count > 0:
                average_usage /= count
                print(f"\nAverage token usage for Task ID {task_id}: {average_usage} tokens")

        print(f"\n{'='*80}")
        print(f"Total Observations: {len(observations.data)}")
        print(f"{'='*80}\n")

        print("Tool Call Latencies:")
        for tool_name, latency in tool_call_latencies:
            print(f"  {tool_name}: {latency} ms")
        
        print("\nReasoning Token Usages:")
        for obs_name, usage_type, token_count in reasoning_token_usages:
            print(f"  {obs_name} - {usage_type}: {token_count} tokens")

def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "Problem diagnosis and remediation for an IT environment."
    }
    try:
        LumynCrew().crew().train(n_iterations=int(sys.argv[1]),
                                 filename=sys.argv[2],
                                 inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        LumynCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "Problem diagnosis and remediation for an IT environment."
    }
    try:
        LumynCrew().crew().test(n_iterations=int(sys.argv[1]),
                                openai_model_name=sys.argv[2],
                                inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")
