# Use this script to convert the WordNet XML file to a simplified JSON format
# This will generate the needed "wn.json" file for the word meaning lookup endpoint
# Move it to the "lexicon" directory

# uv run convert_wn_xml_to_json.py

import xml.etree.ElementTree as ET
import json
import os
from collections import defaultdict

NAMESPACES = {"dc": "http://purl.org/dc/elements/1.1/"}

POS_MAP = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "r": "adverb",
    "s": "adjective_satellite",
    "c": "conjunction",
    "p": "adposition",
    "x": "other",
    "u": "unknown",
}

def safe_find_all(element, match, namespaces=None):
    if element is None:
        return []
    return element.findall(match, namespaces)

def safe_find(element, match, namespaces=None):
    if element is None:
        return None
    return element.find(match, namespaces)


def safe_get(element, attrib, default=None):
    if element is None:
        return default
    return element.get(attrib, default)

def extract_dc_metadata(element, prefix="dc"):
    metadata = {}
    if element is not None:
        for ns_prefix, ns_uri in NAMESPACES.items():
            if ns_prefix == prefix:
                for key, value in element.attrib.items():
                    if key.startswith(f"{{{ns_uri}}}"):
                        local_name = key.split("}", 1)[1]
                        metadata[local_name] = value
                    elif ":" in key and key.startswith(f"{ns_prefix}:"):
                         local_name = key.split(":", 1)[1]
                         metadata[local_name] = value
    return metadata


