from crewai import Agent, Task, Crew
import os
import json
import pandas as pd  # Added for DataFrame functionality
from dotenv import load_dotenv, find_dotenv
import warnings
import yaml
from typing import List
from pydantic import BaseModel, Field

# Pydantic Models
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

project_planning_agent = Agent(config=agents_config['project_planning_agent'])
estimation_agent = Agent(config=agents_config['estimation_agent'])
resource_allocation_agent = Agent(config=agents_config['resource_allocation_agent'])

task_breakdown = Task(config=tasks_config['task_breakdown'], agent=project_planning_agent)
time_resource_estimation = Task(config=tasks_config['time_resource_estimation'], agent=estimation_agent)
resource_allocation = Task(config=tasks_config['resource_allocation'], agent=resource_allocation_agent, output_pydantic=ProjectPlan)

def main():
    crew = Crew(
        agents=[project_planning_agent, estimation_agent, resource_allocation_agent],
        tasks=[task_breakdown, time_resource_estimation, resource_allocation],
        verbose=True
    )

    project = 'Website'
    industry = 'Technology'
    project_objectives = 'Create a website for a small business'
    team_members = """
    - Ajmal Khan (Project Manager)
    - Ajmal Khan (Software Engineer)
    - Abdul Raqeeb (Designer)
    - Musadic (QA Engineer)
    - Abdul Baseer (QA Engineer)
    """
    project_requirements = """
    - Create a responsive design that works well on desktop and mobile devices
    - Implement a modern, visually appealing user interface with a clean look
    - Develop a user-friendly navigation system with intuitive menu structure
    - Include an "About Us" page highlighting the company's history and values
    - Design a "Services" page showcasing the business's offerings with descriptions
    - Create a "Contact Us" page with a form and integrated map for communication
    - Implement a blog section for sharing industry news and company updates
    - Ensure fast loading times and optimize for search engines (SEO)
    - Integrate social media links and sharing capabilities
    - Include a testimonials section to showcase customer feedback and build trust
    """
    inputs = {
        'project_type': project,
        'project_objectives': project_objectives,
        'industry': industry,
        'team_members': team_members,
        'project_requirements': project_requirements
    }

    # Run the crew
    result = crew.kickoff(inputs=inputs)
    
    # Save as JSON
    if isinstance(result, ProjectPlan):
        with open('project_plan.json', 'w', encoding='utf-8') as f:
            json.dump(result.model_dump(), f, indent=4)
    else:
        try:
            raw_data = json.loads(result.raw)
            project_plan = ProjectPlan(**raw_data)
            with open('project_plan.json', 'w', encoding='utf-8') as f:
                json.dump(project_plan.model_dump(), f, indent=4)
        except json.JSONDecodeError as e:
            print(f"Error parsing raw output: {e}")
            with open('project_plan.json', 'w', encoding='utf-8') as f:
                f.write(result.raw)

    # Save Markdown
    with open('Project_Planning.md', 'w', encoding='utf-8') as f:
        f.write(str(result))

    # Convert to DataFrames and save as HTML
    tasks = project_plan.model_dump()['tasks']
    df_tasks = pd.DataFrame(tasks)
    styled_tasks = df_tasks.style.set_table_attributes('border="1"').set_caption("Task Details").set_table_styles(
        [{'selector': 'th, td', 'props': [('font-size', '120%')]}]
    )

    milestones = project_plan.model_dump()['milestones']
    df_milestones = pd.DataFrame(milestones)
    styled_milestones = df_milestones.style.set_table_attributes('border="1"').set_caption("Milestone Details").set_table_styles(
        [{'selector': 'th, td', 'props': [('font-size', '120%')]}]
    )

    # Save styled DataFrames as HTML
    with open('project_tasks.html', 'w', encoding='utf-8') as f:
        f.write(styled_tasks.to_html())
    with open('project_milestones.html', 'w', encoding='utf-8') as f:
        f.write(styled_milestones.to_html())

    return result

if __name__ == "__main__":
    main()