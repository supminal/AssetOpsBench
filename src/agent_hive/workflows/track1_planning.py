from agent_hive.task import Task
from pydantic import Field
from typing import List
from agent_hive.enum import ContextType
import json
from agent_hive.workflows.base_workflow import Workflow
from reactxen.utils.model_inference import watsonx_llm
import re
from agent_hive.workflows.sequential import SequentialWorkflow
from agent_hive.agents.plan_reviewer_agent import PlanReviewerAgent
from agent_hive.logger import get_custom_logger

logger = get_custom_logger(__name__)

# =========================================================
# TODO: Participants can edit this section ONLY
# Add variable, dict. no more any import just any inline code
# =========================================================

# Agent capability mapping for better understanding
AGENT_CAPABILITIES = {
    "IoT Agent": ["sensor data", "building systems", "HVAC", "equipment monitoring", "real-time data"],
    "FMSR Agent": ["failure analysis", "root cause", "failure modes", "diagnostics", "maintenance"],
    "TSFM Agent": ["forecasting", "prediction", "time series", "trends", "future values"],
    "WO Agent": ["work orders", "maintenance tasks", "scheduling", "task management"]
}

# Task complexity indicators
COMPLEXITY_KEYWORDS = {
    "simple": ["get", "fetch", "show", "display", "list"],
    "moderate": ["analyze", "compare", "identify", "determine"],
    "complex": ["predict", "forecast", "diagnose", "optimize", "troubleshoot"]
}

# =========================================================
# END OF EDITABLE SECTION


class NewPlanningWorkflow(Workflow):
    """
    Participant Template for Planning Review Workflow.
    ---------------------------------------------------
    📝 Instructions for participants:
    - Only modify the section marked with "TODO: Edit prompt here"
    - Do NOT change any workflow logic, agents, or execution components
    - Keep all retry, memory, and sequential execution intact
    """

    llm: str = Field(description="LLM used by the task planning.")

    def __init__(self, tasks: List[Task], llm: str):
        self.tasks = tasks
        self.memory = []
        self.max_memory = 10
        self.llm = llm
        self.max_retries = 5
        self._verify_tasks()

    def _verify_tasks(self):
        if not isinstance(self.tasks, list):
            raise ValueError("tasks must be a list of Task objects")
        if len(self.tasks) != 1:
            raise ValueError("Planning only supports one task")
        task = self.tasks[0]
        if task.agents is None or len(task.agents) < 1:
            raise ValueError("Task must have at least one agent")

    def run(self, enable_summarization=False):
        generated_steps = self.generate_steps()

        sequential_workflow = SequentialWorkflow(
            tasks=generated_steps, context_type=ContextType.SELECTED
        )

        return sequential_workflow.run()

    def generate_steps(self, save_plan=False, saved_plan_filename=""):
        task = self.tasks[0]
        agent_descriptions = ""

        # =========================================================
        # TODO: Participants can edit this section ONLY
        # 🎨 Purpose: Customize how agent information is collected and formatted
        # ✅ Allowed: 
        #     - Change numbering style or bullet points
        #     - Include additional metadata (e.g., agent capabilities, tags)
        #     - Provide examples in a different format
        #     - Add emojis or formatting to make the prompt clearer 
        #     - More thinking
        # ❌ Not allowed: 
        #     - Modify workflow execution
        #     - Replace the base ReAct agent or Executor
        #     - Change memory or retry logic
        # =========================================================

        for ii, aagent in enumerate(task.agents):
            agent_descriptions += f"\n{'='*60}\n"
            agent_descriptions += f"🤖 AGENT #{ii + 1}: {aagent.name}\n"
            agent_descriptions += f"{'='*60}\n"
            
            # Enhanced description with emojis
            agent_descriptions += f"📋 Description: {aagent.description}\n"
            
            # Add capability tags if available
            if aagent.name in AGENT_CAPABILITIES:
                capabilities = AGENT_CAPABILITIES[aagent.name]
                agent_descriptions += f"\n🎯 Key Capabilities:\n"
                for cap in capabilities:
                    agent_descriptions += f"   ✓ {cap}\n"
            
            # Enhanced task examples with better formatting
            if "task_examples" in aagent.__dict__ and aagent.task_examples:
                agent_descriptions += f"\n💡 Example Tasks This Agent Can Solve:\n"
                for idx, task_example in enumerate(aagent.task_examples, start=1):
                    agent_descriptions += f"   {idx}. {task_example}\n"
            
            # Add usage guidelines
            agent_descriptions += f"\n📝 Best Used For: "
            if "IoT" in aagent.name:
                agent_descriptions += "Retrieving real-time sensor data and monitoring building systems\n"
            elif "FMSR" in aagent.name:
                agent_descriptions += "Analyzing failure modes and diagnosing equipment issues\n"
            elif "TSFM" in aagent.name or "Forecast" in aagent.name:
                agent_descriptions += "Predicting future trends and forecasting time series data\n"
            elif "WO" in aagent.name or "Work" in aagent.name:
                agent_descriptions += "Managing work orders and scheduling maintenance tasks\n"
            else:
                agent_descriptions += "Specialized task execution\n"
            
            agent_descriptions += "\n"

        # =========================================================
        # END OF EDITABLE SECTION
        # 🚫 Participants should not modify code below this line
        # ❌ No new variables, functions, or workflow logic allowed
        # ✅ Only modify the section marked as TODO above
        # =========================================================

        prompt = self.get_prompt(task.description, agent_descriptions)
        logger.info(f"Plan Generation Prompt: \n{prompt}")
        llm_response = watsonx_llm(
            prompt, model_id=self.llm,
        )["generated_text"]
        logger.info(f"Plan: \n{llm_response}")

        final_plan = llm_response
        self.memory = []

        task_pattern = r"#Task\d+: (.+)"
        agent_pattern = r"#Agent\d+: (.+)"
        dependency_pattern = r"#Dependency\d+: (.+)"
        output_pattern = r"#ExpectedOutput\d+: (.+)"

        tasks = re.findall(task_pattern, final_plan)
        agents = re.findall(agent_pattern, final_plan)
        dependencies = re.findall(dependency_pattern, final_plan)
        outputs = re.findall(output_pattern, final_plan)

        if save_plan:
            if not saved_plan_filename.endswith(".txt"):
                saved_plan_filename += ".txt"

            saved_plan_text = f"Question: {task.description}\nPlan:\n{final_plan}"
            with open(saved_plan_filename, "w") as f:
                f.write(saved_plan_text)

        planned_tasks = []
        for i in range(len(tasks)):
            task_description = tasks[i]
            if i == len(agents):
                break
            agent_name = agents[i]
            if i < len(dependencies):
                dependency = dependencies[i]
            else:
                dependency = "None"
            if i < len(outputs):
                expected_output = outputs[i]
            else:
                expected_output = ""

            selected_agent = None
            for agent in task.agents:
                if agent.name == agent_name:
                    selected_agent = agent
                    break
            if selected_agent is None:
                selected_agent = task.agents[0]

            if dependency != "None":
                numbers = re.findall(r"#S(\d+)", dependency)
                numbers = list(map(int, numbers))
                context = [planned_tasks[i - 1] for i in numbers]
            else:
                context = []

            a_task = Task(
                description=task_description,
                expected_output=expected_output,
                agents=[selected_agent],
                context=context,
            )
            planned_tasks.append(a_task)

        logger.info(f"Planned Tasks: \n{planned_tasks}")

        return planned_tasks

    def get_prompt(self, task_description, agent_descriptions):
        # =========================================================
        # TODO: Participants can edit this section ONLY
        # 🎨 Purpose: Improve prompt clarity, formatting, emojis, guidance
        # ✅ Allowed: Wording, structure, examples, emojis
        # ❌ Not allowed: Changing workflow, ReAct agent, Executor, or memory logic
        # =========================================================

        prompt = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎯 EXPERT TASK PLANNING ASSISTANT                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are an expert AI planning assistant specializing in creating efficient, well-structured 
