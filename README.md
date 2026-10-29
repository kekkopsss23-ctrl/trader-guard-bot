# Trader Guard Bot

Bot Telegram che protegge il topic **"Trader verificati"**: cancella automaticamente
i messaggi di chi non è nella lista dei trader verificati. Gli admin del gruppo
possono sempre scrivere.

## 1. Crea il bot
1. Su Telegram apri **@BotFather** → `/newbot` → copia il token.
2. Aggiungi il bot al gruppo e rendilo **amministratore** con il permesso
   **"Elimina messaggi"**.
3. (Consigliato) In BotFather → `/setprivacy` → **Disable**, così il bot vede tutti
   i messaggi del gruppo, non solo i comandi.

## 2. Trova l'id del topic
1. Avvia il bot (vedi sotto) lasciando `THREAD_ID=0`.
2. Scrivi `/topic` **dentro** il topic "Trader verificati": il bot risponde con
   `chat_id` e `message_thread_id`.
3. Metti l'id del topic in `THREAD_IDS` (verificati + admin) oppure in
   `ADMIN_ONLY_THREAD_IDS` (solo admin, es. Annunci). Più topic separati da
   virgola: `THREAD_IDS=66017,66500`. `GROUP_ID` è opzionale. Poi riavvia.
   In alternativa prendi gli id dal link di un messaggio del topic:
   `https://t.me/c/<gruppo>/<topic_id>/<msg_id>` → `GROUP_ID=-100<gruppo>`, topic_id.

## 3. Avvio in locale
```bash
pip install -r requirements.txt
cp .env.example .env     # inserisci il token e gli id
export $(cat .env | xargs)
python bot.py
```

## 4. Deploy su Railway
1. Carica la cartella su GitHub (il `.gitignore` esclude già `.env` e `verificati.json`).
2. Railway → New Project → Deploy from GitHub repo.
3. In **Variables** inserisci `BOT_TOKEN`, `THREAD_IDS`, `ADMIN_ONLY_THREAD_IDS`, `GROUP_ID`.
4. Per non perdere la lista ai riavvii, aggiungi un **Volume** (es. montato su
   `/data`) e imposta `DATA_FILE=/data/verificati.json`.
5. Il `Procfile` avvia `python bot.py` come worker.

## Comandi (solo admin)
| Comando | Cosa fa |
|---|---|
| `/verifica` (in risposta a un messaggio) | aggiunge quell'utente ai verificati |
| `/verifica 123456789` | aggiunge per user_id |
| `/rimuovi` / `/rimuovi 123456789` | toglie dalla lista |
| `/lista` | mostra i verificati |
| `/topic` | mostra chat_id e id del topic corrente |
| `/id` | (tutti) mostra il proprio user_id |

## Note
- Il bot cancella solo i messaggi arrivati **dopo** il suo avvio.
- Senza topic configurati il bot non cancella nulla (modalità sicura per la configurazione).
