import openai
import time
from typing import List, Dict
import os
import pygame
import tkinter as tk
from tkinter import ttk, messagebox
import threading

# Replace this with your actual OpenAI API key from https://platform.openai.com/account/api-keys
OPENAI_API_KEY = "You_API_Key_Here"  # REPLACE WITH YOUR REAL KEY

# Initialize OpenAI client
try:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    exit(1)


class PodcastAgent:
    def __init__(self, name: str, role: str, personality: str):
        self.name = name
        self.role = role
        self.personality = personality
        self.memory: List[Dict] = []


class ResearchAgent:
    def get_topic_info(self, topic: str) -> Dict:
        try:
            prompt = f"Provide a concise summary of {topic} with 3 key facts suitable for a podcast discussion."
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return {
                "summary": response.choices[0].message.content,
                "timestamp": time.time()
            }
        except Exception as e:
            print(f"Research error: {e}")
            return {"summary": f"Error researching {topic}", "timestamp": time.time()}


class ConversationManager:
    def __init__(self):
        self.host = PodcastAgent("Alex", "host", "Friendly, curious, keeps conversation flowing")
        self.guest = PodcastAgent("Sam", "expert", "Knowledgeable, confident, occasional humor")
        self.researcher = ResearchAgent()
        self.current_topic = None
        pygame.mixer.init()

    def generate_speech(self, text: str, voice: str) -> str:
        try:
            audio_file = f"output_{int(time.time())}.mp3"
            print(f"TTS Input Text ({len(text)} chars): {text}")
            with openai_client.audio.speech.with_streaming_response.create(
                    model="tts-1",
                    voice=voice,
                    input=text
            ) as response:
                with open(audio_file, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            return audio_file
        except Exception as e:
            print(f"TTS error: {e}")
            return None

    def play_audio(self, audio_file: str):
        if not audio_file:
            return
        try:
            sound = pygame.mixer.Sound(audio_file)
            duration_ms = sound.get_length() * 1000

            channel = sound.play()
            if channel:
                pygame.time.wait(int(duration_ms))
            sound.stop()
            time.sleep(0.01)
            os.remove(audio_file)
        except Exception as e:
            print(f"Audio playback error: {e}")
            try:
                os.remove(audio_file)
            except:
                pass

    def generate_response(self, agent: PodcastAgent, context: str, max_tokens: int) -> str:
        try:
            prompt = f"""
            You are {agent.name}, a podcast {agent.role} with a {agent.personality} personality.
            Given the conversation context: '{context}'
            Respond naturally as your character would in a podcast discussion about {self.current_topic}.
            Summarize your thoughts concisely and engagingly within {max_tokens} tokens,
            suitable for audio. Ensure your response is complete, coherent, and fits the segment's purpose.
            """
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=max_tokens
            )
            full_text = response.choices[0].message.content
            print(f"Generated Text ({len(full_text)} chars, max {max_tokens} tokens): {full_text}")
            return full_text
        except Exception as e:
            print(f"Response generation error: {e}")
            return f"{agent.name} encountered an error while responding"

    def run_episode(self, topic: str, total_tokens: int, duration_minutes: float = 2.0):
        self.current_topic = topic
        end_time = time.time() + (duration_minutes * 60)
        MIN_EXCHANGES = 3

        # Calculate token allocations
        intro_tokens = int(total_tokens * 0.15)
        middle_tokens_total = int(total_tokens * 0.55)
        middle_tokens_per_exchange = middle_tokens_total // (MIN_EXCHANGES * 2)
        end_tokens = int(total_tokens * 0.30)

        # Pre-generate all content
        print("Pre-generating all podcast content...")
        audio_files = []

        # Beginning
        research_data = self.researcher.get_topic_info(topic)
        context = f"Starting discussion with research: {research_data['summary']}"
        host_opening_text = self.generate_response(self.host, f"Starting a new episode about {topic}", intro_tokens)
        host_opening_audio = self.generate_speech(host_opening_text, "alloy")
        audio_files.append((self.host.name, host_opening_text, host_opening_audio))

        # Middle
        exchange_count = 0
        while exchange_count < MIN_EXCHANGES and time.time() < end_time:
            guest_response_text = self.generate_response(self.guest, context, middle_tokens_per_exchange)
            guest_response_audio = self.generate_speech(guest_response_text, "echo")
            audio_files.append((self.guest.name, guest_response_text, guest_response_audio))

            context = f"Guest said: {guest_response_text}"
            host_response_text = self.generate_response(self.host, context, middle_tokens_per_exchange)
            host_response_audio = self.generate_speech(host_response_text, "alloy")
            audio_files.append((self.host.name, host_response_text, host_response_audio))

            context = f"Host said: {host_response_text}"
            exchange_count += 1

        # End
        closing_text = self.generate_response(self.host, f"Wrapping up the episode about {topic}", end_tokens)
        closing_audio = self.generate_speech(closing_text, "alloy")
        audio_files.append((self.host.name, closing_text, closing_audio))

        # Play the episode
        print("Playing podcast episode...")
        for speaker, text, audio_file in audio_files:
            print(f"{speaker}: {text}")
            self.play_audio(audio_file)
            if speaker == self.host.name:
                self.host.memory.append({"text": text, "topic": topic})
            else:
                self.guest.memory.append({"text": text, "topic": topic})

    def __del__(self):
        pygame.mixer.quit()


class PodcastUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Podcast Conversation Bot")
        self.root.geometry("400x300")

        self.topic_label = ttk.Label(self.root, text="Enter Podcast Topic (max 999 characters):")
        self.topic_label.pack(pady=10)

        self.topic_entry = tk.Text(self.root, height=4, width=40)
        self.topic_entry.pack(pady=5)
        self.topic_entry.config(wrap="word")
        self.topic_entry.bind("<KeyRelease>", self.limit_chars)

        self.token_label = ttk.Label(self.root, text="Total Tokens for Podcast (100-5000):")
        self.token_label.pack(pady=10)

        self.token_entry = ttk.Entry(self.root, width=10)
        self.token_entry.pack(pady=5)
        self.token_entry.insert(0, "1000")

        self.start_button = ttk.Button(self.root, text="Start Podcast", command=self.start_podcast)
        self.start_button.pack(pady=20)

        self.conversation_manager = ConversationManager()

        self.root.mainloop()

    def limit_chars(self, event):
        content = self.topic_entry.get("1.0", tk.END)
        if len(content) > 999:
            self.topic_entry.delete("1.0", tk.END)
            self.topic_entry.insert("1.0", content[:999])

    def start_podcast(self):
        topic = self.topic_entry.get("1.0", tk.END).strip()
        if not topic:
            messagebox.showwarning("No Topic", "Please enter a topic before starting the podcast.")
            return

        try:
            total_tokens = int(self.token_entry.get().strip())
            if not (100 <= total_tokens <= 5000):
                raise ValueError("Tokens must be between 100 and 5000.")
        except ValueError as e:
            messagebox.showwarning("Invalid Tokens",
                                   str(e) if str(e) else "Please enter a valid number of tokens (100-5000).")
            return

        self.start_button.config(state="disabled")

        def run_in_thread():
            try:
                print(f"Starting podcast episode with {total_tokens} total tokens...")
                self.conversation_manager.run_episode(topic, total_tokens, duration_minutes=2.0)
                print("Episode complete!")
                # Close the Tkinter window and exit after completion
                self.root.after(0, self.root.destroy)
            except Exception as e:
                print(f"Podcast error: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Podcast failed: {str(e)}"))
                self.root.after(0, self.root.destroy)  # Exit even on error
            # No finally block needed since destroy is handled in both cases

        threading.Thread(target=run_in_thread, daemon=True).start()


def main():
    PodcastUI()


if __name__ == "__main__":
    main()




