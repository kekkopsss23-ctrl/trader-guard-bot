"""
Trader Guard Bot
----------------
Cancella nel topic "Trader verificati" i messaggi scritti da chi non è
nella lista dei trader verificati (gli amministratori del gruppo sono sempre
ammessi).

Comandi (solo admin del gruppo):
  /verifica            -> in risposta a un messaggio: verifica quell'utente
  /verifica 123456789  -> verifica per user_id
  /rimuovi             -> in risposta a un messaggio: toglie l'utente dalla lista
  /rimuovi 123456789   -> toglie per user_id
  /lista               -> mostra i verificati
  /topic               -> mostra l'id del topic in cui lo scrivi

Variabili d'ambiente:
  BOT_TOKEN               token di BotFather
  THREAD_IDS              topic dove scrivono verificati + admin, separati da virgola (es. 66017)
  ADMIN_ONLY_THREAD_IDS   topic dove scrivono solo gli admin, es. Annunci (es. 70123)
  GROUP_ID                id del gruppo (opzionale, 0 = qualsiasi)
  DATA_FILE               dove salvare la lista verificati
  /id                  -> mostra il tuo user_id (tutti possono usarlo)
"""

import json
import logging
import os
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("trader-guard")

# ---------------------------------------------------------------- configurazione
TOKEN = os.environ["BOT_TOKEN"]
def _ids(nome: str) -> set[int]:
    """Legge una variabile tipo '66017,70123' e restituisce un set di int."""
    raw = os.environ.get(nome, "").replace(";", ",")
    return {int(x) for x in raw.split(",") if x.strip().lstrip("-").isdigit() and int(x) != 0}


# Topic dove scrivono solo verificati + admin (THREAD_ID è accettato per compatibilità)
THREAD_IDS = _ids("THREAD_IDS") | _ids("THREAD_ID")
# Topic dove scrivono SOLO gli admin (es. Annunci)
ADMIN_ONLY_THREAD_IDS = _ids("ADMIN_ONLY_THREAD_IDS")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))    # 0 = qualsiasi gruppo
DATA_FILE = Path(os.environ.get("DATA_FILE", "verificati.json"))


# ---------------------------------------------------------------- lista verificati
def carica_verificati() -> set[int]:
    if DATA_FILE.exists():
        try:
            return set(json.loads(DATA_FILE.read_text()))
        except Exception as e:  # file corrotto: riparto da zero
            log.warning("verificati.json illeggibile (%s), riparto vuoto", e)
    return set()


def salva_verificati(ids: set[int]) -> None:
    DATA_FILE.write_text(json.dumps(sorted(ids)))


VERIFICATI: set[int] = carica_verificati()


# ---------------------------------------------------------------- helper
async def e_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None or chat.type == "private":
        return False
    membro = await context.bot.get_chat_member(chat.id, user.id)
    return membro.status in ("administrator", "creator")


def id_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Ricava lo user_id da una risposta oppure dall'argomento del comando."""
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id
    if context.args:
        try:
            return int(context.args[0])
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------- comandi
async def cmd_verifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await e_admin(update, context):
        return
    uid = id_target(update, context)
    if uid is None:
        await update.effective_message.reply_text(
            "Usa /verifica rispondendo a un messaggio dell'utente, oppure /verifica <user_id>."
        )
        return
    VERIFICATI.add(uid)
    salva_verificati(VERIFICATI)
    await update.effective_message.reply_text(f"✅ Utente {uid} aggiunto ai trader verificati.")


async def cmd_rimuovi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await e_admin(update, context):
        return
    uid = id_target(update, context)
    if uid is None:
        await update.effective_message.reply_text(
            "Usa /rimuovi rispondendo a un messaggio dell'utente, oppure /rimuovi <user_id>."
        )
        return
    VERIFICATI.discard(uid)
    salva_verificati(VERIFICATI)
    await update.effective_message.reply_text(f"❌ Utente {uid} rimosso dai trader verificati.")


async def cmd_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await e_admin(update, context):
        return
    if not VERIFICATI:
        await update.effective_message.reply_text("Nessun trader verificato ancora.")
        return
    righe = []
    for uid in sorted(VERIFICATI):
        try:
            m = await context.bot.get_chat_member(update.effective_chat.id, uid)
            nome = m.user.full_name + (f" (@{m.user.username})" if m.user.username else "")
        except Exception:
            nome = "non nel gruppo"
        righe.append(f"• <code>{uid}</code> — {nome}")
    await update.effective_message.reply_text(
        "Trader verificati:\n" + "\n".join(righe), parse_mode=ParseMode.HTML
    )


async def cmd_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    tid = msg.message_thread_id
    await msg.reply_text(
        f"chat_id: <code>{msg.chat_id}</code>\n"
        f"message_thread_id: <code>{tid if tid else 'nessuno (chat generale)'}</code>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.effective_message.reply_text(
        f"Il tuo user_id è <code>{u.id}</code>", parse_mode=ParseMode.HTML
    )


# ---------------------------------------------------------------- filtro messaggi
async def filtro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg is None or msg.from_user is None:
        return
    if GROUP_ID and msg.chat_id != GROUP_ID:
        return
    tid = msg.message_thread_id
    if tid not in THREAD_IDS and tid not in ADMIN_ONLY_THREAD_IDS:
        return  # non è un topic protetto

    uid = msg.from_user.id
    if tid in THREAD_IDS and uid in VERIFICATI:
        return
    if await e_admin(update, context):
        return

    try:
        await msg.delete()
        log.info("Cancellato messaggio di %s (%s) nel topic %s", uid, msg.from_user.full_name, tid)
    except Exception as e:
        log.error("Impossibile cancellare il messaggio di %s: %s", uid, e)


# ---------------------------------------------------------------- avvio
def main():
    if not THREAD_IDS and not ADMIN_ONLY_THREAD_IDS:
        log.warning("Nessun topic configurato: il bot NON cancella nulla. Imposta THREAD_IDS / ADMIN_ONLY_THREAD_IDS.")

    app = Application.builder().token(TOKEN).build()

    gruppi = filters.ChatType.GROUPS
    app.add_handler(CommandHandler("verifica", cmd_verifica, filters=gruppi))
    app.add_handler(CommandHandler("rimuovi", cmd_rimuovi, filters=gruppi))
    app.add_handler(CommandHandler("lista", cmd_lista, filters=gruppi))
    app.add_handler(CommandHandler("topic", cmd_topic, filters=gruppi))
    app.add_handler(CommandHandler("id", cmd_id))

    # tutto il resto nei gruppi (testo, foto, sticker, ...) passa dal filtro
    app.add_handler(
        MessageHandler(gruppi & ~filters.COMMAND & ~filters.StatusUpdate.ALL, filtro)
    )

    log.info("Trader Guard Bot avviato. Topic verificati: %s | Topic solo admin: %s",
             sorted(THREAD_IDS) or "nessuno", sorted(ADMIN_ONLY_THREAD_IDS) or "nessuno")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
