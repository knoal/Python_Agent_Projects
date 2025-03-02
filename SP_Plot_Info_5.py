import os
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import json
import requests
import logging
import re
import openai
from tkinter import messagebox
from functools import lru_cache
import time

# Set up logging
logging.basicConfig(
    filename="place_lookup.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class PlaceLookupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Points of Interest Lookup")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)

        # Configure grid to make it responsive
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # API keys
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # Initialize API clients
        if self.OPENAI_API_KEY:
            try:
                self.openai_client = openai.OpenAI(api_key=self.OPENAI_API_KEY)
            except (AttributeError, ImportError):
                # Fall back to the older client interface
                openai.api_key = self.OPENAI_API_KEY
                self.openai_client = None
        else:
            self.openai_client = None

        # Session for making HTTP requests
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

        # Cache for recent searches
        self.place_cache = {}

        # Create UI
        self.create_ui()

    def create_ui(self):
        # Input frame
        input_frame = ttk.LabelFrame(self.root, text="Search for a Point of Interest")
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        # Place name
        ttk.Label(input_frame, text="Place Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.place_name_var = tk.StringVar()
        self.place_name_entry = ttk.Entry(input_frame, textvariable=self.place_name_var)
        self.place_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Location
        ttk.Label(input_frame, text="Location:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.location_var = tk.StringVar()
        self.location_entry = ttk.Entry(input_frame, textvariable=self.location_var)
        self.location_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Search button and clear button side by side
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        self.search_button = ttk.Button(button_frame, text="Search", command=self.search_place)
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_fields)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(input_frame, orient="horizontal", length=100,
                                            mode="determinate", variable=self.progress_var)
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Output frame - uses scrolledtext which is expandable/contractable
        output_frame = ttk.LabelFrame(self.root, text="Place Information")
        output_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(0, weight=1)

        # Create a tabbed interface for the output
        self.tab_control = ttk.Notebook(output_frame)
        self.tab_control.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Tab 1: JSON Output
        self.json_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.json_tab, text='JSON Data')
        self.json_tab.grid_columnconfigure(0, weight=1)
        self.json_tab.grid_rowconfigure(0, weight=1)

        self.json_output = scrolledtext.ScrolledText(self.json_tab, wrap=tk.WORD)
        self.json_output.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Tab 2: Formatted Output
        self.formatted_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.formatted_tab, text='Formatted View')
        self.formatted_tab.grid_columnconfigure(0, weight=1)
        self.formatted_tab.grid_rowconfigure(0, weight=1)

        self.formatted_output = scrolledtext.ScrolledText(self.formatted_tab, wrap=tk.WORD)
        self.formatted_output.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="ew")

        # Initialize progress bar to 0
        self.progress_var.set(0)

        # Bind Enter key to search
        self.place_name_entry.bind("<Return>", lambda event: self.search_place())
        self.location_entry.bind("<Return>", lambda event: self.search_place())

    def clear_fields(self):
        """Clear input fields and output areas"""
        self.place_name_var.set("")
        self.location_var.set("")
        self.json_output.delete(1.0, tk.END)
        self.formatted_output.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.status_var.set("Ready")

    def search_place(self):
        # Clear previous outputs
        self.json_output.delete(1.0, tk.END)
        self.formatted_output.delete(1.0, tk.END)

        place_name = self.place_name_var.get().strip()
        location = self.location_var.get().strip()

        if not place_name or not location:
            messagebox.showerror("Input Error", "Please enter both place name and location.")
            return

        # Check cache first
        cache_key = f"{place_name}|{location}"
        if cache_key in self.place_cache:
            self.status_var.set("Loading from cache...")
            self.progress_var.set(50)
            self.root.update_idletasks()

            # Short delay to show loading from cache
            time.sleep(0.5)

            # Update UI with cached results
            self.update_ui_with_results(self.place_cache[cache_key])
            return

        # Disable search button and update status
        self.search_button.config(state=tk.DISABLED)
        self.status_var.set("Searching...")
        self.progress_var.set(0)
        self.root.update_idletasks()

        # Run the search in a separate thread to prevent UI freeze
        thread = threading.Thread(target=self.perform_search, args=(place_name, location))
        thread.daemon = True
        thread.start()

    def perform_search(self, place_name, location):
        try:
            self.status_var.set(f"Looking up information for {place_name} in {location}...")
            self.update_progress(10)

            place_details = self.get_place_details(place_name, location)

            if place_details:
                # Cache the results
                cache_key = f"{place_name}|{location}"
                self.place_cache[cache_key] = place_details

                # Update the UI with the results
                self.root.after(0, self.update_ui_with_results, place_details)
            else:
                self.update_progress(100)
                self.root.after(0, lambda: self.status_var.set("Place not found."))
                self.root.after(0, lambda: messagebox.showinfo("No Results", "No information found for this place."))
        except Exception as e:
            self.update_progress(100)
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))

        # Re-enable the search button
        self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL))

    def update_progress(self, value):
        """Update progress bar value"""
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.update_idletasks()

    def update_ui_with_results(self, place_details):
        # Update JSON tab
        json_str = json.dumps(place_details, indent=4)
        self.json_output.insert(tk.END, json_str)

        # Update Formatted tab (now includes summary)
        formatted_text = self.format_place_details(place_details)
        self.formatted_output.insert(tk.END, formatted_text)

        # Update status and progress
        self.status_var.set(f"Found information for {place_details.get('name', 'Unknown Place')}")
        self.progress_var.set(100)

        # Switch to formatted tab
        self.tab_control.select(1)  # Index 1 is the formatted tab

    def format_place_details(self, place_details):
        """Format place details for human-readable display"""
        formatted = f"Name: {place_details.get('name', 'N/A')}\n\n"

        if 'type' in place_details:
            formatted += f"Type: {place_details.get('type', 'N/A')}\n\n"

        formatted += f"Address: {place_details.get('address', 'N/A')}\n\n"
        formatted += f"Website: {place_details.get('website', 'N/A')}\n\n"

        # Format hours
        hours = place_details.get('hours', [])
        if hours:
            formatted += "Hours:\n"
            for hour in hours:
                formatted += f"  {hour}\n"
            formatted += "\n"
        else:
            formatted += "Hours: Not available\n\n"

        # Format social media
        social_media = place_details.get('social_media', {})
        if isinstance(social_media, dict) and social_media:
            formatted += "Social Media:\n"
            for platform, url in social_media.items():
                formatted += f"  {platform}: {url}\n"
            formatted += "\n"
        else:
            formatted += f"Social Media: {social_media}\n\n"

        # Add summary section
        summary = place_details.get("summary", "No summary available")
        formatted += "=" * 50 + "\n\n"
        formatted += "SUMMARY:\n\n"
        formatted += summary + "\n\n"
        formatted += "=" * 50 + "\n"

        return formatted

    @lru_cache(maxsize=32)
    def get_place_details(self, place_name, location):
        """Search for a place using Google Places Text Search API with caching."""
        endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        query = f"{place_name}, {location}"
        params = {"query": query, "key": self.GOOGLE_API_KEY}

        self.status_var.set(f"Searching for {place_name} in {location}...")
        self.update_progress(20)

        response = self.session.get(endpoint, params=params)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "OK" and result.get("results"):
                place_id = result["results"][0]["place_id"]
                self.update_progress(30)
                return self.get_place_info(place_id)
            else:
                logging.warning(f"No results found for {query}. API Response: {result}")
                return None
        else:
            logging.error(f"API request failed with status code {response.status_code}")
            return None

    def get_place_info(self, place_id):
        """Retrieve detailed information about a place using its Place ID."""
        details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,website,opening_hours,photos,types",
            "key": self.GOOGLE_API_KEY
        }

        self.status_var.set("Retrieving place details...")
        self.update_progress(40)

        details_response = self.session.get(details_endpoint, params=details_params)
        if details_response.status_code == 200:
            place_details = details_response.json()
            if place_details.get("status") == "OK":
                details = place_details.get("result")
                website = details.get("website", "N/A")

                # Get place type
                place_types = details.get("types", [])
                place_type = place_types[0].replace('_', ' ').title() if place_types else "N/A"

                self.update_progress(50)

                # Construct our place_info dictionary
                place_info = {
                    "name": details.get("name", "N/A"),
                    "type": place_type,
                    "address": details.get("formatted_address", "N/A"),
                    "website": website,
                    "hours": self.format_opening_hours(details.get("opening_hours", {}).get("weekday_text", [])),
                }

                # Get social media links only if website is available
                if website != "N/A":
                    place_info["social_media"] = self.get_social_media_links(website)
                else:
                    place_info["social_media"] = "No website available"

                self.update_progress(80)

                # Generate a 100-word summary and add it to our dictionary
                place_info["summary"] = self.generate_summary(place_info)

                self.update_progress(95)

                return place_info
            else:
                logging.warning(f"No detailed info found for Place ID {place_id}. API Response: {place_details}")
                return None
        else:
            logging.error(f"API request failed with status code {details_response.status_code}")
            return None

    def format_opening_hours(self, hours):
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

    def get_social_media_links(self, website):
        """
        Extract social media links (Facebook, Instagram, Twitter/X) by searching the raw HTML of the website.
        This method uses regex to find URL patterns directly in the HTML.
        """
        try:
            self.status_var.set(f"Retrieving website content from {website}...")
            self.update_progress(60)

            # Use a timeout to avoid hanging on slow websites
            response = self.session.get(website, timeout=8)
            if response.status_code != 200:
                logging.error(f"Failed to retrieve website {website} (status code: {response.status_code})")
                return "Failed to retrieve website"

            html = response.text

            self.update_progress(70)

            # Precompile regex patterns for better performance
            fb_pattern = re.compile(r'https?://(?:www\.)?facebook\.com/[^\s"\'<>]+', re.IGNORECASE)
            insta_pattern = re.compile(r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+', re.IGNORECASE)
            twitter_pattern = re.compile(r'https?://(?:www\.)?twitter\.com/[^\s"\'<>]+', re.IGNORECASE)
            x_pattern = re.compile(r'https?://(?:www\.)?x\.com/[^\s"\'<>]+', re.IGNORECASE)

            # Find all matches
            fb_links = fb_pattern.findall(html)
            insta_links = insta_pattern.findall(html)
            twitter_links = twitter_pattern.findall(html)
            x_links = x_pattern.findall(html)

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
        except requests.Timeout:
            logging.error(f"Timeout retrieving website {website}")
            return "Timeout retrieving website content"
        except Exception as e:
            logging.error(f"Error retrieving social media links from {website}: {e}")
            return f"Error retrieving social media links: {e}"

    def generate_summary(self, place_info):
        """
        Generate a precise 100-word summary for the point of interest using OpenAI's API.
        The summary is based on the place's name, address, website, hours, and social media links.
        """
        if not self.OPENAI_API_KEY:
            logging.error("OpenAI API key not set.")
            return "Error generating summary: OpenAI API key not set."

        self.status_var.set("Generating summary...")
        self.update_progress(85)

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
                Type: {place_info.get('type', 'N/A')}
                Address: {place_info.get('address')}
                Website: {place_info.get('website')}
                Hours: {hours_text}
                Social Media: {social_text}

                Focus main features of the point of interest. Be specific and factual.  Address and hours data are not needed in suaamy as they are already collected.
                The summary should be about 100 words long."""
             }
        ]

        try:
            self.update_progress(90)
            # Use pre-initialized client if available
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=200,
                    temperature=0.7,
                )
                summary = response.choices[0].message.content.strip()
            else:
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
    root = tk.Tk()
    app = PlaceLookupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


