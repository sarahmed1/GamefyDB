import json
import os
import pandas as pd


def _detect_relationships(schema: dict) -> list:
    """Auto-detect FK→PK relationships by matching *_id columns across fact and dim tables.

    For every fact table column ending in _id, checks whether a dim table exists
    whose first column (the surrogate PK) has the same name. Returns a list of
    relationship dicts compatible with Power BI's relationship model.
    """
    dim_pks = {
        df.columns[0]: name
        for name, df in schema.items()
        if name.startswith('dim_')
    }

    relationships = []
    for name, df in schema.items():
        if not name.startswith('fact_'):
            continue
        for col in df.columns:
            if col.endswith('_id') and col in dim_pks:
                relationships.append({
                    'fromTable':   name,
                    'fromColumn':  col,
                    'toTable':     dim_pks[col],
                    'toColumn':    col,
                    'cardinality': 'manyToOne',
                    'active':      True,
                })
    return relationships


def write_all(schema: dict, output_dir: str, fmt: str = 'csv') -> None:
    """Write all star-schema tables to output_dir.

    Args:
        schema: Output of transformer.transform() — {table_name: DataFrame}.
        output_dir: Root output directory (created if absent).
        fmt: 'csv' (default) writes dims/ and facts/ subdirectories.
             'excel' writes a single gamefydb.xlsx workbook.
    """
    os.makedirs(output_dir, exist_ok=True)

    relationships = _detect_relationships(schema)
    rel_path = os.path.join(output_dir, 'relationships.json')
    with open(rel_path, 'w') as f:
        json.dump({'relationships': relationships}, f, indent=2)

    if fmt == 'excel':
        _write_excel(schema, output_dir)
        return

    if fmt != 'csv':
        raise ValueError(f"Unknown fmt {fmt!r}; expected 'csv' or 'excel'")

    dims_dir = os.path.join(output_dir, 'dims')
    facts_dir = os.path.join(output_dir, 'facts')
    os.makedirs(dims_dir, exist_ok=True)
    os.makedirs(facts_dir, exist_ok=True)

    for name, df in schema.items():
        subdir = dims_dir if name.startswith('dim_') else facts_dir
        df.to_csv(os.path.join(subdir, f'{name}.csv'), index=False)


def _write_excel(schema: dict, output_dir: str) -> None:
    path = os.path.join(output_dir, 'gamefydb.xlsx')
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, df in schema.items():
            df.to_excel(writer, sheet_name=name, index=False)
