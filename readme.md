# Facebook/Meta Ads MCP Server

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/gomarble-ai/facebook-ads-mcp-server)](https://archestra.ai/mcp-catalog/gomarble-ai__facebook-ads-mcp-server)
[![smithery badge](https://smithery.ai/badge/@gomarble-ai/facebook-ads-mcp-server)](https://smithery.ai/server/@gomarble-ai/facebook-ads-mcp-server)

This project provides an MCP server acting as an interface to the Meta Ads, enabling programmatic access to Meta Ads data and management features.

<video controls width="1920" height="512" src="https://github.com/user-attachments/assets/c4a76dcf-cf5d-4a1d-b976-08165e880fe4">Your browser does not support the video tag.</video>

## Read-only hardening in this fork

This fork keeps the tools read-only. Account listing exhausts its nested account
pages and returns local `_collection` coverage metadata. `max_pages=100` is an
explicit engineering bound; a remaining page, cycle, malformed page or conflicting
account ID raises instead of returning a partial inventory as complete. Other
individual collection tools still return one page and require their own complete
collector loop.

All GETs validate HTTPS `graph.facebook.com`, disable redirects, use a 30-second
request timeout, and omit raw URLs, tokens and response bodies from exceptions.
`FB_ACCESS_TOKEN` from the process environment is preferred; legacy `--fb-token`
remains supported. Packaged launch examples pass the token through the environment,
not argv. Keep real credentials out of repository files.

Run the synthetic regressions without installing MCP or requests:

```sh
python -m unittest -v test_readonly_hardening
```

These tests use fake transport/MCP modules and synthetic values. They do not prove
live API compatibility, campaign performance, first-ever payer attribution or ROAS.
No marketing thresholds or spending authority are introduced.

## Easy One-Click Setup

For a simpler setup experience, we offer ready-to-use installers:

👉 **Download installer -** [https://gomarble.ai/mcp](https://gomarble.ai/mcp)

## Join our community for help and updates

👉 **Slack Community -** [AI in Ads](https://join.slack.com/t/ai-in-ads/shared_invite/zt-36hntbyf8-FSFixmwLb9mtEzVZhsToJQ)

## Try Google ads mcp server also

👉 **Google Ads MCP -** [Google Ads MCP](https://github.com/gomarble-ai/google-ads-mcp-server)

### What It Does

- Installs and configures the MCP server locally
- Automatically handles environment setup
- Prompts for Meta token authentication during the process which is optional
- If Meta access token is not provided then connect to GoMarble's server to create the token on your behalf

### Important Disclaimer

This setup **does not require** you to manually obtain a Meta Developer Access Token.

Instead, it connects securely to **GoMarble's server to create the token on your behalf**.
GoMarble **does not store** your token — it is saved locally on your machine for use with the MCP server.

---

## Setup

### Prerequisites

*   Python 3.10+
*   Dependencies listed in `requirements.txt`



1.  **(Optional but Recommended) Create and Activate a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

    Using a virtual environment helps manage project dependencies cleanly[[Source]](https://docs.python.org/3/tutorial/venv.html).
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Obtain Meta Access Token:** Secure a Meta User Access Token with the necessary permissions (e.g., `ads_read`). You can generate this through the Meta Developer portal. Follow [this link](https://elfsight.com/blog/how-to-get-facebook-access-token/).

### Usage with MCP Clients (e.g., Cursor, Claude Desktop)

To integrate this server with an MCP-compatible client, add a configuration([Claude](https://modelcontextprotocol.io/quickstart/user#2-add-the-filesystem-mcp-server)) similar to the following. Arrange for the server process to inherit `FB_ACCESS_TOKEN` from your approved local secret mechanism and adjust the path to `server.py`. Do not commit the token or put it in process arguments.

```json
{
  "mcpServers": {
    "fb-ads-mcp-server": {
      "command": "python",
      "args": ["/path/to/your/fb-ads-mcp-server/server.py"]
    }
  }
}
```
Restart the MCP Client app after making the update in the configuration.

*(Note: On Windows, you might need to adjust the command structure or use `cmd /k` depending on your setup.)*

### Debugging the Server

Execute `server.py` with `FB_ACCESS_TOKEN` already supplied through the process environment.

```bash
python server.py
```

### Available MCP Tools

This MCP server provides tools for interacting with META Ads objects and data:

| Tool Name                       | Description                                              |
| ------------------------------- | -------------------------------------------------------- |
| **Account & Object Read**       |                                                          |
| `list_ad_accounts`              | Lists ad accounts linked to the token.                   |
| `get_details_of_ad_account`     | Retrieves details for a specific ad account.             |
| `get_campaign_by_id`            | Retrieves details for a specific campaign.               |
| `get_adset_by_id`               | Retrieves details for a specific ad set.                 |
| `get_ad_by_id`                  | Retrieves details for a specific ad.                     |
| `get_ad_creative_by_id`         | Retrieves details for a specific ad creative.            |
| `get_adsets_by_ids`             | Retrieves details for multiple ad sets by their IDs.     |
| **Fetching Collections**        |                                                          |
| `get_campaigns_by_adaccount`    | Retrieves campaigns within an ad account.                |
| `get_adsets_by_adaccount`       | Retrieves ad sets within an ad account.                  |
| `get_ads_by_adaccount`          | Retrieves ads within an ad account.                      |
| `get_adsets_by_campaign`        | Retrieves ad sets within a campaign.                     |
| `get_ads_by_campaign`           | Retrieves ads within a campaign.                         |
| `get_ads_by_adset`              | Retrieves ads within an ad set.                          |
| `get_ad_creatives_by_ad_id`     | Retrieves creatives associated with an ad.               |
| **Insights & Performance Data** |                                                          |
| `get_adaccount_insights`        | Retrieves performance insights for an ad account.        |
| `get_campaign_insights`         | Retrieves performance insights for a campaign.           |
| `get_adset_insights`            | Retrieves performance insights for an ad set.            |
| `get_ad_insights`               | Retrieves performance insights for an ad.                |
| `fetch_pagination_url`          | Fetches data from a pagination URL (e.g., from insights).|
| **Activity/Change History**     |                                                          |
| `get_activities_by_adaccount`   | Retrieves change history for an ad account.              |
| `get_activities_by_adset`       | Retrieves change history for an ad set.                  |

*(Note: Most tools support additional parameters like `fields`, `filtering`, `limit`, pagination, date ranges, etc. Refer to the detailed docstrings within `server.py` for the full list and description of arguments for each tool.)*

*(Note: If your Meta access token expires, you'll need to generate a new one and update the configuration file of the MCP Client with new token to continue using the tools.)*

### Dependencies

*   [mcp](https://pypi.org/project/mcp/) (>=1.6.0)
*   [requests](https://pypi.org/project/requests/) (>=2.32.3)

### License
This project is licensed under the MIT License.

---

## Installing via Smithery

To install Facebook Ads Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@gomarble-ai/facebook-ads-mcp-server):

```bash
npx -y @smithery/cli install @gomarble-ai/facebook-ads-mcp-server --client claude
```