def convert_wn_xml_to_lookup_json(xml_file_path, json_file_path):
    if not os.path.exists(xml_file_path):
        print(f"Error: XML file not found at {xml_file_path}")
        return

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return
    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
        return

    synsets_data = {}
    senses_data = {}
    entries_data = {}
    synset_to_lemmas = defaultdict(set)
    all_lexical_entries = [] # Keep order

    for lexicon_elem in root.findall("Lexicon") + root.findall(
        "LexiconExtension"
    ):
        for synset_elem in safe_find_all(lexicon_elem, "Synset"):
            synset_id = synset_elem.get("id")
            if not synset_id: continue

            xml_pos = synset_elem.get("partOfSpeech", "u")
            json_pos = POS_MAP.get(xml_pos, "unknown")
            definitions = []
            relations = []

            for def_elem in safe_find_all(synset_elem, "Definition"):
                gloss = def_elem.text.strip() if def_elem.text else ""
                if gloss:
                    def_obj = {"pos": json_pos, "gloss": gloss}
                    dc_meta = extract_dc_metadata(def_elem)
                    if "source" in dc_meta: def_obj["source"] = dc_meta["source"]
                    definitions.append(def_obj)

            ili_def_elem = safe_find(synset_elem, "ILIDefinition")
            if ili_def_elem is not None and ili_def_elem.text:
                 gloss = ili_def_elem.text.strip()
                 if gloss:
                    ili_def_obj = {"pos": json_pos, "gloss": gloss}
                    dc_meta = extract_dc_metadata(ili_def_elem)
                    if "source" in dc_meta: ili_def_obj["source"] = dc_meta["source"]
                    definitions.append(ili_def_obj)

            for rel_elem in safe_find_all(synset_elem, "SynsetRelation"):
                rel_type = rel_elem.get("relType")
                target = rel_elem.get("target")
                if target and rel_type in ["antonym", "similar"]: # Only keep these
                    relations.append({"type": rel_type, "target": target})

            synsets_data[synset_id] = {
                "definitions": definitions,
                "relations": relations,
                "pos": json_pos,
                "members": synset_elem.get("members", "").split(),
            }

        for entry_elem in safe_find_all(lexicon_elem, "LexicalEntry"):
            entry_id = entry_elem.get("id")
            if not entry_id: continue
            all_lexical_entries.append(entry_elem)

            lemma_elem = safe_find(entry_elem, "Lemma")
            lemma_form = safe_get(lemma_elem, "writtenForm", "N/A")
            xml_pos = safe_get(lemma_elem, "partOfSpeech", "u")
            json_pos = POS_MAP.get(xml_pos, "unknown")
            pronunciations = []
            sense_ids = []

            # Extract Pronunciations
            for pron_elem in safe_find_all(entry_elem, "Pronunciation"):
                pron_text = pron_elem.text.strip() if pron_elem.text else None
                if pron_text: pronunciations.append(pron_text)

            entries_data[entry_id] = {
                "lemma": lemma_form,
                "pos": json_pos,
                "pronunciations": pronunciations,
                "sense_ids": sense_ids,
            }

            for sense_elem in safe_find_all(entry_elem, "Sense"):
                sense_id = sense_elem.get("id")
                synset_ref = sense_elem.get("synset")
                if not sense_id: continue

                sense_ids.append(sense_id)

                examples = []
                relations = []

                for ex_elem in safe_find_all(sense_elem, "SenseExample"):
                    ex_text = ex_elem.text.strip() if ex_elem.text else None
                    if ex_text: examples.append(ex_text)

                for rel_elem in safe_find_all(sense_elem, "SenseRelation"):
                    rel_type = rel_elem.get("relType")
                    target = rel_elem.get("target")
                    if target and rel_type == "antonym":
                        relations.append({"type": rel_type, "target": target})

                senses_data[sense_id] = {
                    "synsetRef": synset_ref,
                    "examples": examples,
                    "relations": relations,
                }

                if synset_ref:
                    synset_to_lemmas[synset_ref].add(lemma_form)

    output_list = []
    processed_definitions = {} 
    processed_examples = {}
    processed_antonyms = set()
    processed_similar = set()

    for entry_elem in all_lexical_entries:
        entry_id = entry_elem.get("id")
        entry_info = entries_data.get(entry_id)
        if not entry_info: continue

        processed_definitions.clear()
        processed_examples.clear()
        processed_antonyms.clear()
        processed_similar.clear()

        word_obj = {
            "word": entry_info["lemma"],
            "id": entry_id,
            "partOfSpeech": entry_info["pos"],
            "pronunciations": entry_info["pronunciations"],
            "definitions": [],
            "examples": [],
            "synonyms": set(),
            "antonyms": set(),
            "similar_words": set(),
        }

        current_word_lemma = entry_info["lemma"]
        related_synset_ids = set()

        for sense_id in entry_info["sense_ids"]:
            sense_info = senses_data.get(sense_id)
            if not sense_info: continue

            synset_id = sense_info.get("synsetRef")

            for ex in sense_info.get("examples", []):
                 if ex not in processed_examples:
                    word_obj["examples"].append(ex)
                    processed_examples[ex] = True

            for rel in sense_info.get("relations", []):
                if rel["target"] not in processed_antonyms:
                    word_obj["antonyms"].add(rel["target"])
                    processed_antonyms.add(rel["target"])

            if synset_id:
                related_synset_ids.add(synset_id)
                synset_info = synsets_data.get(synset_id)
                if not synset_info: continue

                for definition in synset_info.get("definitions", []):
                    def_key = (definition["pos"], definition["gloss"])
                    if def_key not in processed_definitions:
                        word_obj["definitions"].append(definition)
                        processed_definitions[def_key] = True

                for rel in synset_info.get("relations", []):
                    if rel["type"] == "antonym":
                        if rel["target"] not in processed_antonyms:
                            word_obj["antonyms"].add(rel["target"])
                            processed_antonyms.add(rel["target"])
                    elif rel["type"] == "similar":
                         if rel["target"] not in processed_similar:
                            word_obj["similar_words"].add(rel["target"])
                            processed_similar.add(rel["target"])

        for synset_id in related_synset_ids:
            lemmas = synset_to_lemmas.get(synset_id, set())
            for lemma in lemmas:
                if lemma != current_word_lemma:
                    word_obj["synonyms"].add(lemma)

        word_obj["synonyms"] = sorted(list(word_obj["synonyms"]))
        word_obj["antonyms"] = sorted(list(word_obj["antonyms"]))
        word_obj["similar_words"] = sorted(list(word_obj["similar_words"]))

        if not word_obj["pronunciations"]: del word_obj["pronunciations"]
        if not word_obj["definitions"]: del word_obj["definitions"]
        if not word_obj["examples"]: del word_obj["examples"]
        if not word_obj["synonyms"]: del word_obj["synonyms"]
        if not word_obj["antonyms"]: del word_obj["antonyms"]
        if not word_obj["similar_words"]: del word_obj["similar_words"]

        output_list.append(word_obj)

    try:
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(output_list, f, ensure_ascii=False, indent=2)
        print(f"Successfully converted {xml_file_path} to {json_file_path}")
    except IOError as e:
        print(f"Error writing JSON file: {e}")
    except TypeError as e:
        print(f"Error serializing data to JSON: {e}")


if __name__ == "__main__":
    input_xml = "wn.xml"
    output_json = "wn.json"

    if os.path.exists(input_xml):
        convert_wn_xml_to_lookup_json(input_xml, output_json)
    else:
        print(f"Input file '{input_xml}' not found.")
        print("Please place the WordNet XML file named 'wn.xml' in the")
        print("same directory as this script, or update the 'input_xml' variable.")
