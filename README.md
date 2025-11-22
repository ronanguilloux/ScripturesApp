# Bible CLI Tool

A command-line interface for reading the Bible in Greek (N1904), English, and French (TOB).

```sh
./run.sh "Mc 1:1-2"

Marc 1:1-2

Marc 1:1
Ἀρχὴ τοῦ εὐαγγελίου Ἰησοῦ Χριστοῦ (Υἱοῦ Θεοῦ). 
Commencement de l'Evangile de Jésus Christ Fils de Dieu:

Marc 1:2
Καθὼς γέγραπται ἐν τῷ Ἠσαΐᾳ τῷ προφήτῃ Ἰδοὺ ἀποστέλλω τὸν ἄγγελόν μου πρὸ προσώπου σου, ὃς κατασκευάσει τὴν ὁδόν σου· 
Ainsi qu'il est écrit dans le livre du prophète Esaïe, Voici, j'envoie mon messager en avant de toi, pour préparer ton chemin.
```

## Setup

The project requires Python 3 and the `text-fabric` library.
A helper script `run.sh` is provided to manage the virtual environment and dependencies automatically.

## Usage

You can use the `run.sh` script to execute commands. It will automatically set up the environment if needed.

### Search for a Verse
```bash
./run.sh "John 3:16"
./run.sh "Luc 1:1"
```

### Search for a Range
```bash
./run.sh "Mt 5:1-10"
```

### List Books
```bash
./run.sh list books
```

## Manual Setup

If you prefer to run `main.py` directly, you must install the dependencies:

```bash
pip install -r requirements.txt
```

Or use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py "Jn 3:16"
```
