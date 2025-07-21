from flask import Flask, request, jsonify, render_template_string
from binance.client import Client
from binance.enums import *
import requests
import threading
import json
import os
from datetime import datetime
import hashlib
import hmac
import time

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# === CONFIGURATION SÉCURISÉE ===
API_KEY ="II6OiPRBKVAGGFXhq4qp695DjAHk9OxUpQsPLT53yz8WWbWeSBn8HyDlT8rU3foh"
API_SECRET = "qxFIxoNyzUnwtx7pjGIXUXzzQeFnOHoBLBIiMib0UBaAgky8oIwFQMfa0fiTYQuC"
USE_TESTNET = False

TELEGRAM_TOKEN = "8026364606:AAGmeZiLVGCAayvk-yNb1Fm3GaUxWkq0m1c"
TELEGRAM_CHAT_ID = "7711423126"

# Clé secrète pour sécuriser les webhooks TradingView
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your_secret_key_here')

app = Flask(__name__)

# === CONFIGURATION FILE ===
CONFIG_FILE = "trading_config.json"

# Liste des cryptomonnaies considérées comme halal (basée sur les critères islamiques)
HALAL_COINS = {
    # Coins avec utilité technologique claire et pas de ribā
    'BTC', 'ETH', 'AVA', 'ADA', 'DOT', 'MATIC', 'AVAX', 'SOL', 'ATOM', 'ALGO',
    'VET', 'XTZ', 'HBAR', 'IOTA', 'XLM', 'FIL', 'THETA', 'EGLD', 'ONE', 'NEAR',
    'S', 'SAND', 'MANA', 'ORDI', 'OP', 'PARTI', 'OMNI', 'ARB', 'SEI', 'ZK',
    'SUI', 'FET', 'ENS', 'EDU', 'LRC', 'ENJ', 'CHZ', 'BAT', 'ZIL', 'ICX',
    'OMG', 'RLC', 'ACH', 'BAND', 'RSR', 'MDT', 'OCEAN', 'NKN', 'CTSI', 'DUSK',
    'HIGH', 'TON', 'WIN', 'HOT', 'DENT', 'KEY', 'RARE', 'ONG', 'DOGE', 'MASK',
    'TAO', 'KAITO', 'API3', 'ARKM', 'GRT', 'FIDA', 'QTUM', 'MANTA', 'SCR', 'UTK',
    'ARPA', 'WLD', 'FLUX', 'GMT', 'PHA', 'SUI', 'VANA', 'TRX', 'HOOK', 'APE', 'RAD',
     'EPIC', 'XVG', 'PHB', 'ETC',
    # Ajoutez d'autres coins selon vos critères halal
}

