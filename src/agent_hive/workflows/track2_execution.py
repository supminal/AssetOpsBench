"""
Track 2: Execution-Oriented Dynamic Multi-Agent Workflow
-------------------------------------------------------

Template for participants to implement a DynamicWorkflow.
This workflow is inspired by SequentialWorkflow, but allows for:
    - Multiple agents per task
    - Dynamic / conditional task execution
    - Parallel task execution (if desired)
    - Helper agents for fallback or support
    - Smarter context propagation across tasks

⚠️ IMPORTANT:
Participants are expected to edit ONLY the clearly marked TODO sections.
All other logic (executor, memory, orchestration) must remain unchanged.
"""

import json
from typing import List
from pydantic import Field

from agent_hive.enum import ContextType
from agent_hive.task import Task
from agent_hive.workflows.base_workflow import Workflow
from agent_hive.logger import get_custom_logger
from agent_hive.agents.base_agent import BaseAgent

logger = get_custom_logger(__name__)

# =========================================================
# 🛠️ EDITABLE SECTION for Participants
# 🎯 Purpose: Implement revision / validation of task inputs
#
# ✅ Allowed:
#   - Define your own revision rules (clarity check, validation, enrichment)
#   - Add formatting styles (bullet points, numbered lists, emojis, etc.)
#   - Suggest metadata (tags, difficulty, clarity score)
#   - Return multiple variants of a revision
#
# ❌ Not Allowed:
#   - Modify workflow execution logic outside this agent
#   - Replace the base ReAct agent or Executor
#   - Change memory persistence or retry logic
# =========================================================

class TaskRevisionHelperAgent(BaseAgent):
    """
    Template for TaskRevisionHelperAgent.
    Participants should implement logic for revising/validating tasks.
    """

    name = "TaskRevisionHelperAgent"
    description = "Revises, validates, and provides suggestions for task inputs."
    memory = []
    tools = []

    def __init__(self, llm: str = None, max_retries: int = 3):
        self.llm = llm
        self.max_retries = max_retries

    def execute_task(self, task_input: str) -> str:
        """
        Review and revise the given task input, suggesting improvements or validation.

        Args:
            task_input (str): The task description to revise.

        Returns:
            str: Revised/validated task description or feedback.
        """
        # =========================================================
        # 🚧 TODO: Implement your revision logic here
        # Example ideas:
        #   - Fix grammar / spelling
        #   - Improve clarity of task instructions
        #   - Suggest metadata (tags, difficulty, etc.)
        #   - Return multiple variants of the revision
        #
        # 👉 IMPORTANT: Do NOT modify anything outside this method
        # =========================================================
        
        # Quality assessment
        response_length = len(task_input.strip())
        has_data = any(keyword in task_input.lower() for keyword in 
                      ['found', 'data', 'value', 'result', 'output', 'analysis'])
        has_error = any(keyword in task_input.lower() for keyword in 
                       ['error', 'failed', 'unable', 'could not', 'exception'])
        
        # Quality score (0-10)
        quality_score = 0
        if response_length > 50:
            quality_score += 3
        if response_length > 150:
            quality_score += 2
        if has_data:
            quality_score += 3
        if not has_error:
            quality_score += 2
        
        # If quality is acceptable, return as-is with minimal formatting
        if quality_score >= 6:
            # Clean up the response
            cleaned_response = task_input.strip()
            # Remove any residual "Final Answer:" prefixes if present
            if "Final Answer:" in cleaned_response:
                cleaned_response = cleaned_response.split("Final Answer:")[-1].strip()
            return cleaned_response
        
        # For low quality responses, add context markers
        if has_error:
            return f"⚠️ Task execution encountered issues:\n{task_input.strip()}"
        elif response_length < 50:
            return f"ℹ️ Brief response received:\n{task_input.strip()}"
        else:
            return task_input.strip()


