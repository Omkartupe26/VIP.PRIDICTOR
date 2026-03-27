from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlite3
import random
import os
BOT_TOKEN = os.getenv("BOT_TOKEN_2")

# DATABASE
conn = sqlite3.connect("game_history.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
id INTEGER PRIMARY KEY AUTOINCREMENT,
number INTEGER,
color TEXT,
size TEXT
)
""")
conn.commit()

last_prediction = None

green = [1,3,7,9]
red = [2,4,6,8]
violet = [0,5]

def get_color(n):
    if n in green:
        return "Green"
    elif n in red:
        return "Red"
    else:
        return "Violet"

def get_size(n):
    return "Big" if n >= 5 else "Small"

def get_last_numbers(limit=20):
    cursor.execute("SELECT number FROM history ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    return [r[0] for r in rows]

def strategy_engine(user_numbers):
    global last_prediction

    history_numbers = get_last_numbers(20)
    numbers = user_numbers + history_numbers

    if len(numbers) < 3:
        # Not enough data fallback
        n = random.randint(0,9)
        return n, 40, ["Fallback Random"]

    score = {i:0 for i in range(10)}
    strategies_used = []

    try:
        # Missing number strategy
        for i in range(10):
            if i not in numbers[-10:]:
                score[i] += 3
        strategies_used.append("Missing")

        # Low frequency
        freq = {i:0 for i in range(10)}
        for n in numbers[-15:]:
            freq[n] += 1
        least_common = min(freq, key=freq.get)
        score[least_common] += 3
        strategies_used.append("LowFreq")

        # Opposite number
        last = numbers[-1]
        opposite = 9 - last
        score[opposite] += 2
        strategies_used.append("Opposite")

        # Neighbor strategy
        neighbors = [(last - 1) % 10, (last + 1) % 10]
        for n in neighbors:
            score[n] += 2
        strategies_used.append("Neighbor")

        # Double break
        if len(numbers) >= 2 and numbers[-1] == numbers[-2]:
            for i in range(10):
                if i != numbers[-1]:
                    score[i] += 2
            strategies_used.append("DoubleBreak")

        # Trend strategy
        if len(numbers) >= 4:
            if numbers[-1] > numbers[-2] > numbers[-3]:
                score[(numbers[-1] + 1) % 10] += 2
                strategies_used.append("UpTrend")
            elif numbers[-1] < numbers[-2] < numbers[-3]:
                score[(numbers[-1] - 1) % 10] += 2
                strategies_used.append("DownTrend")

        # Rebound
        recent = numbers[-12:]
        for i in range(10):
            if recent.count(i) == 0:
                score[i] += 2
        strategies_used.append("Rebound")

        # Random safety
        score[random.randint(0,9)] += 1

    except:
        # Emergency fallback
        n = random.randint(0,9)
        return n, 35, ["Safe Mode"]

    best = max(score, key=score.get)
    confidence = min(score[best] * 10, 95)

    return best, confidence, strategies_used

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Smart Prediction Bot Started 🚀\n\n"
        "/predict 1 2 3 4 5\n"
        "/result 7\n"
        "/stats"
    )

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_prediction
    try:
        user_numbers = list(map(int, context.args))

        if len(user_numbers) == 0:
            await update.message.reply_text("Send numbers like:\n/predict 1 2 3 4 5")
            return

        best, confidence, strategies = strategy_engine(user_numbers)
        last_prediction = best

        msg = f"""
Prediction Ready

Number: {best}
Color: {get_color(best)}
Size: {get_size(best)}
Confidence: {confidence}%

Strategies: {", ".join(strategies)}
"""
        await update.message.reply_text(msg)

    except:
        await update.message.reply_text("Use numbers only.\nExample:\n/predict 3 7 2 9")

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_prediction
    try:
        number = int(context.args[0])
        color = get_color(number)
        size = get_size(number)

        cursor.execute(
            "INSERT INTO history (number, color, size) VALUES (?, ?, ?)",
            (number, color, size)
        )
        conn.commit()

        if last_prediction is None:
            await update.message.reply_text("No prediction yet.")
            return

        predicted_color = get_color(last_prediction)
        predicted_size = get_size(last_prediction)

        win_types = []

        if number == last_prediction:
            win_types.append("Number")
        if color == predicted_color:
            win_types.append("Color")
        if size == predicted_size:
            win_types.append("Size")

        if win_types:
            msg = f"WIN ✅ ({', '.join(win_types)})"
        else:
            msg = "LOSS ❌"

        await update.message.reply_text(msg)

    except:
        await update.message.reply_text("Example:\n/result 7")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT COUNT(*) FROM history")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT number FROM history ORDER BY id DESC LIMIT 10")
    last = cursor.fetchall()

    numbers = [str(x[0]) for x in last]

    msg = f"""
Bot Stats
Rounds: {total}
Recent: {' '.join(numbers)}
"""
    await update.message.reply_text(msg)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("predict", predict))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("stats", stats))

print("Bot is running...")
app.run_polling()
