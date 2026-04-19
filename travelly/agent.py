from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm

from typing import Optional, Any


def save_info_to_state(
        destination: Optional[str] = None,
        origin: Optional[str] = None,
        date_from_start: Optional[str] = None,
        date_from_end: Optional[str] = None,
        date_to_start: Optional[str] = None,
        date_to_end: Optional[str] = None,
        trip_duration: Optional[int] = None,
        default_currency: Optional[str] = None,
        hotel_rating: Optional[str] = None,
        tool_context=None,
) -> dict[str, Any]:
    state = tool_context.state

    if "trip" not in state:
        state["trip"] = {
            "destination": None,
            "origin": None,
            "date_from_start": None,
            "date_from_end": None,
            "date_to_start": None,
            "date_to_end": None,
            "trip_duration": None,
            "default_currency": None,
            "hotel_rating": None,
        }

    updated_fields = {}

    def maybe_update(field_name: str, value: Optional[str]):
        if value is not None:
            state["trip"][field_name] = value
            updated_fields[field_name] = value

    maybe_update("destination", destination)
    maybe_update("origin", origin)
    maybe_update("date_from_start", date_from_start)
    maybe_update("date_from_end", date_from_end)
    maybe_update("date_to_start", date_to_start)
    maybe_update("date_to_end", date_to_end)
    maybe_update("default_currency", default_currency)
    maybe_update("hotel_rating", hotel_rating)
    maybe_update("trip_duration", trip_duration)

    return {
        "status": "ok",
        "updated_fields": updated_fields,
        "trip": state["trip"],
    }


root_agent = Agent(
    model=LiteLlm('ollama/qwen3.5:4b'),
    name='root_agent',
    description='Coordinates travel planning by calling flight, hotel, and activity agents.',
    instruction="""
                You are the host agent responsible for orchestrating trip planning tasks.
                You manage three specialists:
                1. flight_manager: Finds flights and prices on tickets
                2. hotel_manager: Finds hotels and websites for booking
                3. activity_manager: Finds activities in city. e.g: Food, Museums, Photo points, Excursions...
                4. helper: Answers all user's questions not about flights, hotels or activities. e.g: cheapest groceries, taxi providers (app or phone call), buses... 
                
                Your tools:
                1. [LONGTIME_MEMORY] Get user's interests from DB by ID: get_user_interests
                2. [LONGTIME_MEMORY] Save user's interests to DB by ID: save_user_interests
                3. Currency converter: currency_converter 
                4. [SESSION_MEMORY] Save session state: save_info_to_state
                
                If the user provides new trip information, call `save_info_to_state` with only the fields you are confident about.
                Do not call the tool if no new structured information was provided.
                Never overwrite known fields with null or guessed values.
                
                Your responsibilities:
                - **MEMORY CHECK**: At the start of conversation, use `get_user_interests` (if ID provided) to get all users interests from your memory.
                - Ask users ID, if it not provided. If user not providing his ID, skip all Memory parts
                - **CAPTURE PREFERENCES**: Actively listen for user preferences, interests
                - Convert all prices to the user's currency if it specified, otherwise, display everything in US Dollars
                - If the user asks for currency converter, use `currency_converter` tool. 
                - If the user wants to find flight tickets, delegate to flight_manager.
                - If the user wants to find hotels, delegate to hotel_manager.
                - If the user wants to find activities, delegate to activity_manager.
                - Be proactive in helping the user navigate from flight (flight_manager) to hotel (hotel_manager) to activities (activity_manager). Only if needed.
                - If the user asks only for certain items (e.g only the hotel and activities) skip the useless agent.   
                """,
    sub_agents=[],
    tools=[save_info_to_state]
)
