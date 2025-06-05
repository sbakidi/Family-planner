# Family-planner

Een eenvoudige planner voor ouders om diensten, evenementen en verblijfsperiodes van kinderen te beheren.

## Installatie

1. Zorg dat Python 3 geïnstalleerd is.
2. Installeer de vereisten uit [`requirements.txt`](requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```

## CLI gebruiken

Start de commandoregelinterface met:
```bash
python main.py
```

## Flask-app gebruiken

De webapplicatie start je met:
```bash
python app.py
```
Deze draait standaard op `http://localhost:5000`.

## Tests uitvoeren

Alle unittests kun je draaien met:
```bash
python -m unittest discover
```