# Configuration par défaut
default_config = {
    "auto_trading": False,
    "trading_active": False,
    "default_usdt_amount": 100,
    "symbol_configs": {},
    "max_risk_percentage": 5,
    "stop_loss_percentage": 2,
    "take_profit_percentage": 5,
    "language": "fr",
    "trailing_stop_percentage": 1.5,
    "halal_filter_enabled": True,
    "allowed_symbols": [],
    "min_volume_filter": 1000000,  # Volume minimum en USDT
    "price_change_threshold": 0.5  # Seuil de changement de prix minimum
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return default_config.copy()
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

config = load_config()

# === MULTILINGUAL SUPPORT ===
messages = {
    "fr": {
        "welcome": "🤖 **Bot Trading Smilebot**\n\nStatut: {status}\nMode: {mode}\nSolde: {balance} USDT\nCoins Halal: {halal_status}\nSymboles actifs: {symbols_count}\n\nChoisissez une action:",
        "trading_started": "✅ Trading démarré",
        "trading_stopped": "🛑 Trading arrêté",
        "auto_mode_on": "🤖 Mode automatique activé",
        "auto_mode_off": "👨‍💻 Mode manuel activé",
        "balance_updated": "💰 Solde mis à jour: {amount} USDT",
        "no_open_trades": "Aucune position ouverte",
        "total_profit": "💰 Profit Total: {profit} USDT",
        "summary": "📊 **Résumé**\nTrades: {trades}\nProfit: {profit} USDT\nWin Rate: {winrate}%",
        "language_changed": "🌐 Langue changée en Français",
        "halal_filter_on": "✅ Filtre Halal activé",
        "halal_filter_off": "❌ Filtre Halal désactivé",
        "symbols_updated": "📈 Symboles mis à jour: {count} coins disponibles",
        # Nouveaux messages
        "begin": "✨ Begin",
        "stop_trading": "🏁 Stop Trading",
        "auto_trade": "🤖 Auto Trade",
        "manual_trade": "👨‍💻 Manual Trade",
        "set_balance": "💰 Set Balance",
        "show_open_trades": "📈 Show Open Trades",
        "show_total_profit": "💰 Show Total Profit",
        "show_summary": "📊 Show Summary",
        "halal_filter": "☪️ Filtre Halal",
        "toggle_sma": "📉 SMA Scanner" ,
        "update_symbols": "🔄 Update Symbols",
        "language": "🌐 Language"
    },
    "en": {
        "welcome": "🤖 **Smilebot Trading Bot**\n\nStatus: {status}\nMode: {mode}\nBalance: {balance} USDT\nHalal Coins: {halal_status}\nActive Symbols: {symbols_count}\n\nChoose an action:",
        "trading_started": "✅ Trading started",
        "trading_stopped": "🛑 Trading stopped",
        "auto_mode_on": "🤖 Auto mode enabled",
        "auto_mode_off": "👨‍💻 Manual mode enabled",
        "balance_updated": "💰 Balance updated: {amount} USDT",
        "no_open_trades": "No open positions",
        "total_profit": "💰 Total Profit: {profit} USDT",
        "summary": "📊 **Summary**\nTrades: {trades}\nProfit: {profit} USDT\nWin Rate: {winrate}%",
        "language_changed": "🌐 Language changed to English",
        "halal_filter_on": "✅ Halal filter enabled",
        "halal_filter_off": "❌ Halal filter disabled",
        "symbols_updated": "📈 Symbols updated: {count} coins available",
        # Nouveaux messages
        "begin": "✨ Begin",
        "stop_trading": "🏁 Stop Trading",
        "auto_trade": "🤖 Auto Trade",
        "manual_trade": "👨‍💻 Manual Trade",
        "set_balance": "💰 Set Balance",
        "show_open_trades": "📈 Show Open Trades",
        "show_total_profit": "💰 Show Total Profit",
        "show_summary": "📊 Show Summary",
        "halal_filter": "☪️ Halal Filter",
        "update_symbols": "🔄 Update Symbols",
        "language": "🌐 Language"
    }
}

def get_message(key, **kwargs):
    lang = config.get('language', 'fr')
    message = messages[lang].get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message

# === INITIALISATION BINANCE ===
if USE_TESTNET:
    client = Client(API_KEY, API_SECRET, testnet=True)
    client.API_URL = 'https://testnet.binance.vision/api'
else:
    client = Client(API_KEY, API_SECRET)

# === GESTION DES SYMBOLES ===
def get_all_trading_symbols():
    """Récupère tous les symboles de trading disponibles sur Binance"""
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        print(f"Erreur récupération symboles: {e}")
        return []

def update_trading_symbols():
    """Met à jour la liste des symboles de trading"""
    symbols = get_all_trading_symbols()

    # Filtrer par volume si nécessaire
    if config.get('min_volume_filter', 0) > 0:
        symbols = filter_by_volume(symbols)

    config['allowed_symbols'] = symbols
    save_config(config)
    return len(symbols)

def filter_by_volume(symbols):
    """Filtre les symboles par volume de trading"""
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        print(f"Erreur filtrage volume: {e}")
        return symbols

def is_symbol_allowed(symbol):
    """Vérifie si un symbole est autorisé au trading"""
    if not config.get('allowed_symbols'):
        update_trading_symbols()

    return symbol.upper() in config.get('allowed_symbols', [])

# === TELEGRAM BOT ===
bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher

pending_order = None
trade_history = []
open_positions = {}
total_profit = 0.0

def send_telegram_message(text, reply_markup=None):
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        print(f"Erreur envoi Telegram: {e}")

def get_account_balance():
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        print(f"Erreur récupération solde: {e}")
        return config['default_usdt_amount']

def create_main_keyboard():
    keyboard = [
        [
        InlineKeyboardButton(get_message("begin"), callback_data="begin"),
        InlineKeyboardButton(get_message("stop_trading"), callback_data="stop_trading")
        ],
        [
        InlineKeyboardButton(get_message("auto_trade"), callback_data="auto_trade"),
        InlineKeyboardButton(get_message("manual_trade"), callback_data="manual_trade")
        ],
        [
        InlineKeyboardButton(get_message("set_balance"), callback_data="set_balance"),
        InlineKeyboardButton(get_message("show_open_trades"), callback_data="show_open_trades")
        ],
        [
        InlineKeyboardButton(get_message("show_total_profit"), callback_data="show_total_profit"),
        InlineKeyboardButton(get_message("show_summary"), callback_data="show_summary")
        ],
        [
        InlineKeyboardButton(get_message("halal_filter"), callback_data="halal_filter"),
        InlineKeyboardButton(get_message("update_symbols"), callback_data="update_symbols")
        ],
        [
        InlineKeyboardButton(get_message("language"), callback_data="language")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_language_keyboard():
    keyboard = [
        [
        InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
        ],
        [
        InlineKeyboardButton("🔙 Retour / Back", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_balance_keyboard():
    keyboard = [
       [
        InlineKeyboardButton("💰 5USDT", callback_data="balance_5"),
        InlineKeyboardButton("💰 10 USDT", callback_data="balance_10")
        ],
    [
        InlineKeyboardButton("💰 15USDT", callback_data="balance_5"),
        InlineKeyboardButton("💰 25 USDT", callback_data="balance_10")
        ],
        [
        InlineKeyboardButton("💰 50 USDT", callback_data="balance_50"),
        InlineKeyboardButton("💰 100 USDT", callback_data="balance_100")
        ],
        [
        InlineKeyboardButton("💰 250 USDT", callback_data="balance_250"),
        InlineKeyboardButton("💰 500 USDT", callback_data="balance_500")
        ],
        [
        InlineKeyboardButton("💰 1000 USDT", callback_data="balance_1000"),
        InlineKeyboardButton("💰 Custom", callback_data="balance_custom")
        ],
        [
        InlineKeyboardButton("🔙 Retour / Back", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def calculate_quantity(symbol, usdt_amount):
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        print(f"Erreur récupération prix : {e}")
        return None, None

def execute_trade(symbol, action, quantity, price):
    global total_profit
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        trade_record = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'price': price,
        'order_id': None,
        'status': f'ERROR: {str(e)}'
        }
        trade_history.append(trade_record)
        return False, str(e)

# === SÉCURITÉ WEBHOOK ===
def verify_tradingview_webhook(request):
    """Vérifie l'authenticité du webhook TradingView"""
    if not WEBHOOK_SECRET or WEBHOOK_SECRET == 'your_secret_key_here':
        return True  # Pas de sécurité configurée

    signature = request.headers.get('X-TradingView-Signature')
    if not signature:
        return False

    body = request.get_data()
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, f"sha256={expected_signature}")

# === COMMANDES TELEGRAM ===
def start(update: Update, context: CallbackContext):
    balance = get_account_balance()
    status = "🟢 ACTIF" if config['trading_active'] else "🔴 INACTIF"
    mode = "🤖 AUTO" if config['auto_trading'] else "👨‍💻 MANUEL"
    halal_status = "✅" if config.get('halal_filter_enabled', True) else "❌"
    symbols_count = len(config.get('allowed_symbols', []))

    welcome_text = get_message("welcome",
    status=status,
    mode=mode,
    balance=balance,
    halal_status=halal_status,
    symbols_count=symbols_count)

    update.message.reply_text(welcome_text,
        parse_mode='Markdown',
        reply_markup=create_main_keyboard())

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    balance = get_account_balance()
    status = "🟢 ACTIF" if config['trading_active'] else "🔴 INACTIF"
    mode = "🤖 AUTO" if config['auto_trading'] else "👨‍💻 MANUEL"
    halal_status = "✅" if config.get('halal_filter_enabled', True) else "❌"
    symbols_count = len(config.get('allowed_symbols', []))

    if query.data == "begin":
        config['trading_active'] = True
        save_config(config)
        text = f"✅ {get_message('trading_started')}\n\n{get_message('welcome', status='🟢 ACTIF', mode=mode, balance=balance, halal_status=halal_status, symbols_count=symbols_count)}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "stop_trading":
        config['trading_active'] = False
        save_config(config)
        text = f"🛑 {get_message('trading_stopped')}\n\n{get_message('welcome', status='🔴 INACTIF', mode=mode, balance=balance, halal_status=halal_status, symbols_count=symbols_count)}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "auto_trade":
        config['auto_trading'] = True
        save_config(config)
        text = f"🤖 {get_message('auto_mode_on')}\n\n{get_message('welcome', status=status, mode='🤖 AUTO', balance=balance, halal_status=halal_status, symbols_count=symbols_count)}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "manual_trade":
        config['auto_trading'] = False
        save_config(config)
        text = f"👨‍💻 {get_message('auto_mode_off')}\n\n{get_message('welcome', status=status, mode='👨‍💻 MANUEL', balance=balance, halal_status=halal_status, symbols_count=symbols_count)}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "halal_filter":
        config['halal_filter_enabled'] = not config.get('halal_filter_enabled', True)
        save_config(config)
        # Mettre à jour les symboles après changement du filtre
        update_trading_symbols()
        message_key = "halal_filter_on" if config['halal_filter_enabled'] else "halal_filter_off"
        text = f"☪️ {get_message(message_key)}\n\n{get_message('welcome', status=status, mode=mode, balance=balance, halal_status='✅' if config['halal_filter_enabled'] else '❌', symbols_count=len(config.get('allowed_symbols', [])))}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "update_symbols":
        count = update_trading_symbols()
        text = f"🔄 {get_message('symbols_updated', count=count)}\n\n{get_message('welcome', status=status, mode=mode, balance=balance, halal_status=halal_status, symbols_count=count)}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "set_balance":
        text = f"💰 **Définir le solde de trading**\n\nSolde actuel: {config['default_usdt_amount']} USDT\n\nChoisissez un nouveau montant:"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_balance_keyboard())

    elif query.data == "balance_custom":
        global waiting_for_custom_balance
        waiting_for_custom_balance = True

    elif query.data.startswith("balance_"):
        amount = int(query.data.split("_")[1])
        config['default_usdt_amount'] = amount
        save_config(config)
        text = f"💰 {get_message('balance_updated', amount=amount)}\n\n" + \
    get_message("welcome", status=status, mode=mode, balance=balance,
    halal_status=halal_status, symbols_count=symbols_count)
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())


    elif query.data == "show_open_trades":
        if not open_positions:
            text = f"📈 {get_message('no_open_trades')}"
        else:
            text = "📈 **Positions ouvertes:**\n\n"
        else:
        text = "📈 **Positions ouvertes:**\n\n"
        for symbol, pos in open_positions.items():
            try:
                requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{symbol}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi du signal pour {symbol}: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")]]
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "show_total_profit":
        profit_text = get_message('total_profit', profit=total_profit)
        text = f"💰 **Statistiques de profit**\n\n{profit_text}\nTrades total: {len(trade_history)}"
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")]]
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "show_summary":
        successful_trades = len([t for t in trade_history if t['status'] == 'SUCCESS'])
        win_rate = (successful_trades / len(trade_history) * 100) if trade_history else 0
        summary_text = get_message('summary',
    trades=len(trade_history),
    profit=total_profit,
    winrate=win_rate)
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")]]
        query.edit_message_text(summary_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


    elif query.data == "toggle_sma":
        config["sma_scanner_enabled"] = not config.get("sma_scanner_enabled", True)
        save_config(config)
        status_txt = "✅ SMA Scanner activé" if config["sma_scanner_enabled"] else "❌ SMA Scanner désactivé"
        updated = get_message("welcome", status=status, mode=mode, balance=balance, halal_status=halal_status, symbols_count=symbols_count)
        query.edit_message_text(f"{status_txt}\n\n{updated}", parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "language":
        text = "🌐 **Choisir la langue / Choose Language**"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_language_keyboard())

    elif query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        config['language'] = lang
        save_config(config)
        text = f"🌐 {get_message('language_changed')}\n\n{get_message('welcome', status=status, mode=mode, balance=balance, halal_status=halal_status, symbols_count=symbols_count)}"
        query.edit_message_text(text, parse_mode='Markdown', reply_markup=create_main_keyboard())

    elif query.data == "back_to_main":
        welcome_text = get_message("welcome",
    status=status,
    mode=mode,
    balance=balance,
    halal_status=halal_status,
    symbols_count=symbols_count)
        query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=create_main_keyboard())

# Enregistrer les handlers
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CallbackQueryHandler(button_callback))

# === INTERFACE WEB ===
@app.route('/')
def dashboard():
    return jsonify({
        'status': 'Bot running',
        'config': config,
        'open_positions': len(open_positions),
        'total_trades': len(trade_history),
        'total_profit': total_profit,
        'allowed_symbols': len(config.get('allowed_symbols', [])),
        'halal_filter': config.get('halal_filter_enabled', True)
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint pour recevoir les signaux de TradingView"""
    global pending_order

    # Vérifier l'authenticité du webhook
    if not verify_tradingview_webhook(request):
        return jsonify({'error': 'Invalid signature'}), 401

    # Vérifier si le trading est actif
    if not config['trading_active']:
        return jsonify({'error': 'Trading is not active'}), 400

    data = request.json
    if not data or 'symbol' not in data or 'action' not in data:
        return jsonify({'error': 'Invalid payload'}), 400

    symbol = data['symbol'].upper()
    action = data['action'].upper()

    # Vérifier si le symbole est autorisé
    if not is_symbol_allowed(symbol):
        return jsonify({'error': f'Symbol {symbol} not allowed or not halal'}), 400

    # Utiliser la configuration du symbole ou la configuration par défaut
    if symbol in config['symbol_configs']:
        usdt_amount = config['symbol_configs'][symbol]['usdt_amount']
    else:
        usdt_amount = config['default_usdt_amount']

    qty, price = calculate_quantity(symbol, usdt_amount)
    if qty is None:
        return jsonify({'error': 'Error fetching price'}), 500

    # Si le trading automatique est activé, exécuter directement
    if config['auto_trading']:
        success, result = execute_trade(symbol, action, qty, price)

        if success:
        message = (
        f"✅ **TRADE AUTO EXÉCUTÉ** (TradingView)\n"
        f"Action: {action} {symbol}\n"
        f"Quantité: {qty}\n"
        f"Prix: {price} USDT\n"
        f"Total: {qty * price:.2f} USDT\n"
        f"Halal: {'✅' if symbol.replace('USDT', '') in HALAL_COINS else '❓'}"
        )
        send_telegram_message(message)
        return jsonify({
        'status': 'executed',
        'order_id': result['orderId'],
        'symbol': symbol,
        'action': action,
        'quantity': qty,
        'price': price
        }), 200
        else:
        error_message = f"❌ **ERREUR TRADE AUTO** (TradingView)\n{action} {symbol}\n{result}"
        send_telegram_message(error_message)
        return jsonify({'error': result}), 500

    # Sinon, créer un ordre en attente pour confirmation manuelle
    pending_order = {
        'symbol': symbol,
        'action': action,
        'quantity': qty,
        'price': price,
        'source': ''
    }

    # Créer un clavier pour la confirmation
    keyboard = [
        [
        InlineKeyboardButton("✅ Confirmer", callback_data=f"confirm_trade"),
        InlineKeyboardButton("❌ Annuler", callback_data="cancel_trade")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    halal_status = "✅" if symbol.replace('USDT', '') in HALAL_COINS else "❓"
    text = (
        f"⚠️ **SIGNAL {action} REÇU** (TradingView)\n"
        f"Symbole: {symbol}\n"
        f"Prix actuel: {price} USDT\n"
        f"Quantité: {qty}\n"
        f"Montant: {usdt_amount} USDT\n"
        f"Halal: {halal_status}\n\n"
        "Confirmer le trade?"
    )
    send_telegram_message(text, reply_markup)

    return jsonify({
        'status': 'waiting confirmation',
        'symbol': symbol,
        'action': action,
        'quantity': qty,
        'price': price
    }), 200

@app.route('/tradingview', methods=['POST'])
def tradingview_webhook():
    """Endpoint spécialisé pour TradingView avec format JSON étendu"""
    global pending_order

    # Vérifier l'authenticité du webhook
    if not verify_tradingview_webhook(request):
        return jsonify({'error': 'Invalid signature'}), 401

    # Vérifier si le trading est actif
    if not config['trading_active']:
        return jsonify({'error': 'Trading is not active'}), 400

    data = request.json
    print(f"TradingView Signal reçu: {data}")  # Debug

    # Format  étendu
    required_fields = ['symbol', 'action']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: symbol, action'}), 400

    symbol = data['symbol'].upper()
    action = data['action'].upper()

    # Support pour différents formats de symboles TradingView
    if not symbol.endswith('USDT'):
        symbol += 'USDT'

    # Informations optionnelles de TradingView
    price_hint = data.get('price')  # Prix suggéré par TradingView
    volume_hint = data.get('volume')  # Volume suggéré
    strategy_name = data.get('strategy', 'Unknown')
    timeframe = data.get('timeframe', '1h')

    # Vérifier si le symbole est autorisé
    if not is_symbol_allowed(symbol):
        error_msg = f"❌ **SYMBOLE NON AUTORISÉ**\nSymbole: {symbol}\nRaison: {'Non-Halal' if config.get('halal_filter_enabled') else 'Non disponible'}"
        send_telegram_message(error_msg)
        return jsonify({'error': f'Symbol {symbol} not allowed or not halal'}), 400

    # Calculer la quantité
    if volume_hint:
        usdt_amount = float(volume_hint)
    elif symbol in config['symbol_configs']:
        usdt_amount = config['symbol_configs'][symbol]['usdt_amount']
    else:
        usdt_amount = config['default_usdt_amount']

    qty, current_price = calculate_quantity(symbol, usdt_amount)
    if qty is None:
        error_msg = f"❌ **ERREUR PRIX**\nSymbole: {symbol}\nImpossible de récupérer le prix actuel"
        send_telegram_message(error_msg)
        return jsonify({'error': 'Error fetching price'}), 500

    # Utiliser le prix suggéré par TradingView si disponible
    trade_price = float(price_hint) if price_hint else current_price

    # Log détaillé
    trade_info = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'action': action,
        'strategy': strategy_name,
        'timeframe': timeframe,
        'suggested_price': price_hint,
        'current_price': current_price,
        'quantity': qty,
        'volume_usdt': usdt_amount,
        'halal_approved': symbol.replace('USDT', '') in HALAL_COINS
    }

    print(f"Trade info: {trade_info}")  # Debug

    # Si le trading automatique est activé, exécuter directement
    if config['auto_trading']:
        success, result = execute_trade(symbol, action, qty, current_price)

        if success:
        message = (
        f"✅ **TRADE AUTO EXÉCUTÉ**\n"
        f"📊 Stratégie: {strategy_name}\n"
        f"⏰ Timeframe: {timeframe}\n"
        f"💱 {action} {symbol}\n"
        f"📊 Quantité: {qty}\n"
        f"💰 Prix: {current_price} USDT\n"
        f"💵 Total: {qty * current_price:.2f} USDT\n"
        f"☪️ Halal: {'✅' if symbol.replace('USDT', '') in HALAL_COINS else '❓'}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(message)
        return jsonify({
        'status': 'executed',
        'order_id': result['orderId'],
        'symbol': symbol,
        'action': action,
        'quantity': qty,
        'price': current_price,
        'strategy': strategy_name,
        'timeframe': timeframe
        }), 200
        else:
        error_message = (
        f"❌ **ERREUR TRADE AUTO**\n"
        f"📊 Stratégie: {strategy_name}\n"
        f"💱 {action} {symbol}\n"
        f"❗ Erreur: {result}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(error_message)
        return jsonify({'error': result, 'strategy': strategy_name}), 500

    # Mode manuel : créer un ordre en attente
    pending_order = {
        'symbol': symbol,
        'action': action,
        'quantity': qty,
        'price': current_price,
        'source': 'TradingView',
        'strategy': strategy_name,
        'timeframe': timeframe,
        'suggested_price': price_hint
    }

    # Créer un clavier pour la confirmation avec plus d'options
    keyboard = [
        [
        InlineKeyboardButton("✅ Confirmer Trade", callback_data="confirm_trade"),
        InlineKeyboardButton("❌ Rejeter", callback_data="cancel_trade")
        ],
        [
        InlineKeyboardButton("📊 Détails", callback_data="trade_details"),
        InlineKeyboardButton("⚙️ Modifier", callback_data="modify_trade")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    halal_status = "✅" if symbol.replace('USDT', '') in HALAL_COINS else "❓"
    price_diff = ""
    if price_hint and abs(float(price_hint) - current_price) / current_price > 0.001:
        price_diff = f"\n💡 Prix suggéré: {price_hint} USDT"

    text = (
        f"⚠️ **NOUVEAU SIGNAL**\n"
        f"📊 Stratégie: {strategy_name}\n"
        f"⏰ Timeframe: {timeframe}\n"
        f"💱 Action: {action} {symbol}\n"
        f"💰 Prix: {current_price} USDT{price_diff}\n"
        f"📊 Quantité: {qty}\n"
        f"💵 Montant: {usdt_amount} USDT\n"
        f"☪️ Halal: {halal_status}\n\n"
        "Que souhaitez-vous faire?"
    )
    send_telegram_message(text, reply_markup)

    return jsonify({
        'status': 'waiting confirmation',
        'symbol': symbol,
        'action': action,
        'quantity': qty,
        'price': current_price,
        'strategy': strategy_name,
        'timeframe': timeframe
    }), 200

@app.route('/symbols', methods=['GET'])
def get_symbols():
    """Retourne la liste des symboles autorisés"""
    if not config.get('allowed_symbols'):
        update_trading_symbols()

    symbols_info = []
    for symbol in config.get('allowed_symbols', []):
        base_asset = symbol.replace('USDT', '')
        is_halal = base_asset in HALAL_COINS
        symbols_info.append({
        'symbol': symbol,
        'base_asset': base_asset,
        'is_halal': is_halal
        })

    return jsonify({
        'total_symbols': len(symbols_info),
        'halal_filter_enabled': config.get('halal_filter_enabled', True),
        'symbols': symbols_info
    })

@app.route('/update-symbols', methods=['POST'])
def update_symbols_endpoint():
    """Met à jour manuellement la liste des symboles"""
    count = update_trading_symbols()
    return jsonify({
        'status': 'updated',
        'symbols_count': count,
        'halal_filter_enabled': config.get('halal_filter_enabled', True)
    })

@app.route('/halal-coins', methods=['GET'])
def get_halal_coins():
    """Retourne la liste des coins considérés comme halal"""
    return jsonify({
        'halal_coins': list(HALAL_COINS),
        'total_count': len(HALAL_COINS),
        'filter_enabled': config.get('halal_filter_enabled', True)
    })

@app.route('/status', methods=['GET'])
def status():
    """Status détaillé du bot"""
    return jsonify({
        'status': 'bot is running 🚀',
        'trading_active': config['trading_active'],
        'auto_trading': config['auto_trading'],
        'halal_filter_enabled': config.get('halal_filter_enabled', True),
        'allowed_symbols_count': len(config.get('allowed_symbols', [])),
        'pending_order': pending_order is not None,
        'trade_count': len(trade_history),
        'account_balance': get_account_balance(),
        'total_profit': total_profit,
        'open_positions': len(open_positions),
        'config': {
        'default_usdt_amount': config['default_usdt_amount'],
        'language': config.get('language', 'fr'),
        'min_volume_filter': config.get('min_volume_filter', 0)
        }
    })

@app.route('/test-webhook', methods=['POST'])
def test_webhook():
    """Endpoint pour tester les webhooks"""
    data = {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "price": "50000",
        "volume": "100",
        "strategy": "Test Strategy",
        "timeframe": "1h"
    }

    print("Test webhook appelé avec:", data)
    return jsonify({'message': 'Test webhook received', 'data': data})

# Gestionnaire amélioré pour les confirmations de trade
def handle_trade_confirmation(query):
    global pending_order

    if query.data == "confirm_trade" and pending_order:
        symbol = pending_order['symbol']
        action = pending_order['action']
        quantity = pending_order['quantity']
        price = pending_order['price']
        source = pending_order.get('source', 'Manual')
        strategy = pending_order.get('strategy', 'Unknown')

        success, result = execute_trade(symbol, action, quantity, price)

        if success:
        message = (
        f"✅ **TRADE CONFIRMÉ**\n"
        f"📡 Source: {source}\n"
        f"📊 Stratégie: {strategy}\n"
        f"💱 {action} {symbol}\n"
        f"📊 Quantité: {quantity}\n"
        f"💰 Prix: {price} USDT\n"
        f"💵 Total: {quantity * price:.2f} USDT\n"
        f"🆔 Order ID: {result['orderId']}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )
        query.edit_message_text(message, parse_mode='Markdown')
        else:
        error_message = (
        f"❌ **ERREUR TRADE**\n"
        f"💱 {action} {symbol}\n"
        f"❗ {result}"
        )
        query.edit_message_text(error_message, parse_mode='Markdown')

        pending_order = None

    elif query.data == "cancel_trade":
        if pending_order:
        symbol = pending_order['symbol']
        action = pending_order['action']
        query.edit_message_text(f"❌ **TRADE ANNULÉ**\n{action} {symbol}", parse_mode='Markdown')
        pending_order = None

    elif query.data == "trade_details" and pending_order:
        details = (
        f"📋 **DÉTAILS DU TRADE**\n\n"
        f"💱 Symbole: {pending_order['symbol']}\n"
        f"🎯 Action: {pending_order['action']}\n"
        f"📊 Quantité: {pending_order['quantity']}\n"
        f"💰 Prix: {pending_order['price']} USDT\n"
        f"💵 Total: {pending_order['quantity'] * pending_order['price']:.2f} USDT\n"
        f"📡 Source: {pending_order.get('source', 'Manual')}\n"
        f"📊 Stratégie: {pending_order.get('strategy', 'Unknown')}\n"
        f"⏰ Timeframe: {pending_order.get('timeframe', 'N/A')}\n"
        f"☪️ Halal: {'✅' if pending_order['symbol'].replace('USDT', '') in HALAL_COINS else '❓'}"
        )

        keyboard = [
        [
        InlineKeyboardButton("✅ Confirmer", callback_data="confirm_trade"),
        InlineKeyboardButton("❌ Annuler", callback_data="cancel_trade")
        ]
        ]
        query.edit_message_text(details, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Mise à jour du gestionnaire de boutons pour inclure les nouvelles fonctions
def enhanced_button_callback(update: Update, context: CallbackContext):
    query = update.callback_query

    # Gérer les confirmations de trade
    if query.data in ["confirm_trade", "cancel_trade", "trade_details", "modify_trade"]:
        handle_trade_confirmation(query)
        return

    # Appeler le gestionnaire de boutons original
    button_callback(update, context)

# Remplacer le gestionnaire de boutons
# Enregistrer les handlers
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CallbackQueryHandler(enhanced_button_callback))  # <-- ligne mise à jour


if __name__ == "__main__":
    print("🚀 Démarrage du Smilebot Trading Bot Enhanced...")
    print(f"🤖 Status API: http://localhost:5000/status")
    print(f"🔗 Webhook: http://localhost:5000/webhook")
    print(f"📊 TradingView: http://localhost:5000/tradingview")
    print(f"📈 Symbols: http://localhost:5000/symbols")
    print(f"☪️ Halal Coins: http://localhost:5000/halal-coins")
    print(f"📱 Utilisez /start sur Telegram pour commencer")

    # Initialiser les symboles au démarrage
    print("🔄 Initialisation des symboles de trading...")
    symbols_count = update_trading_symbols()
    print(f"✅ {symbols_count} symboles disponibles")

    # Démarrer le serveur Flask dans un thread séparé
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()

    # Démarrer le bot Telegram
    updater.start_polling()
    updater.idle()


# === SMA STRATEGY (TTR) ===
import pandas as pd

def get_klines(symbol):
    try:
        requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
    except Exception as e:
        print(f"Erreur kline pour {symbol}: {e}")
        return None

def sma_crossover_signal(df):
    df['SMA14'] = df['close'].rolling(14).mean()
    df['SMA28'] = df['close'].rolling(28).mean()
    if len(df) < 29: return None
    if df.iloc[-2]['SMA14'] < df.iloc[-2]['SMA28'] and df.iloc[-1]['SMA14'] > df.iloc[-1]['SMA28']:
        return 'BUY'
    elif df.iloc[-2]['SMA14'] > df.iloc[-2]['SMA28'] and df.iloc[-1]['SMA14'] < df.iloc[-1]['SMA28']:
        return 'SELL'
    return None

def sma_scanner_loop():
    if not config.get("sma_scanner_enabled", True):
        print("📉 SMA Scanner désactivé.")
        return

    print("📡 Démarrage du scanner SMA intégré")
    while True:
        if config.get('auto_trading') and config.get('trading_active'):
            for sym in config.get('allowed_symbols', []):
                df = get_klines(sym)
                if df is not None:
                    signal = sma_crossover_signal(df)
                    if signal:
                        print(f"📈 {sym} ➜ Signal {signal}")
        payload = {
        "symbol": sym,
        "action": signal,
        "strategy": "TTR",
        "timeframe": "3m",
        "volume": str(config.get('default_usdt_amount', 25))
        }
                        try:
                            requests.post("http://localhost:5000/tradingview", json=payload)
        signal_msg = (
        f"📡 *Signal SMA détecté*\n"
        f"🪙 Symbole: `{sym}`\n"
        f"📈 Action: *{signal}*\n"
        f"💸 Volume: {config.get('default_usdt_amount', 25)} USDT\n"
        f"🕐 Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(signal_msg)
                        except Exception as e:
                            print(f"Erreur envoi signal SMA : {e}")
        time.sleep(180)
        send_telegram_message(signal_msg)

        print(f"Erreur webhook {sym}: {e}")
        time.sleep(180)
