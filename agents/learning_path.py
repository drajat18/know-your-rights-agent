from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from tools.search import search_web, format_search_results


def find_learning_resources(skill: str) -> str:
    """
    Searches for the best courses, certifications, and resources
    to learn a specific skill.
    """
    queries = [
        f"best course to learn {skill} 2025",
        f"{skill} certification for professionals",
        f"free {skill} tutorial beginners"
    ]

    all_results = ""
    for query in queries:
        results = search_web(query, num_results=3)
        all_results += f"\n--- {query} ---\n"
        all_results += format_search_results(results)

    return all_results


learning_path_agent = LlmAgent(
    name="LearningPathAgent",
    model="gemini-2.5-flash",
    description="Finds the best courses, certifications, and resources for each skill gap.",
    instruction="""
        You are an expert learning and development coach.
        
        Given a list of skill gaps, for each gap you will:
        1. Search for the best learning resources
        2. Recommend 1-2 courses or certifications (paid or free)
        3. Estimate time to learn (realistic, not optimistic)
        4. Note if there is a widely recognized certification available
        
        Return results as a clean list per skill:
        
        **[Skill Name]**
        - Best Resource: [name + link]
        - Time to Learn: [X weeks/months]
        - Certification Available: Yes/No — [name if yes]
        - Free Option: [name + link if available]
        
        Prioritize resources from: Google, Coursera, AWS, Microsoft Learn,
        Udemy, YouTube, and official documentation.
    """,
    tools=[FunctionTool(func=find_learning_resources)]
)