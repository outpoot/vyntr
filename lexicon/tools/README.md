# Vyntr Lexicon
This is the code behind "word lookups" in Vyntr, powered by [English WordNet](https://github.com/globalwordnet/english-wordnet)

To generate the needed `wn.json` in `vyntr/lexicon/wn.json`:
1. Go to https://en-word.net/ and click "Download as XML"
2. Move the file to `vyntr/lexicon/tools`
3. (optional) Install `uv` if you haven't already:
    - macOS and Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
4. Run `uv run convert_wn_xml_to_json.py`

And wait a few seconds.