class DynamicWorkflow(Workflow):
    """
    DynamicWorkflow extends the baseline Workflow with more flexible
    execution strategies and multi-agent support.
    """

    context_type: ContextType = Field(
        default=ContextType.DISABLED, description="Type of context to use."
    )

    def __init__(
        self,
        tasks: List[Task],
        context_type: ContextType = ContextType.DISABLED,
        max_memory: int = 10,
    ):
        self.tasks = tasks
        self.context_type = context_type
        self.memory: List[str] = []
        self.max_memory = max_memory
        self._verify_tasks()

    def _verify_tasks(self):
        if not isinstance(self.tasks, list):
            raise ValueError("tasks must be a list of Task objects")

        for i, task in enumerate(self.tasks):
            if not task.agents:
                raise ValueError("Task must have at least one agent")

            if len(task.agents) > 1:
                logger.info(
                    f"Task {i+1} has {len(task.agents)} agents. "
                    "DynamicWorkflow must decide how to use them (primary, fallback, parallel, etc.)."
                )

            # Validate context dependencies
            if self.context_type == ContextType.SELECTED and isinstance(task.context, list):
                for context_task in task.context:
                    if context_task not in self.tasks[:i]:
                        raise ValueError(
                            "task.context must be a list of Task objects "
                            "that are part of the workflow"
                        )

    def run(self):
        """
        Execute tasks dynamically.
        Participants can edit only the marked TODO section to introduce:
            - parallelism
            - conditional execution
            - helper agents
            - fallback strategies
        """
        self.memory = []

        # =========================================================
        # 🚧 TODO: Participants can edit this section ONLY
        # 🎨 Purpose: Customize how agents are scheduled and executed
        #
        # ✅ Allowed:
        #   - Replace for-loop with while-loop (max iterations fixed at 15)
        #   - Use TaskRevisionHelperAgent to refine or validate responses
        #   - Experiment with combining multiple agent responses
        #   - Add fallback strategies (e.g., retry with helper agent)
        #
        # ❌ Not Allowed:
        #   - Remove safety cap on iterations (max = 15 must remain)
        #   - Change memory persistence logic
        #   - Replace Executor orchestration logic
        # =========================================================
        self.context_type = ContextType.SELECTED
        max_loops = 15
        i = 0
        
        # Initialize helper agent for response quality improvement
        helper = TaskRevisionHelperAgent()
        
        while i < len(self.tasks) and i < max_loops:
            task = self.tasks[i]
            task_no = i + 1
            logger.info(f"Task {task_no}: {task.description}")

            assigned_agents = task.agents

            # Build input with context
            user_input = self._build_input(task, i)

            # Strategy: Use multiple agents with fallback
            response = None
            execution_success = False
            
            # Try primary agent first
            try:
                logger.info(f"Executing with primary agent: {assigned_agents[0].name}")
                response = assigned_agents[0].execute_task(user_input)
                
                # Quality check on response
                response_quality = self._assess_response_quality(response)
                
                if response_quality >= 0.6:  # Quality threshold
                    execution_success = True
                    logger.info(f"Primary agent succeeded with quality score: {response_quality:.2f}")
                else:
                    logger.info(f"Primary agent response quality low: {response_quality:.2f}")
                    
            except Exception as e:
                logger.warning(f"Primary agent failed: {e}")
            
            # Fallback strategy: If primary agent failed or low quality, try secondary agents
            if not execution_success and len(assigned_agents) > 1:
                for fallback_idx in range(1, min(len(assigned_agents), 3)):  # Try up to 2 fallback agents
                    try:
                        logger.info(f"Trying fallback agent {fallback_idx}: {assigned_agents[fallback_idx].name}")
                        fallback_response = assigned_agents[fallback_idx].execute_task(user_input)
                        
                        fallback_quality = self._assess_response_quality(fallback_response)
                        
                        if fallback_quality > self._assess_response_quality(response or ""):
                            response = fallback_response
                            execution_success = True
                            logger.info(f"Fallback agent {fallback_idx} provided better response")
                            break
                    except Exception as e:
                        logger.warning(f"Fallback agent {fallback_idx} failed: {e}")
                        continue
            
            # If still no good response, use original or empty
            if response is None:
                response = "Task execution did not produce a valid response."
                logger.warning(f"Task {task_no} completed with no valid response")

            # Use helper agent to clean and validate the response
            response = helper.execute_task(response)
            
            # Clean up any remaining "Final Answer:" artifacts
            response = response.replace("Final Answer:", "").strip()
            
            # Store in memory
            self.memory.append(response)
            logger.info(f"Task {task_no} completed. Response length: {len(response)}")

            i += 1

        history = self.generate_history()
        print(json.dumps(history, indent=4))
        return history

    def _assess_response_quality(self, response: str) -> float:
        """
        Assess the quality of a response on a scale of 0.0 to 1.0.
        Helper method for fallback strategy.
        """
        if not response or len(response.strip()) == 0:
            return 0.0
        
        quality_score = 0.0
        response_lower = response.lower()
        
        # Length factor (up to 0.3)
        length = len(response.strip())
        if length > 200:
            quality_score += 0.3
        elif length > 100:
            quality_score += 0.2
        elif length > 50:
            quality_score += 0.1
        
        # Data presence (up to 0.3)
        data_keywords = ['found', 'data', 'value', 'result', 'output', 'analysis', 
                        'temperature', 'pressure', 'status', 'reading', 'measurement']
        data_count = sum(1 for keyword in data_keywords if keyword in response_lower)
        quality_score += min(0.3, data_count * 0.1)
        
        # Error indicators (negative score, up to -0.4)
        error_keywords = ['error', 'failed', 'unable', 'could not', 'exception', 
                         'not found', 'invalid', 'no data']
        error_count = sum(1 for keyword in error_keywords if keyword in response_lower)
        quality_score -= min(0.4, error_count * 0.15)
        
        # Completeness indicators (up to 0.2)
        if any(word in response_lower for word in ['completed', 'success', 'retrieved', 'identified']):
            quality_score += 0.2
        
        # Structure indicators (up to 0.2)
        if '\n' in response or ',' in response or ':' in response:
            quality_score += 0.1
        if any(char.isdigit() for char in response):
            quality_score += 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, quality_score))
    
    def _build_input(self, task: Task, idx: int) -> str:
        """Helper to build task input string based on context type."""
        if self.context_type == ContextType.DISABLED:
            return task.description

        elif self.context_type == ContextType.ALL:
            context = "\n".join(self.memory[-self.max_memory :])
            return f"{task.description}\n\nContext:\n{context}"

        elif self.context_type == ContextType.PREVIOUS:
            if not self.memory:
                return task.description
            context = self.memory[-1]
            return f"{task.description}\n\nContext:\n{context}"

        elif self.context_type == ContextType.SELECTED:
            context_tasks = task.context or []
            context = ""
            for context_task in context_tasks:
                idx = self.tasks.index(context_task)
                if idx >= len(self.memory):
                    raise IndexError(
                        f"Context task {context_task.description} not found in memory"
                    )
                context += self.memory[idx] + "\n"
            return f"{task.description}\n\nContext:\n{context}"

        else:
            raise ValueError(f"Invalid context_type: {self.context_type}")

    def generate_history(self):
        """
        Return structured execution history for evaluation.
        """
        history = []
        for i, task in enumerate(self.tasks):
            history.append(
                {
                    "task_number": i + 1,
                    "task_description": task.description,
                    "agent_names": [agent.name for agent in task.agents],
                    "response": self.memory[i] if i < len(self.memory) else None,
                }
            )
        return history
