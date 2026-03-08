# API Usage Examples

## Fetching Verses

The `/api/v1/search` endpoint allows you to search for and retrieve specific verses with various translation options.

```bash
curl -s -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=Mc 1:1-2" \
  --data-urlencode "bible=bj" \
  --data-urlencode "tr=fr" \
  --data-urlencode "tr=gr"
```

### Fetching a Verse in Multiple Languages (with Proper Unicode Formatting)

When fetching texts that contain non-ASCII characters (like Ancient Greek), standard JSON formatters might escape the characters (e.g., `\u1f08\u03c1\u03c7`). 

To fetch a verse (e.g., "Mc 1:1-2") in both the French BJ ("Bible de Jérusalem") version and Greek, while keeping the output readable in your terminal, use one of the following methods:

**Method 1: Using Python's `json.tool` (Built-in on most systems)**
Use the `--no-ensure-ascii` flag to prevent Python from escaping the unicode characters:

```bash
curl -s -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=Mc 1:1-2" \
  --data-urlencode "bible=bj" \
  --data-urlencode "tr=fr" \
  --data-urlencode "tr=gr" | python3 -m json.tool --no-ensure-ascii
```

**Method 2: Using `jq` (Requires installation)**
`jq` natively handles unicode out of the box without any escaping:

```bash
curl -s -G "http://localhost:8000/api/v1/search" \
  --data-urlencode "q=Mc 1:1-2" \
  --data-urlencode "bible=bj" \
  --data-urlencode "tr=fr" \
  --data-urlencode "tr=gr" | jq
```

## Exposing the Local API to the Internet (ngrok)

You can expose the local API to the internet for testing or using it with external tools like Google Apps Script using [ngrok](https://ngrok.com/).

Run the following command in a new terminal window while your local API is running:

```bash
ngrok http http://localhost:8000
```

Ngrok will provide a public URL (e.g., `https://<your-id>.ngrok-free.dev`). You can use this URL instead of `http://localhost:8000`.

**Important for Automated Tools:**
If you are using the free tier of ngrok, it intercepts the first request and serves an HTML "Browser Warning" page. If your external script (like Google Apps Script, `curl`, or frontend apps) expects JSON, this will cause JSON parsing errors.

To bypass this warning page in automated requests, add the `ngrok-skip-browser-warning` header to your HTTP requests:

```bash
# Example with curl
curl -s -G "https://<your-id>.ngrok-free.dev/api/v1/search" \
  -H "ngrok-skip-browser-warning: true" \
  --data-urlencode "q=Mc 1:1-2"
```

```javascript
// Example with Google Apps Script
const options = {
  "method": "get",
  "headers": {
    "ngrok-skip-browser-warning": "true"
  },
  "muteHttpExceptions": true
};
const url = "https://<your-id>.ngrok-free.dev/api/v1/search?q=Mc%201%3A1-2";
const response = UrlFetchApp.fetch(url, options);
const data = JSON.parse(response.getContentText());
```
