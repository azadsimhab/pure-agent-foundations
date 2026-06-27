import os
import sys
from smolagents import CodeAgent, LiteLLMModel, tool

# =====================================================================
# 1. UNTYPED LEGACY INFRASTRUCTURE (Mocking a 3rd Party Database Library)
# =====================================================================
def legacy_untyped_query(sql_query):
    query_lower = sql_query.lower()
    if "california" in query_lower:
        return "California Real Estate Data: Average Home Price is $500,000. Property tax rate is 0.0075 (0.75%)."
    elif "new york" in query_lower:
        return "New York Real Estate Data: Average Home Price is $500,000. Property tax rate is 0.0162 (1.62%)."
    else:
        return "Standard Regional Data: Average Home Price is $400,000. Property tax rate is 0.011 (1.10%)."


# =====================================================================
# 2. ADAPTER DESIGN PATTERN & PROGRAMMATIC SANITIZATION (CTO Guardrails)
# =====================================================================
@tool
def secure_database_query(sql_query: str) -> str:
    """
    Executes a read-only SQL query against the real estate database to fetch home values and tax rates.

    Args:
        sql_query: A strict SQL SELECT string (e.g., "SELECT * FROM real_estate WHERE location = 'California'"). Mutative keywords (DROP, DELETE, UPDATE, INSERT) are strictly forbidden.
    """
    destructive_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]
    upper_query = sql_query.upper()

    for keyword in destructive_keywords:
        if keyword in upper_query:
            return f"Security Exception Blocked: Command contains mutative keyword '{keyword}'."

    return legacy_untyped_query(sql_query)


# =====================================================================
# 3. COMPOSABLE DATA CONVERSION & COMPUTATIONAL TOOL
# =====================================================================
@tool
def calculate_mortgage_payment(property_value: float, tax_rate: float, interest_rate: float = 0.045, term_years: int = 30) -> str:
    """
    Calculates the estimated monthly mortgage payment (P&I + monthly property tax allocations).

    Args:
        property_value: The estimated market price of the asset in USD.
        tax_rate: The local property tax rate expressed as a decimal value (e.g., 0.0075 for 0.75%).
        interest_rate: The annual mortgage interest rate. Defaults to 0.045 (4.5%).
        term_years: The duration of the loan in years. Defaults to 30.
    """
    try:
        annual_tax = property_value * tax_rate
        monthly_tax = annual_tax / 12.0

        monthly_interest = interest_rate / 12.0
        total_months = term_years * 12

        if monthly_interest == 0:
            monthly_p_and_i = property_value / total_months
        else:
            monthly_p_and_i = property_value * (
                (monthly_interest * (1 + monthly_interest)**total_months) / 
                ((1 + monthly_interest)**total_months - 1)
            )

        total_monthly = monthly_p_and_i + monthly_tax

        return (
            f"Mortgage Calculation Success:\n"
            f"- Home Value: ${property_value:,.2f}\n"
            f"- Principal & Interest: ${monthly_p_and_i:,.2f}/mo\n"
            f"- Property Tax Escrow: ${monthly_tax:,.2f}/mo\n"
            f"- Combined Est. Monthly: ${total_monthly:,.2f}/mo"
        )
    except Exception as e:
        return f"Computation Error: {str(e)}"


# =====================================================================
# 4. ENGINE INITIALIZATION
# =====================================================================
def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Fatal Environment Error]: GEMINI_API_KEY environment variable is not defined.")
        sys.exit(1)

    model = LiteLLMModel(
        model_id="gemini/gemini-2.5-flash",
        api_key=api_key
    )

    agent = CodeAgent(
        tools=[secure_database_query, calculate_mortgage_payment],
        model=model,
        add_base_tools=False
    )

    user_prompt = (
        "Use secure_database_query to look up California and New York. "
        "Then use calculate_mortgage_payment to find the total monthly costs for a $500,000 home in both states using their parsed tax rates. Compare them."
    )

    agent.run(user_prompt)


if __name__ == "__main__":
    main()