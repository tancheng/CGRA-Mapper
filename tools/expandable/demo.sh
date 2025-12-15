#!/usr/bin/env bash
python -m pip install --upgrade pip
pip install eventlet pandas matplotlib

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--test)
            TEST_FLAG="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

TEST_FLAG=${TEST_FLAG:-n}

rm -r ./tmp
rm -r ./result
rm -r ./fig
mkdir ./tmp
mkdir ./result
mkdir ./fig

python main.py --test=$TEST_FLAG