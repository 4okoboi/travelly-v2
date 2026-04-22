import json
from datetime import datetime
from urllib import error, parse, request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from typing import Optional, Any


def get_current_date(timezone_name: Optional[str] = None) -> dict[str, str]:
    """Returns the current date and time for the requested IANA timezone."""
    try:
        tz = ZoneInfo(timezone_name) if timezone_name else datetime.now().astimezone().tzinfo
    except ZoneInfoNotFoundError:
        return {
            "status": "error",
            "message": f"Unknown timezone: {timezone_name}",
        }

    now = datetime.now(tz)
    return {
        "status": "ok",
        "timezone": str(tz),
        "current_date": now.date().isoformat(),
        "current_datetime": now.isoformat(timespec="seconds"),
        "weekday": now.strftime("%A"),
    }


def currency_converter(
        amount: float,
        from_currency: str,
        to_currency: str = "USD",
        rate_date: Optional[str] = None,
) -> dict[str, Any]:
    """Converts an amount between ISO 4217 currencies using the Frankfurter API."""
    if amount < 0:
        return {
            "status": "error",
            "message": "Amount must be greater than or equal to 0.",
        }

    source_currency = from_currency.strip().upper()
    target_currency = to_currency.strip().upper()

    if not source_currency or not target_currency:
        return {
            "status": "error",
            "message": "Both from_currency and to_currency are required.",
        }

    if source_currency == target_currency:
        return {
            "status": "ok",
            "amount": amount,
            "from_currency": source_currency,
            "to_currency": target_currency,
            "converted_amount": amount,
            "exchange_rate": 1.0,
            "date": rate_date or datetime.now().date().isoformat(),
            "source": "identity",
        }

    endpoint = f"https://api.frankfurter.dev/v2/rate/{source_currency}/{target_currency}"
    params = {}
    if rate_date:
        params["date"] = rate_date
    url = endpoint if not params else f"{endpoint}?{parse.urlencode(params)}"

    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "travelly/1.0",
            },
            timeout=10,
        )
        payload = response.json()
    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": f"Exchange rate request failed: {exc}",
        }
    except ValueError:
        return {
            "status": "error",
            "message": "Exchange rate API returned invalid JSON.",
        }

    if response.status_code != 200:
        return {
            "status": "error",
            "message": f"Exchange rate request failed with status {response.status_code}.",
            "details": payload,
        }

    exchange_rate = payload.get("rate")
    if exchange_rate is None:
        return {
            "status": "error",
            "message": "Exchange rate API did not return a rate for the requested currency pair.",
            "payload": payload,
        }

    converted_amount = round(amount * exchange_rate, 2)
    return {
        "status": "ok",
        "amount": amount,
        "from_currency": source_currency,
        "to_currency": target_currency,
        "converted_amount": converted_amount,
        "exchange_rate": exchange_rate,
        "date": payload.get("date", rate_date),
        "source": "frankfurter.dev",
    }


def normalize_city_name(city_query: str) -> dict[str, Any]:
    """Normalizes a city query to the English `City, Country` format."""
    normalized_query = city_query.strip()
    if not normalized_query:
        return {
            "status": "error",
            "message": "city_query is required.",
        }

    params = parse.urlencode(
        {
            "q": normalized_query,
            "format": "jsonv2",
            "limit": 5,
            "addressdetails": 1,
            "accept-language": "en",
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = request.Request(
        url,
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            payload = json.load(response)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return {
            "status": "error",
            "message": f"City normalization request failed with status {exc.code}.",
            "details": details or None,
        }
    except error.URLError as exc:
        return {
            "status": "error",
            "message": f"City normalization request failed: {exc.reason}",
        }

    if not payload:
        return {
            "status": "error",
            "message": f"City not found: {city_query}",
        }

    best_match = payload[0]
    address = best_match.get("address", {})
    city_name = (
        address.get("city")
        or address.get("state")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("hamlet")
        or address.get("county")
    )
    country_name = address.get("country")

    if not city_name or not country_name:
        return {
            "status": "error",
            "message": "Geocoder returned an incomplete city match.",
            "payload": best_match,
        }

    return {
        "status": "ok",
        "original_query": city_query,
        "normalized_city": city_name,
        "country": country_name,
        "normalized_location": f"{city_name}, {country_name}",
        "latitude": best_match.get("lat"),
        "longitude": best_match.get("lon"),
        "source": "nominatim.openstreetmap.org",
    }


def save_info_to_state(
        destination: Optional[str] = None,
        origin: Optional[str] = None,
        date_from_start: Optional[str] = None,
        date_from_end: Optional[str] = None,
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
            "trip_duration": None,
            "default_currency": None,
            "hotel_rating": None,
        }

    updated_fields = {}
    normalization_results = {}
    validation_errors = {}

    def maybe_update(field_name: str, value: Optional[str]):
        if value is not None:
            state["trip"][field_name] = value
            updated_fields[field_name] = value

    def validate_iso_date(field_name: str, value: Optional[str]):
        if value is None:
            return

        normalized_value = value.strip()
        try:
            datetime.fromisoformat(normalized_value.replace("Z", "+00:00"))
        except ValueError:
            validation_errors[field_name] = (
                f"`{field_name}` must be in ISO format. Received: {value}"
            )
            return

        maybe_update(field_name, normalized_value)

    def normalize_and_update(field_name: str, value: Optional[str]):
        if value is None:
            return

        normalized_value = value
        normalization_result = normalize_city_name(value)
        if normalization_result.get("status") == "ok":
            normalized_value = normalization_result["normalized_location"]
        normalization_results[field_name] = normalization_result
        maybe_update(field_name, normalized_value)

    normalize_and_update("destination", destination)
    normalize_and_update("origin", origin)
    validate_iso_date("date_from_start", date_from_start)
    validate_iso_date("date_from_end", date_from_end)
    maybe_update("default_currency", default_currency)
    maybe_update("hotel_rating", hotel_rating)
    maybe_update("trip_duration", trip_duration)

    if validation_errors:
        status = "partial_success" if updated_fields else "error"
        message = "Some fields were not saved because date values are not in ISO format."
    else:
        status = "ok"
        message = "Trip state updated."

    return {
        "status": status,
        "message": message,
        "updated_fields": updated_fields,
        "normalization_results": normalization_results,
        "validation_errors": validation_errors,
        "trip": state["trip"],
    }
