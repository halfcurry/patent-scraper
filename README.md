
## Run Script

python -m venv .venv

.\\.venv\Scripts\activate

pip install -r .\requirements.txt

python scraper.py test.csv output.json --sleep 2.0

## Dataset

https://huggingface.co/datasets/AI-Growth-Lab/patents_claims_1.5m_traim_test/tree/main

## Paper and Reference Code

https://arxiv.org/pdf/2103.11933

https://arxiv.org/abs/2103.11933

https://huggingface.co/AI-Growth-Lab/PatentSBERTa

https://github.com/AI-Growth-Lab/PatentSBERTa