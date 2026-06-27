import os
import sys
from smolagents import CodeAgent, LiteLLMModel, tool

# Verify that the API Key is active in the environment
if not os.environ.get("GEMINI_API_KEY"):
    print("[Error] GEMINI_API_KEY environment variable is not set.")
    print("Please run: $env:GEMINI_API_KEY='your_api_key' in PowerShell before running.")
    sys.exit(1)

# 1. First Tool: Property Tax Rate Lookup (Reflection-driven)
@tool
def get_property_tax(location: str) -> str:
    """
    Calculates property tax rates for a given location.

    Args:
        location: The name of the city or state.
    """
    loc = location.lower()
    if "new york" in loc:
        return "Property tax rate is 1.62%"
    elif "california" in loc:
        return "Property tax rate is 0.75%"
    else:
        return "Standard regional property tax rate is 1.1%"

# 2. Second Tool: Demonstrating Composability (Math and logical execution)
@tool
def calculate_monthly_cost(property_value: float, tax_rate_string: str) -> float:
    """
    Calculates the combined monthly mortgage principal and property tax payment.
    Assumes a fixed annual interest rate of 4.5% over a 30-year term.

    Args:
        property_value: The market purchase price of the property.
        tax_rate_string: The raw tax rate string returned from get_property_tax (e.g., "Property tax rate is 1.62%").
    """
    try:
        # Extract the numeric float from the string output (e.g., "1.62%" -> 0.0162)
        percentage_str = tax_rate_string.split("is")[-1].replace("%", "").strip()
        tax_rate = float(percentage_str) / 100.0
    except Exception as e:
        # Fallback if parsing fails
        tax_rate = 0.011
        
    # Calculate annual property tax
    annual_tax = property_value * tax_rate
    monthly_tax = annual_tax / 12.0
    
    # Simple mortgage math: 4.5% annual interest fixed for 30 years
    r = 0.045 / 12.0
    n = 30 * 12
    monthly_principal_interest = property_value * (r * (1 + r)**n) / ((1 + r)**n - 1)
    
    return round(monthly_principal_interest + monthly_tax, 2)

# 3. Initialize the Model Engine
# Using LiteLLMModel to map seamlessly to Gemini using your active environment variable
model = LiteLLMModel(
    model_id="gemini/gemini-2.5-flash",
    api_key=os.environ.get("GEMINI_API_KEY")
)

# 4. Initialize the CodeAgent with multiple tools
agent = CodeAgent(
    tools=[get_property_tax, calculate_monthly_cost],
    model=model,
    add_base_tools=False
)

# 5. Execute a composable multi-step problem
if __name__ == "__main__":
    task = (
        "Compare the total monthly carrying cost for a $500,000 property "
        "between California and New York. Fetch the tax rates first, "
        "and then compute the final monthly payment for both states."
    )
    agent.run(task)