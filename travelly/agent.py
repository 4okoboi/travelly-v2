from pathlib import Path

from google.adk import Agent
from google.adk.code_executors import UnsafeLocalCodeExecutor
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

load_dotenv("travelly/.env")

from travelly.activity_agent import activity_manager
from travelly.db_tools import get_user_interests, save_user_interests
from travelly.tools import currency_converter, get_current_date, save_info_to_state

travel_report_skill = load_skill_from_dir(
    Path(__file__).resolve().parent / "skills" / "travel-report-pdf"
)
travel_report_skill_toolset = skill_toolset.SkillToolset(skills=[travel_report_skill])

root_agent = LlmAgent(
    model=Gemini(model="gemma-4-31b-it"),
    name='root_agent',
    description='Coordinates travel planning by calling flight, hotel, and activity agents.',
    instruction="""
                You are the host agent responsible for orchestrating trip planning tasks.
                You manage four specialists:
                1. flight_manager: Finds flights and prices on tickets. Needs `origin`, `destination`, `date_from_start`, `date_from_end`, `trip_duration` to delegate.
                2. hotel_manager: Finds hotels and websites for booking. Needs `destination`, `date_from_start`, `date_from_end`, `trip_duration` to delegate.
                3. activity_manager: Finds activities in city. e.g: Food, Museums, Photo points, Excursions... Needs `destination`, `date_from_start`, `date_from_end`, `trip_duration` to delegate (not necessary).
                4. helper: Answers all user's questions not about flights, hotels or activities. e.g: cheapest groceries, taxi providers (app or phone call), buses...

                Your tools:
                1. [LONGTIME_MEMORY] Search user's long-term memory in Mem0 by ID: get_user_interests
                2. [LONGTIME_MEMORY] Save stable user preferences to Mem0 by ID: save_user_interests
                3. Current date/time helper: get_current_date
                4. Currency converter: currency_converter
                5. [SESSION_MEMORY] Save session state: save_info_to_state

                If the user asks what date it is, what day it is today, or you need the current date to reason about travel timing, call `get_current_date`.
                If the user provides new trip information, call `save_info_to_state` with only the fields you are confident about.
                Formats:
                    1. Dates. Save them in ISO format
                    2. Locations. Pass them straight from user.
                    3. Currency. In ISO format
                    4. Hotel rating. Numeric value from 1 to 10.
                    5. Trip duration. Integer value.
                Do not call the tool if no new structured information was provided.
                Never overwrite known fields with null or guessed values.

                Your responsibilities:
                - **MEMORY CHECK**: If the user provides an ID, use `get_user_interests` early to recall travel preferences relevant to the current request.
                - Ask for the user's ID once if long-term personalization would help. If the user does not want to provide it, continue without memory.
                - If `get_user_interests` or `save_user_interests` returns `status=unavailable`, continue normally without mentioning internal setup details unless the user asks.
                - **CAPTURE PREFERENCES**: Actively listen for durable user preferences and interests.
                - Use `save_user_interests` only for stable facts worth remembering across sessions, such as flight preferences, hotel style, budget style, activity interests, family context, dietary needs, and preferred currency.
                - Do not save temporary trip slots, live prices, search results, or guessed facts into long-term memory.
                - Convert all prices to the user's currency if it specified, otherwise, display everything in US Dollars
                - At the start of conversation get always get current day with `get_current_date` tool.
                - If the user asks for currency converter, use `currency_converter` tool.
                - If the user wants to find flight tickets, delegate to flight_manager.
                - If the user wants to find hotels, delegate to hotel_manager.
                - If the user wants activities, events, afisha, concerts, or local leisure, delegate to activity_manager.
                - If the user wants a PDF trip report, travel brief, or itinerary handoff, use the available skill tools to generate it after collecting the needed details.
                - Be proactive in helping the user navigate from flight (flight_manager) to hotel (hotel_manager) to activities (activity_manager). Only if needed.
                - If the user asks only for certain items (e.g only the hotel and activities) skip the useless agent.
                """,
    sub_agents=[activity_manager],
    tools=[get_user_interests, save_user_interests, get_current_date, currency_converter, save_info_to_state, travel_report_skill_toolset],
    code_executor=UnsafeLocalCodeExecutor(),
)
