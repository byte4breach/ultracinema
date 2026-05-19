"""
CinemaMax Telegram Bot
Offers both Web App (Mini App) and inline Telegram booking flows.
"""

import os
import json
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
)

# ── Config ─────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "8796607447:AAHPvCaZyKyVln2rIpdsZawbwY8TIgSDtt0")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://byte4breach.github.io/ultracinema")
API_URL     = os.getenv("API_URL", "http://localhost:8000")   # your backend

STANDARD_PRICE = 20
VIP_PRICE      = 50
MOVIES_PER_PAGE = 6

CHOICE, GALLERY, TIMES, SEATS, CONFIRM = range(5)


# ── API helpers ─────────────────────────────────────────────────

async def api_get(path: str):
    async with aiohttp.ClientSession() as s:
        async with s.get(API_URL + path) as r:
            r.raise_for_status()
            return await r.json()

async def api_post(path: str, data: dict):
    async with aiohttp.ClientSession() as s:
        async with s.post(API_URL + path, json=data) as r:
            r.raise_for_status()
            return await r.json()


# ── Formatting helpers ──────────────────────────────────────────

def seat_label(pos: str) -> str:
    row, col = pos.split("-")
    return f"{chr(65 + int(row))}{int(col) + 1}"

def avail_label(avail: int) -> str:
    return f"⚠️ {avail} left" if avail < 15 else f"✅ {avail} seats"

def price_for(is_vip: bool) -> int:
    return VIP_PRICE if is_vip else STANDARD_PRICE


# ── /start ──────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("📱 Open Web App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("🤖 Book in Telegram", callback_data="choice:telegram")],
    ]
    text = "Welcome to *CinemaMax* 🎬\n\nHow would you like to book tickets?"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOICE

async def on_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if update.callback_query.data == "choice:telegram":
        ctx.user_data['page'] = 0
        return await show_gallery(update, ctx)
    return CHOICE


# ── Gallery ─────────────────────────────────────────────────────

