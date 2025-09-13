Usage:

```bash
python -m venv venv
source venv/bin/activate
pip3 install requests beautifulsoup4 genanki


python main.py --word-level a1
python main.py --word-level a2
python main.py --word-level b1
python main.py --word-level b2
python main.py --word-level c1

python main.py --word-level none --csv-file oxford-phrase.csv --output-file-name oxford-5000-phrase.apkg
```


We found words from this repo https://github.com/nalgeon/words
