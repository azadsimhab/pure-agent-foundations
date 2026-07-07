from typing import Any
import requests
from smolagents.tools import Tool

class LiveCurrencyTrackerTool(Tool):
    name = "get_live_currency_rate"
    description = (
        "Queries live global currency conversion parameters from a keyless, highly resilient "
        "and public exchange rate API. Features multi-provider fallback routing."
    )
    inputs = {
        'base_currency': {
            'type': 'string',
            'description': "The standard 3-letter ISO code to convert from, e.g., 'USD', 'EUR', 'INR'."
        },
        'target_currency': {
            'type': 'string',
            'description': "The target 3-letter ISO code to convert to, e.g., 'INR', 'JPY', 'GBP'."
        }
    }
    output_type = "string"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_initialized = True

    def forward(self, base_currency: str, target_currency: str) -> str:
        base = base_currency.strip().upper()
        target = target_currency.strip().upper()

        if len(base) != 3 or len(target) != 3:
            return "Validation Error: Currency ISO codes must be exactly 3 characters long."

        # Multi-provider list for zero-auth public rates checkpoints
        providers = [
            f"https://open.er-api.com/v6/latest/{base}",
            f"https://api.exchangerate-api.com/v4/latest/{base}"
        ]

        errors = []
        for url in providers:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("result") == "error" or "rates" not in data:
                    continue
                    
                rates = data.get("rates", {})
                if target not in rates:
                    return f"Error: Target currency '{target}' is not supported by the provider exchange registry."

                conversion_rate = rates[target]
                last_update = data.get("time_last_update_utc", data.get("date", "N/A"))

                return (
                    f"### 💱 Real-Time Currency Analytics ({base} to {target})\n"
                    f"* **Spot Conversion Rate:** `1.00 {base} = {conversion_rate:.4f} {target}`\n"
                    f"* **Reciprocal Rate:** `1.00 {target} = {1/conversion_rate:.4f} {base}`\n"
                    f"* **Transaction Spread Estimation (0.2%):** `{(conversion_rate * 0.998):.4f} - {(conversion_rate * 1.002):.4f}`\n"
                    f"* **Registry Source Synchronized:** `{url.split('/')[2]}`\n"
                    f"* **UTC Synchronization Timestamp:** `{last_update}`"
                )
            except Exception as e:
                errors.append(f"{url.split('/')[2]}: {str(e)}")
                continue

        # Hardcoded fallback layer if HF Space network is strictly firewalled from external API registries
        mock_rates = {
            "USD": {"INR": 83.50, "EUR": 0.92, "GBP": 0.79, "JPY": 160.20},
            "EUR": {"USD": 1.08, "INR": 90.76, "GBP": 0.85, "JPY": 174.12},
            "INR": {"USD": 0.012, "EUR": 0.011, "GBP": 0.0095, "JPY": 1.92}
        }

        if base in mock_rates and target in mock_rates[base]:
            fallback_rate = mock_rates[base][target]
            return (
                f"### ⚠️ Live Query Interrupted (Running Static Fallback Engine)\n"
                f"* **Calculated Conversion Rate:** `1.00 {base} = {fallback_rate:.4f} {target}`\n"
                f"* **Reciprocal Rate:** `1.00 {target} = {1/fallback_rate:.4f} {base}`\n"
                f"* **Diagnostic Logs:** {', '.join(errors)}"
            )

        return f"Query Failed: All global currency providers are offline and no fallback index exists for {base} -> {target}."