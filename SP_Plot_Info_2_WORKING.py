import os
import requests
import json
import logging
import re
import openai

# Set up logging
logging.basicConfig(
    filename="place_lookup.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set your API keys from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set the OpenAI API key
openai.api_key = OPENAI_API_KEY


def get_place_details(place_name, location):
    """Search for a place using Google Places Text Search API."""
    endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = f"{place_name}, {location}"
    params = {"query": query, "key": GOOGLE_API_KEY}

    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        result = response.json()
        if result.get("status") == "OK" and result.get("results"):
            place_id = result["results"][0]["place_id"]
            return get_place_info(place_id)
        else:
            logging.warning(f"No results found for {query}. API Response: {result}")
            return None
    else:
        logging.error(f"API request failed with status code {response.status_code}")
        return None


def get_place_info(place_id):
    """Retrieve detailed information about a place using its Place ID."""
    details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        "place_id": place_id,
        "fields": "name,formatted_address,website,opening_hours",
        "key": GOOGLE_API_KEY
    }

    details_response = requests.get(details_endpoint, params=details_params)
    if details_response.status_code == 200:
        place_details = details_response.json()
        if place_details.get("status") == "OK":
            details = place_details.get("result")
            website = details.get("website", "N/A")

            # Construct our place_info dictionary
            place_info = {
                "name": details.get("name", "N/A"),
                "address": details.get("formatted_address", "N/A"),
                "website": website,
                "hours": format_opening_hours(details.get("opening_hours", {}).get("weekday_text", [])),
                "social_media": get_social_media_links(website) if website != "N/A" else "No website available"
            }

            # Generate a 100-word summary and add it to our dictionary
            place_info["summary"] = generate_summary(place_info)

            return place_info
        else:
            logging.warning(f"No detailed info found for Place ID {place_id}. API Response: {place_details}")
            return None
    else:
        logging.error(f"API request failed with status code {details_response.status_code}")
        return None


def format_opening_hours(hours):
    """
    Format opening hours.
    Returns a list of strings (one per day) formatted as "Day: 10:00 AM - 6:00 PM".
    """
    if not hours:
        return ["Not available"]

    formatted_hours = []
    for entry in hours:
        try:
            # Example entry: "Monday: 10:00\u202fAM\u2009\u2013\u20096:00\u202fPM"
            day, time_range = entry.split(": ", 1)
            # Clean up time formatting using regex:
            time_range_clean = re.sub(
                r"(\d{1,2}:\d{2})\s*[^\w\d]*(AM|PM|am|pm)\s*[-–]\s*(\d{1,2}:\d{2})\s*[^\w\d]*(AM|PM|am|pm)",
                r"\1 \2 - \3 \4", time_range)
            formatted_hours.append(f"{day}: {time_range_clean}")
        except Exception as e:
            logging.error(f"Error formatting hours entry '{entry}': {e}")
            formatted_hours.append(entry)
    return formatted_hours


def get_social_media_links(website):
    """
    Extract social media links (Facebook, Instagram, Twitter/X) by searching the raw HTML of the website.
    This method uses regex to find URL patterns directly in the HTML.
    """
    try:
        response = requests.get(website, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            logging.error(f"Failed to retrieve website {website} (status code: {response.status_code})")
            return "Failed to retrieve website"

        html = response.text

        # Use regex to extract URLs for each platform.
        fb_links = re.findall(r'https?://(?:www\.)?facebook\.com/[^\s"\'<>]+', html, re.IGNORECASE)
        insta_links = re.findall(r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+', html, re.IGNORECASE)
        twitter_links = re.findall(r'https?://(?:www\.)?twitter\.com/[^\s"\'<>]+', html, re.IGNORECASE)
        x_links = re.findall(r'https?://(?:www\.)?x\.com/[^\s"\'<>]+', html, re.IGNORECASE)

        social_links = {}
        if fb_links:
            social_links["Facebook"] = fb_links[0]
        if insta_links:
            social_links["Instagram"] = insta_links[0]
        if twitter_links:
            social_links["Twitter/X"] = twitter_links[0]
        elif x_links:
            social_links["Twitter/X"] = x_links[0]

        return social_links if social_links else "No social media links found"
    except Exception as e:
        logging.error(f"Error retrieving social media links from {website}: {e}")
        return f"Error retrieving social media links: {e}"


def generate_summary(place_info):
    """
    Generate a precise 100-word summary for the point of interest using OpenAI's API.
    The summary is based on the place's name, address, website, hours, and social media links.
    """
    if not OPENAI_API_KEY:
        logging.error("OpenAI API key not set.")
        return "Error generating summary: OpenAI API key not set."

    # Format hours in a more readable way
    hours_text = '; '.join(place_info.get('hours', []))

    # Format social media links more cleanly
    social_media = place_info.get('social_media', {})
    if isinstance(social_media, dict):
        social_text = ', '.join([f"{platform}: {url}" for platform, url in social_media.items()])
    else:
        social_text = str(social_media)

    # Create a well-structured prompt
    messages = [
        {"role": "system",
         "content": "You are a helpful assistant who provides concise, informative summaries of places."},
        {"role": "user", "content":
            f"""Create a concise, informative 100-word summary for the following place:

            Name: {place_info.get('name')}
            Address: {place_info.get('address')}
            Website: {place_info.get('website')}
            Hours: {hours_text}
            Social Media: {social_text}

            Focus on the location, main features, operating hours, and online presence. Be specific and factual.
            The summary should be exactly 100 words long."""
         }
    ]

    try:
        # For newer OpenAI client
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )
            summary = response.choices[0].message.content.strip()
        except (AttributeError, ImportError):
            # Fallback for older OpenAI client
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )
            summary = response.choices[0].message.content.strip()

        # Verify summary length and adjust if needed
        words = summary.split()
        if len(words) > 100:
            summary = ' '.join(words[:100]) + '.'
        elif len(words) < 90:
            logging.warning(f"Summary too short ({len(words)} words)")

        logging.debug(f"Generated summary of {len(words)} words")
        return summary

    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return f"Error generating summary: {e}"


def main():
    place_name = input("Enter the name of the place: ")
    location = input("Enter the location (city, state/country): ")

    logging.info("Fetching place details...")
    place_details = get_place_details(place_name, location)

    if place_details:
        print(json.dumps(place_details, indent=4))
    else:
        print("Place not found.")


if __name__ == "__main__":
    main() 


