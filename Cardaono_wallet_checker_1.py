import os
import requests
import logging
from crewai import Agent, Task, Crew

# 🔹 **Setup Debug Logging**
logging.basicConfig(
    filename="debug_cardano_wallet.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# **Set Blockfrost API Key**
BLOCKFROST_API_KEY = os.getenv("BLOCKFROST_API_KEY")  # Ensure this is set in your environment
API_URL = "https://cardano-mainnet.blockfrost.io/api/v0"


def fetch_utxos(wallet_address):
    """Fetch UTXOs from the Cardano wallet and separate locked vs. spendable ADA."""
    url = f"{API_URL}/addresses/{wallet_address}/utxos"
    headers = {"project_id": BLOCKFROST_API_KEY}

    logging.debug(f"🔹 Sending request to Blockfrost API: {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        utxos = response.json()

        logging.debug(f"✅ Blockfrost API Response (UTXOs): {utxos}")

        spendable_ada = 0
        locked_ada = 0

        # Analyze UTXOs
        for utxo in utxos:
            logging.debug(f"🔸 Processing UTXO: {utxo}")

            for asset in utxo.get("amount", []):
                if asset.get("unit") == "lovelace":
                    ada_amount = int(asset["quantity"]) / 1_000_000  # Convert Lovelace to ADA

                    # Check if UTXO is locked (heuristic: script reference present)
                    if utxo.get("script"):
                        locked_ada += ada_amount
                        logging.debug(f"🔒 Locked ADA Found: {ada_amount} ADA")
                    else:
                        spendable_ada += ada_amount
                        logging.debug(f"✅ Spendable ADA Found: {ada_amount} ADA")

        logging.info(f"🔍 Final ADA Calculation: Spendable ADA = {spendable_ada}, Locked ADA = {locked_ada}")
        return spendable_ada, locked_ada

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"❌ HTTP Error: {http_err}")
        if response.status_code == 403:
            return None, None, "❌ API Key is invalid or unauthorized. Check your Blockfrost API key."
        elif response.status_code == 404:
            return None, None, "❌ Wallet address not found. Ensure the address is correct."
        else:
            return None, None, f"❌ API Request Failed: {http_err}"
    except requests.exceptions.RequestException as err:
        logging.error(f"❌ Network Error: {err}")
        return None, None, f"❌ Network error: {err}"


# **1️⃣ UTXO Processing Agent**
utxo_agent = Agent(
    role="Cardano UTXO Processor",
    goal="Analyze UTXOs to determine locked and spendable ADA.",
    backstory="A blockchain analyst that categorizes UTXOs from the Cardano blockchain.",
    verbose=False,
    allow_delegation=False,
    function=fetch_utxos
)


# **2️⃣ ADA Reporting Agent**
def report_ada_balance(wallet_address):
    """Retrieves and reports the locked and spendable ADA from the UTXO agent."""
    spendable_ada, locked_ada = fetch_utxos(wallet_address)

    if spendable_ada is None:
        return locked_ada  # If error message, return it

    # **Formatted List Display**
    balance_report = f"""
📌 **ADA Balance Breakdown**
--------------------------------
✅ **Spendable ADA:** {spendable_ada:.6f} ADA
🔒 **Locked ADA:** {locked_ada:.6f} ADA
💰 **Total ADA in Wallet:** {(spendable_ada + locked_ada):.6f} ADA
--------------------------------
"""
    logging.info(f"📊 ADA Balance Report Generated: {balance_report}")
    return balance_report.strip()


reporting_agent = Agent(
    role="Cardano Wallet Balance Reporter",
    goal="Summarize the spendable and locked ADA balances in a wallet.",
    backstory="A financial analyst for Cardano blockchain users.",
    verbose=False,
    allow_delegation=False,
    function=report_ada_balance
)


# **CrewAI Task: Get UTXO data and report ADA**
def check_wallet_ada(wallet_address):
    utxo_task = Task(
        description=f"Retrieve and process UTXOs for wallet: {wallet_address}.",
        agent=utxo_agent,
        expected_output="A breakdown of spendable and locked ADA."
    )

    reporting_task = Task(
        description=f"Summarize ADA balance (spendable vs. locked) for {wallet_address}.",
        agent=reporting_agent,
        expected_output="A human-readable summary of the wallet balance."
    )

    # Create Crew and execute tasks
    crew = Crew(agents=[utxo_agent, reporting_agent], tasks=[utxo_task, reporting_task])
    result = crew.kickoff()
    return result


# **Run the Script**
if __name__ == "__main__":
    wallet_address = input("Enter a Cardano public wallet address: ").strip()
    ada_balance_summary = check_wallet_ada(wallet_address)
    print("\n📌 **ADA Balance in Wallet:**\n", ada_balance_summary)

    print("\n✅ **Debug log saved in 'debug_cardano_wallet.log'**")











