# Vyntr Lexicon
This is the code behind "word lookups" in Vyntr, powered by [English WordNet](https://github.com/globalwordnet/english-wordnet)

To generate the needed `wn.json` in `vyntr/lexicon/wn.json`:
1. Go to https://en-word.net/ and click "Download as XML"
2. Move the file to `vyntr/lexicon/tools`
3. Install [uv](https://github.com/astral-sh/uv)
    - 🐧 Linux / macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - 🪟 Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
    - or, with `pip install uv`
    - or, with `pipx install uv`
4. Run `uv sync`
5. Run `uv run src/convert_wn_xml_to_json.py`

And wait a few seconds.

If you run into missing modules, run `uv add <module>`.