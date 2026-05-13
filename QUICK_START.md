# Quick Start — CBO-data_mcp

Get from zero to your first CBO data answer in five steps.

---

## Step 1 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2 — Set your Gemini API key

```bash
cp .env.example .env
# Edit .env and replace "your_key_here" with your actual key
```

Get a free key at <https://aistudio.google.com/app/apikey>.

---

## Step 3 — Fetch CBO data

```bash
python scripts/catalog_data.py
```

This clones the CBO baseline data repo into `data/raw/` and writes
`data/catalog.json`.

---

## Step 4 — Start the CLI

```bash
python main.py
```

---

## Step 5 — Ask a question

```
cbo> How many people are projected to be enrolled in Medicaid in 2029?
```

The agent calls the right data tools automatically and returns a cited answer.

---

## Useful follow-up commands

| Command | What it does |
|---------|-------------|
| `/types` | List available CBO file types |
| `/vintages medicaid` | List vintages for the "medicaid" file type |
| `/export` | Save the last answer to a CSV file in `./exports/` |
| `/help` | Show all commands |
| `/quit` | Exit |
