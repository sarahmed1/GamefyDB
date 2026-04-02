import argparse
from gamefydb.ingestor import ingest_all
from gamefydb.cleaner import clean_all
from gamefydb.transformer import transform
from gamefydb.writer import write_all


def main():
    parser = argparse.ArgumentParser(description='GamefyDB ETL pipeline')
    parser.add_argument('--input',  default='excel',  help='Directory containing .xls source files')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--format', dest='fmt', choices=['csv', 'excel'], default='csv',
                        help='Output format: csv (default) or excel')
    args = parser.parse_args()

    print(f'Ingesting from {args.input}...')
    raw = ingest_all(args.input)

    print('Cleaning...')
    cleaned = clean_all(raw)

    print('Transforming to star schema...')
    schema = transform(cleaned)

    print(f'Writing {args.fmt} output to {args.output}...')
    write_all(schema, args.output, fmt=args.fmt)

    print('Done.')
    for name, df in schema.items():
        print(f'  {name}: {len(df)} rows')


if __name__ == '__main__':
    main()
