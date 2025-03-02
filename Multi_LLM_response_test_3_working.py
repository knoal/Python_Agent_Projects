import os
import argparse
import json
import requests
from typing import Any, Dict, List, Optional, Union
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up debugging
DEBUG = True


def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")


# Get API keys from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Google AI API key for Gemini

debug_print(f"Anthropic API key set: {bool(ANTHROPIC_API_KEY)}")
debug_print(f"OpenAI API key set: {bool(OPENAI_API_KEY)}")
debug_print(f"Grok API key set: {bool(GROK_API_KEY)}")
debug_print(f"Google API key set: {bool(GOOGLE_API_KEY)}")


# Define custom tool classes with proper type annotations
class ClaudeTool(BaseTool):
    name: str = "AskClaude"
    description: str = "Query Anthropic's Claude API to get a response to the prompt"

    def _run(self, prompt: str) -> str:
        """Tool to query Anthropic's Claude API using requests"""
        try:
            debug_print(f"Sending request to Claude API with prompt: {prompt[:50]}...")

            headers = {
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            data = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 1000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            debug_print("Making request to Anthropic API...")
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            )

            debug_print(f"Claude API response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                debug_print(f"Claude API response: {str(result)[:200]}...")
                return "ANTHROPIC CLAUDE:\n\n" + result["content"][0]["text"]
            else:
                error_msg = f"Error from Claude API: Status {response.status_code}, {response.text}"
                debug_print(error_msg)
                return "ANTHROPIC CLAUDE:\n\n" + error_msg
        except Exception as e:
            error_msg = f"Error with Claude API: {str(e)}"
            debug_print(error_msg)
            return "ANTHROPIC CLAUDE:\n\n" + error_msg


class GPTTool(BaseTool):
    name: str = "AskGPT"
    description: str = "Query OpenAI's GPT API to get a response to the prompt"

    def _run(self, prompt: str) -> str:
        """Tool to query OpenAI's GPT API using requests"""
        try:
            debug_print(f"Sending request to OpenAI API with prompt: {prompt[:50]}...")

            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000
            }

            debug_print("Making request to OpenAI API...")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )

            debug_print(f"OpenAI API response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                debug_print(f"OpenAI API response: {str(result)[:200]}...")
                return "OPENAI GPT:\n\n" + result["choices"][0]["message"]["content"]
            else:
                error_msg = f"Error from OpenAI API: Status {response.status_code}, {response.text}"
                debug_print(error_msg)
                return "OPENAI GPT:\n\n" + error_msg
        except Exception as e:
            error_msg = f"Error with OpenAI API: {str(e)}"
            debug_print(error_msg)
            return "OPENAI GPT:\n\n" + error_msg


class GrokTool(BaseTool):
    name: str = "AskGrok"
    description: str = "Query Grok's API to get a response to the prompt"

    def _run(self, prompt: str) -> str:
        """Tool to query Grok's API using requests"""
        try:
            debug_print(f"Sending request to Grok API with prompt: {prompt[:50]}...")

            # Note: For Grok, we're still using Groq's API endpoint as a substitute
            # Since direct Grok API access is limited
            headers = {
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "mixtral-8x7b-32768",  # Using an appropriate model
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000
            }

            debug_print("Making request to Grok API...")
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                # This might need to be updated to Grok's actual endpoint
                headers=headers,
                json=data
            )

            debug_print(f"Grok API response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                debug_print(f"Grok API response: {str(result)[:200]}...")
                return "GROK:\n\n" + result["choices"][0]["message"]["content"]
            else:
                error_msg = f"Error from Grok API: Status {response.status_code}, {response.text}"
                debug_print(error_msg)
                return "GROK:\n\n" + error_msg
        except Exception as e:
            error_msg = f"Error with Grok API: {str(e)}"
            debug_print(error_msg)
            return "GROK:\n\n" + error_msg


class GeminiTool(BaseTool):
    name: str = "AskGemini"
    description: str = "Query Google's Gemini API to get a response to the prompt"

    def _run(self, prompt: str) -> str:
        """Tool to query Google's Gemini API using requests"""
        try:
            debug_print(f"Sending request to Gemini API with prompt: {prompt[:50]}...")

            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"

            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1000,
                    "topP": 0.8,
                    "topK": 40
                }
            }

            debug_print("Making request to Google Gemini API...")
            response = requests.post(
                api_url,
                headers=headers,
                json=data
            )

            debug_print(f"Gemini API response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                debug_print(f"Gemini API response: {str(result)[:200]}...")

                # Extract the text from Gemini's response format
                try:
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    return "GOOGLE GEMINI:\n\n" + text
                except (KeyError, IndexError) as e:
                    return f"GOOGLE GEMINI:\n\nError parsing Gemini response: {str(e)}\nRaw response: {str(result)[:500]}"
            else:
                error_msg = f"Error from Gemini API: Status {response.status_code}, {response.text}"
                debug_print(error_msg)
                return "GOOGLE GEMINI:\n\n" + error_msg
        except Exception as e:
            error_msg = f"Error with Gemini API: {str(e)}"
            debug_print(error_msg)
            return "GOOGLE GEMINI:\n\n" + error_msg


# Create direct functions to test the APIs outside of CrewAI
def test_claude_api(prompt):
    tool = ClaudeTool()
    return tool._run(prompt)


def test_openai_api(prompt):
    tool = GPTTool()
    return tool._run(prompt)


def test_grok_api(prompt):
    tool = GrokTool()
    return tool._run(prompt)


def test_gemini_api(prompt):
    tool = GeminiTool()
    return tool._run(prompt)


# Create instances of the tools
claude_tool = ClaudeTool()
gpt_tool = GPTTool()
grok_tool = GrokTool()
gemini_tool = GeminiTool()


def main():
    parser = argparse.ArgumentParser(description="Get responses from multiple LLM agents")
    parser.add_argument("prompt", nargs="?", help="The prompt to send to the LLMs")
    parser.add_argument("--test", action="store_true", help="Test APIs directly without CrewAI")
    args = parser.parse_args()

    # Get prompt from command line or user input
    user_prompt = args.prompt
    if not user_prompt:
        user_prompt = input("Enter your prompt: ")

    print(f"\nSending prompt to all LLMs: \"{user_prompt}\"\n")

    # Test APIs directly if --test flag is used
    if args.test:
        print("Testing APIs directly...\n")

        print("\n=== ANTHROPIC CLAUDE ===\n")
        claude_response = test_claude_api(user_prompt)
        print(claude_response)

        print("\n=== OPENAI GPT ===\n")
        gpt_response = test_openai_api(user_prompt)
        print(gpt_response)

        print("\n=== GROK ===\n")
        grok_response = test_grok_api(user_prompt)
        print(grok_response)

        print("\n=== GOOGLE GEMINI ===\n")
        gemini_response = test_gemini_api(user_prompt)
        print(gemini_response)

        return

    print("Generating responses using CrewAI...\n")

    try:
        # Create the agents with tools
        claude_agent = Agent(
            role="Claude Language Model",
            goal="Provide the best possible response to the user's prompt",
            backstory="You are Claude, an AI assistant created by Anthropic, known for thoughtful and nuanced responses.",
            tools=[claude_tool],
            verbose=True
        )

        gpt_agent = Agent(
            role="GPT Language Model",
            goal="Provide the best possible response to the user's prompt",
            backstory="You are GPT, an AI assistant created by OpenAI, known for versatile and creative responses.",
            tools=[gpt_tool],
            verbose=True
        )

        grok_agent = Agent(
            role="Grok Language Model",
            goal="Provide the best possible response to the user's prompt",
            backstory="You are Grok, an AI assistant created by xAI, providing efficient and knowledgeable responses.",
            tools=[grok_tool],
            verbose=True
        )

        gemini_agent = Agent(
            role="Gemini Language Model",
            goal="Provide the best possible response to the user's prompt",
            backstory="You are Gemini, an AI assistant created by Google, known for helpful and accurate responses.",
            tools=[gemini_tool],
            verbose=True
        )

        # Create tasks with expected_output field
        claude_task = Task(
            description=f"Use the AskClaude tool to respond to this prompt: {user_prompt}",
            agent=claude_agent,
            expected_output="A comprehensive response from Anthropic's Claude",
            async_execution=False
        )

        gpt_task = Task(
            description=f"Use the AskGPT tool to respond to this prompt: {user_prompt}",
            agent=gpt_agent,
            expected_output="A comprehensive response from OpenAI's GPT",
            async_execution=False
        )

        grok_task = Task(
            description=f"Use the AskGrok tool to respond to this prompt: {user_prompt}",
            agent=grok_agent,
            expected_output="A comprehensive response from Grok",
            async_execution=False
        )

        gemini_task = Task(
            description=f"Use the AskGemini tool to respond to this prompt: {user_prompt}",
            agent=gemini_agent,
            expected_output="A comprehensive response from Google's Gemini",
            async_execution=False
        )

        # Create and run the crew
        crew = Crew(
            agents=[claude_agent, gpt_agent, grok_agent, gemini_agent],
            tasks=[claude_task, gpt_task, grok_task, gemini_task],
            verbose=True,
            process=Process.sequential  # Run tasks one after another
        )

        # Run the crew
        result = crew.kickoff()

        # Process and display the results without the combined summary
        print("\n" + "=" * 50 + "\n")
        print("INDIVIDUAL RESPONSES FROM EACH LLM:")
        print("\n" + "=" * 50 + "\n")

        # Use simple printing of model outputs without the summary
        for task in [claude_task, gpt_task, grok_task, gemini_task]:
            task_output = task.output if hasattr(task, 'output') and task.output else "No response received"
            print(task_output)
            print("\n" + "=" * 50 + "\n")

        return result

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


if __name__ == "__main__":
    main()
 

