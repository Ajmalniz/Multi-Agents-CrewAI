import chainlit as cl
from crewai import Agent, Task, Crew
import os
import json
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import warnings
import yaml
from typing import List
from pydantic import BaseModel, Field

# Pydantic Models (same as before)
class TaskEstimate(BaseModel):
    task_name: str = Field(..., description="Name of the task")
    estimated_time_hours: float = Field(..., description="Estimated time to complete the task in hours")
    required_resources: List[str] = Field(..., description="List of resources required to complete the task")

class Milestone(BaseModel):
    milestone_name: str = Field(..., description="Name of the milestone")
    tasks: List[str] = Field(..., description="List of task IDs associated with this milestone")

class ProjectPlan(BaseModel):
    tasks: List[TaskEstimate] = Field(..., description="List of tasks with their estimates")
    milestones: List[Milestone] = Field(..., description="List of project milestones")

# Load environment variables and configurations
warnings.filterwarnings("ignore")
load_dotenv(find_dotenv())

current_dir = os.path.dirname(os.path.abspath(__file__))
files = {
    'agents': os.path.join(current_dir, 'config', 'agents.yaml'),
    'tasks': os.path.join(current_dir, 'config', 'tasks.yaml')
}
configs = {}
for config_type, file_path in files.items():
    with open(file_path, 'r') as file:
        configs[config_type] = yaml.safe_load(file)

agents_config = configs['agents']
tasks_config = configs['tasks']

# Define agents
project_planning_agent = Agent(config=agents_config['project_planning_agent'])
estimation_agent = Agent(config=agents_config['estimation_agent'])
resource_allocation_agent = Agent(config=agents_config['resource_allocation_agent'])

# Define tasks
task_breakdown = Task(config=tasks_config['task_breakdown'], agent=project_planning_agent)
time_resource_estimation = Task(config=tasks_config['time_resource_estimation'], agent=estimation_agent)
resource_allocation = Task(config=tasks_config['resource_allocation'], agent=resource_allocation_agent, output_pydantic=ProjectPlan)

# Chainlit setup
@cl.on_chat_start
async def start():
    # Initialize session variables to store inputs
    cl.user_session.set("inputs", {})
    cl.user_session.set("step", "project_type")
    await cl.Message(content="Welcome to the Project Planning Assistant! Let's start.\n\nWhat is the project type? (e.g., Website, Mobile App)").send()

@cl.on_message
async def main(message: cl.Message):
    current_step = cl.user_session.get("step")
    inputs = cl.user_session.get("inputs")

    # Store the user's response for the current step
    user_response = message.content.strip()
    if not user_response:
        await cl.Message(content="Please provide a valid input.").send()
        return

    # Process the input based on the current step
    if current_step == "project_type":
        inputs["project_type"] = user_response
        cl.user_session.set("step", "project_objectives")
        await cl.Message(content="Great! What are the project objectives? (e.g., 'Create a website for a small business')").send()

    elif current_step == "project_objectives":
        inputs["project_objectives"] = user_response
        cl.user_session.set("step", "industry")
        await cl.Message(content="Nice! Which industry does this project belong to? (e.g., Technology, Healthcare)").send()

    elif current_step == "industry":
        inputs["industry"] = user_response
        cl.user_session.set("step", "team_members")
        await cl.Message(content="Got it! Please list the team members (e.g., 'Ajmal Khan (Project Manager), Abdul Raqeeb (Designer)')").send()

    elif current_step == "team_members":
        inputs["team_members"] = user_response
        cl.user_session.set("step", "project_requirements")
        await cl.Message(content="Almost there! What are the project requirements? (Provide a detailed list, one per line or as a paragraph)").send()

    elif current_step == "project_requirements":
        inputs["project_requirements"] = user_response
        cl.user_session.set("step", "done")

        # All inputs collected, now process with CrewAI
        await cl.Message(content="Thank you! Processing your project plan now...").send()

        # Create and run the crew
        crew = Crew(
            agents=[project_planning_agent, estimation_agent, resource_allocation_agent],
            tasks=[task_breakdown, time_resource_estimation, resource_allocation],
            verbose=True
        )

        result = crew.kickoff(inputs=inputs)

        # Handle the result
        if isinstance(result, ProjectPlan):
            project_plan = result
        else:
            try:
                raw_data = json.loads(result.raw)
                project_plan = ProjectPlan(**raw_data)
            except json.JSONDecodeError as e:
                await cl.Message(content=f"Error parsing result: {e}\nRaw output: {result.raw}").send()
                return

        # Format and send the response
        tasks_df = pd.DataFrame(project_plan.model_dump()['tasks'])
        milestones_df = pd.DataFrame(project_plan.model_dump()['milestones'])

        response = (
            "## Project Plan\n\n"
            "### Tasks\n" + tasks_df.to_markdown(index=False) + "\n\n"
            "### Milestones\n" + milestones_df.to_markdown(index=False)
        )
        await cl.Message(content=response).send()

        # Save outputs (optional)
        with open('project_plan.json', 'w', encoding='utf-8') as f:
            json.dump(project_plan.model_dump(), f, indent=4)
        with open('Project_Planning.md', 'w', encoding='utf-8') as f:
            f.write(response)

        # Reset for a new project (optional)
        cl.user_session.set("inputs", {})
        cl.user_session.set("step", "project_type")
        await cl.Message(content="Project plan generated! Would you like to start a new project? If so, what is the project type?").send()

if __name__ == "__main__":
    pass