
# Creating a virtual environment to run this code

#!/bin/bash
set -e
set -x

virtualenv -p python3 .
source ./bin/activate

pip install -r rouge/requirements.txt
# python -m rouge.io
# python -m rouge.rouge_scorer
# python -m rouge.scoring
