# Dataset Tools

This folder contains tools for dataset file management and cleaning.

> [!WARNING]
> Scripts in this folder do not interfere directly with the given dataset. However, it's recommended you have enough disk space before continuing. A 100GB folder, when duplicated, takes 200GB total.

## Overview

### `content_cleaner.js`
Cleans JSON files by removing HTML tags, normalizing whitespace, and removing obscure characters (`�`).
```bash
node content_cleaner.js <input-directory>
```
Creates `analyses_cleaned` folder with processed files.

### `find_largest.js`
Identifies the top 1000 largest dataset entries for review.
```bash
node find_largest.js <input-directory>
```
Outputs `largest_content.jsonl` with entry details.

### `remove_largest.js`
Removes entries identified by `find_largest.js`.
```bash
node remove_largest.js <input-directory>
```
Requires `largest_content.jsonl` to operate.

**Note:** Default input directory is `analyses` if unspecified.

## Quick Start
1. Clean data: `node content_cleaner.js analyses`
2. Identify large entries: `node find_largest.js analyses`
3. Remove flagged entries: `node remove_largest.js analyses`

## Technical Details
- All tools process `.jsonl` files (JSON Lines format)
- Expects directory structure: `<input-directory>/partition=*/*.jsonl`
- Example paths:
    ```
    analyses/partition=00/batch_1fbd814b-310c-4c13-8876-0e869989a80a.jsonl
    analyses/partition=1e/batch_2bea673b-b09a-4691-b5c1-f37571355057.jsonl
    ```

## Additional Optimization
The dataset underwent further optimization by removing the 200 most frequent words, which included common JavaScript terms (undefined, true, false, script). This process achieved a 5% size reduction (script not included).

> [!TIP]
> We recommend additional optimization audits before generating embeddings.