step-by-step plans for complex asset operations and building management problems.

🎯 YOUR MISSION:
Create an optimal execution plan using the available specialist agents. Each agent has 
specific expertise - use them wisely to maximize efficiency and accuracy.

📋 CRITICAL PLANNING RULES:
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✓ MUST use ONLY the agents listed below - NO exceptions                    │
│ ✓ Keep plan concise: Maximum 5 steps (fewer is better if possible)         │
│ ✓ Each step must be atomic and achievable by a single agent                │
│ ✓ Clearly specify dependencies to ensure proper execution order            │
│ ✓ Make task descriptions detailed, specific, and unambiguous               │
│ ✓ Expected outputs should be concrete and measurable                       │
└─────────────────────────────────────────────────────────────────────────────┘

🏗️ PLANNING STRATEGY:
1️⃣ Understand the Problem: Break down the complex task into logical components
2️⃣ Match Agents to Tasks: Select the most appropriate agent for each component
3️⃣ Sequence Dependencies: Ensure data flows correctly between steps
4️⃣ Minimize Steps: Combine tasks when possible without losing clarity
5️⃣ Validate Completeness: Ensure the plan fully addresses the problem

📐 REQUIRED OUTPUT FORMAT:
Each step MUST follow this exact structure (replace <...> with actual content):

## Step 1
#Task1: <Clear, detailed description of what needs to be done - include all necessary parameters, time ranges, equipment IDs, etc.>
#Agent1: <exact_agent_name_from_list_below>
#Dependency1: None
#ExpectedOutput1: <Specific, measurable output - what data/result will this step produce?>

## Step 2
#Task2: <Next task description with complete details>
#Agent2: <exact_agent_name_from_list_below>
#Dependency2: [#S1] (or [#S1, #S2] or None if no dependencies)
#ExpectedOutput2: <Clear expected output>

## Step 3 (if needed)
#Task3: <Task description>
#Agent3: <exact_agent_name_from_list_below>
#Dependency3: [#S1, #S2] (reference any previous steps needed)
#ExpectedOutput3: <Expected output>

... and so on (up to Step 5 maximum)

═══════════════════════════════════════════════════════════════════════════════

🤖 AVAILABLE SPECIALIST AGENTS:
{agent_descriptions}

═══════════════════════════════════════════════════════════════════════════════

❓ PROBLEM TO SOLVE:
{task_description}

═══════════════════════════════════════════════════════════════════════════════

💡 QUALITY CHECKLIST (Review before submitting your plan):
☐ Each task is specific and actionable
☐ Agent selection matches task requirements
☐ Dependencies are correctly specified
☐ Expected outputs are concrete and measurable
☐ Plan is minimal yet complete (≤5 steps)
☐ Step sequence is logical and efficient

═══════════════════════════════════════════════════════════════════════════════

🚀 YOUR GENERATED PLAN (output ONLY the plan, no additional commentary):
"""
        # =========================================================
        # End of participant editable section
        # =========================================================
        return prompt
