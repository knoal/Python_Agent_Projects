import sys
import crewai
from crewai import OpenAICompletion  # This is an example; adjust if needed


def summarize_text_with_crewai(text, min_sentences=3, max_sentences=7):
    """
    Creates a CrewAI agent with required fields and uses it to summarize the provided text.
    This version uses an LLM instance and then calls the agent as a callable.
    """
    # Create an LLM instance (adjust parameters if needed)
    llm = OpenAICompletion(api_key="YOUR_API_KEY", model="gpt-3.5-turbo")

    # Create an agent with the required fields and provide the LLM instance.
    agent = crewai.Agent(
        api_key="YOUR_API_KEY",  # Replace with your actual API key
        role="summarizer",
        goal="Summarize the provided text into a concise summary of 3 to 7 sentences.",
        backstory="I am an AI summarization agent built to condense long texts into a short, informative summary.",
        llm=llm
    )

    # Use the agent as a callable. (Adjust the parameters according to CrewAI's API.)
    response = agent("summarize", text=text, min_sentences=min_sentences, max_sentences=max_sentences)

    # Expect the response to be a dictionary with a "summary" key.
    summary = response.get("summary")
    if not summary:
        raise ValueError("No summary was returned from CrewAI.")
    return summary


def main():
    print("Please enter your text (up to 99,999 characters).")
    print("When finished, press Enter on an empty line:")

    # Read multi-line input until an empty line is entered.
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    text = "\n".join(lines)

    # Truncate if text exceeds 99,999 characters.
    if len(text) > 99999:
        text = text[:99999]

    try:
        summary = summarize_text_with_crewai(text, min_sentences=3, max_sentences=7)
    except Exception as e:
        print("An error occurred while summarizing the text:", e)
        return

    print("\nSummary:")
    print(summary)


if __name__ == "__main__":
    main()