async def show_gallery(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        movies = await api_get('/movies')
    except Exception:
        await update.callback_query.edit_message_text("❌ Could not reach API. Is the server running?")
        return GALLERY

    page = ctx.user_data.get('page', 0)
    total_pages = max(1, (len(movies) + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE)
    page_movies = movies[page*MOVIES_PER_PAGE : (page+1)*MOVIES_PER_PAGE]
    ctx.user_data['movies'] = movies

    keyboard = []
    for m in page_movies:
        star  = "⭐ " if m["is_blockbuster"] else ""
        label = f"{star}{m['title']}  [{m['genre']}]  ({m['show_count']} showings)"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"movie:{m['id']}:{m['title']}")])

    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if page < total_pages-1: nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page+1}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="back:start")])

    await update.callback_query.edit_message_text(
        f"🎬 *CinemaMax — Now Showing*\n\nPick a movie (Page {page+1}/{total_pages}):",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GALLERY

async def on_page_change(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    ctx.user_data['page'] = int(update.callback_query.data.split(":")[1])
    return await show_gallery(update, ctx)

async def on_movie_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    _, movie_id, title = update.callback_query.data.split(":", 2)
    ctx.user_data["movie_id"]    = int(movie_id)
    ctx.user_data["movie_title"] = title
    return await show_showtimes(update, ctx)


# ── Showtimes ───────────────────────────────────────────────────

async def show_showtimes(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        rows = await api_get(f"/showtimes/{ctx.user_data['movie_id']}")
    except Exception:
        await update.callback_query.edit_message_text("❌ Could not load showtimes.")
        return TIMES

    keyboard = []
    for s in rows:
        avail = s["available"]
        time  = str(s["show_time"])[:5]
        vip   = "★ VIP  " if s["is_vip"] else ""
        label = f"{vip}{s['hall_name']}  {time}  — {avail_label(avail)}"
        keyboard.append([InlineKeyboardButton(
            label,
            callback_data=f"show:{s['id']}:{s['hall_name']}:{time}:{1 if s['is_vip'] else 0}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back:gallery")])

    await update.callback_query.edit_message_text(
        f"🎭 *{ctx.user_data['movie_title']}*\n\nChoose a showtime:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TIMES

async def on_showtime_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    _, sid, hall, time, vip_flag = update.callback_query.data.split(":", 4)
    ctx.user_data.update(showtime_id=int(sid), hall=hall, time=time, is_vip=(vip_flag=="1"), selected=[])
    return await show_seat_map(update, ctx)


# ── Seat map ─────────────────────────────────────────────────────

async def show_seat_map(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    sid    = ctx.user_data["showtime_id"]
    is_vip = ctx.user_data["is_vip"]
    sel    = set(ctx.user_data.get("selected", []))
    rows   = 4 if is_vip else 8
    cols   = 6 if is_vip else 12

    try:
        booked = set(await api_get(f"/booked/{sid}"))
    except Exception:
        booked = set()

    keyboard = []
    header = [InlineKeyboardButton(str(c+1), callback_data="noop") for c in range(cols)]
    keyboard.append(header)

    for r in range(rows):
        row_btns = [InlineKeyboardButton(chr(65+r), callback_data="noop")]
        for c in range(cols):
            pos = f"{r}-{c}"
            if pos in booked:
                emoji, cb = "🔴", "noop"
            elif pos in sel:
                emoji, cb = "🟢", f"seat:deselect:{pos}"
            else:
                emoji, cb = "⬜", f"seat:select:{pos}"
            row_btns.append(InlineKeyboardButton(emoji, callback_data=cb))
        keyboard.append(row_btns)

    count  = len(sel)
    total  = count * price_for(is_vip)
    labels = sorted(seat_label(p) for p in sel)

    keyboard.append([
        InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
        InlineKeyboardButton("⬅️ Back",   callback_data="back:times"),
    ])

    header_text = (
        f"🎬 *{ctx.user_data['movie_title']}*{'  ★ VIP' if is_vip else ''}\n"
        f"📍 {ctx.user_data['hall']}  🕐 {ctx.user_data['time']}\n"
        f"⬜ Available  🟢 Selected  🔴 Booked\n\n"
        f"Selected: {', '.join(labels) if labels else '—'}\nTotal: ${total}.00"
    )
    await update.callback_query.edit_message_text(
        header_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SEATS

async def on_seat_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    _, action, pos = update.callback_query.data.split(":", 2)
    sel = ctx.user_data.setdefault("selected", [])
    if action == "select" and pos not in sel:   sel.append(pos)
    elif action == "deselect" and pos in sel:    sel.remove(pos)
    return await show_seat_map(update, ctx)


# ── Confirm & book ───────────────────────────────────────────────

async def on_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    sel = ctx.user_data.get("selected", [])
    if not sel:
        await update.callback_query.answer("❗ Select at least one seat first.", show_alert=True)
        return SEATS

    is_vip = ctx.user_data["is_vip"]
    total  = len(sel) * price_for(is_vip)
    labels = sorted(seat_label(p) for p in sel)

    ticket = (
        f"🎟 *Booking Summary*\n\n"
        f"🎬 *Film:* {ctx.user_data['movie_title']}\n"
        f"📍 *Hall:* {'★ VIP Platinum' if is_vip else ctx.user_data['hall']}\n"
        f"🕐 *Time:* {ctx.user_data['time']}\n"
        f"💺 *Seats:* {', '.join(labels)}\n"
        f"🎫 *Tickets:* {len(sel)} × ${price_for(is_vip)}.00\n"
        f"💰 *Total:* ${total}.00"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Pay & Book", callback_data="book"),
        InlineKeyboardButton("⬅️ Back",       callback_data="back:seats"),
    ]])
    await update.callback_query.edit_message_text(ticket, parse_mode="Markdown", reply_markup=keyboard)
    return CONFIRM

async def on_book(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    sid   = ctx.user_data["showtime_id"]
    sel   = ctx.user_data.get("selected", [])
    title = ctx.user_data["movie_title"]

    try:
        await api_post('/book', {"showtime_id": sid, "seats": sel})
        labels = sorted(seat_label(p) for p in sel)
        await update.callback_query.edit_message_text(
            f"✅ *Booking Confirmed!*\n\n🎬 {title}\n💺 Seats: {', '.join(labels)}\n\nEnjoy the show! 🍿\n\nType /start to book again.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"❌ Booking failed: {e}\n\nType /start to try again."
        )

    ctx.user_data.clear()
    return ConversationHandler.END


# ── Back navigation ──────────────────────────────────────────────

async def on_back(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    dest = update.callback_query.data.split(":")[1]
    if   dest == "start":   return await start(update, ctx)
    elif dest == "gallery": return await show_gallery(update, ctx)
    elif dest == "times":   return await show_showtimes(update, ctx)
    elif dest == "seats":   return await show_seat_map(update, ctx)

async def noop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


# ── Main ─────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOICE:  [CallbackQueryHandler(on_choice,  pattern=r"^choice:")],
            GALLERY: [
                CallbackQueryHandler(on_movie_selected, pattern=r"^movie:"),
                CallbackQueryHandler(on_page_change,    pattern=r"^page:"),
                CallbackQueryHandler(on_back,           pattern=r"^back:start"),
            ],
            TIMES: [
                CallbackQueryHandler(on_showtime_selected, pattern=r"^show:"),
                CallbackQueryHandler(on_back,              pattern=r"^back:"),
            ],
            SEATS: [
                CallbackQueryHandler(on_seat_toggle, pattern=r"^seat:"),
                CallbackQueryHandler(on_confirm,     pattern=r"^confirm$"),
                CallbackQueryHandler(on_back,        pattern=r"^back:"),
                CallbackQueryHandler(noop,           pattern=r"^noop$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(on_book, pattern=r"^book$"),
                CallbackQueryHandler(on_back, pattern=r"^back:"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    )
    app.add_handler(conv)
    print("✅ CinemaMax bot running…  (Ctrl-C to stop)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
