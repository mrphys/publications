#!/usr/bin/env bash

PY_SCRIPT="data/fetch_pubmed.py"
MD_DIR="content"

for MD_FILE in "$MD_DIR"/*/*.md; do
    # Extract dataset name from the file path in `file:` (strip 'data/' and '.json')
    dataset_name=$(grep "^file:" "$MD_FILE" | sed -E "s/file:[[:space:]]*'data\/(.*)\.json'/\1/")

    # Extract the authors string from `authors:` line
    authors_line=$(grep "^authors:" "$MD_FILE" | sed -E "s/authors:[[:space:]]*\"(.*)\"/\1/")

    # Run the Python script
    echo "Running for dataset: $dataset_name"
    python "$PY_SCRIPT" "$authors_line" "$dataset_name"
done
