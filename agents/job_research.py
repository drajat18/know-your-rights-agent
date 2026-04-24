from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from tools.search import search_web, format_search_results


def research_job_requirements(target_role: str) -> str:
    """
    Searches the web for real job postings for the target role
    and returns a summary of required skills and qualifications.
    """
    queries = [
        f"{target_role} job requirements skills 2025",
        f"{target_role} job description must have qualifications",
        f"{target_role} entry level vs senior skills needed"
    ]

    all_results = ""
    for query in queries:
        results = search_web(query, num_results=4)
        all_results += f"\n--- Search: {query} ---\n"
        all_results += format_search_results(results)

    return all_results


job_research_agent = LlmAgent(
    name="JobResearchAgent",
    model="gemini-2.5-flash",
    description="Searches the web for real job postings and extracts required skills for a target role.",
    instruction="""
        You are a job market research expert.
        
        Given a target job title, you will:
        1. Analyze the search results provided to you
        2. Extract the most commonly required technical skills
        3. Extract soft skills and qualifications
        4. Note experience level requirements
        5. Identify any certifications or degrees mentioned
        
        Return a clean structured summary with these sections:
        - Technical Skills Required
        - Soft Skills Required  
        - Experience Requirements
        - Certifications/Education
        - Key Themes (what comes up most across postings)
        
        Be specific and concrete. No fluff.
    """,
    tools=[FunctionTool(func=research_job_requirements)]
)