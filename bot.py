from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlite3
import random
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

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

    score = {i:0 for i in range(10)}
    strategies_used = []

    # Missing number strategy
    for i in range(10):
        if i not in numbers[-10:]:
            score[i] += 3
    strategies_used.append("Missing Strategy")

    # Low frequency strategy
    freq = {i:0 for i in range(10)}
    for n in numbers[-15:]:
        freq[n] += 1
    least_common = min(freq, key=freq.get)
    score[least_common] += 3
    strategies_used.append("Low Frequency Strategy")

    # Opposite last number
    last = numbers[-1]
    opposite = 9 - last
    score[opposite] += 2
    strategies_used.append("Opposite Strategy")

    # Color streak break
    colors = [get_color(n) for n in numbers[-5:]]
    if len(colors) == 5 and colors.count(colors[0]) == 5:
        streak_color = colors[0]
        for i in range(10):
            if get_color(i) != streak_color:
                score[i] += 4
        strategies_used.append("Color Streak Break")

    # Size streak break
    sizes = [get_size(n) for n in numbers[-5:]]
    if len(sizes) == 5 and sizes.count(sizes[0]) == 5:
        streak_size = sizes[0]
        for i in range(10):
            if get_size(i) != streak_size:
                score[i] += 3
        strategies_used.append("Size Streak Break")

    # Avoid repeating prediction
    if last_prediction is not None:
        score[last_prediction] -= 5
        strategies_used.append("Anti Repeat")

    # Random safety
    score[random.randint(0,9)] += 1
    strategies_used.append("Random Safety")

    best = max(score, key=score.get)
    confidence = min(score[best] * 10, 95)

    return best, confidence, strategies_used

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Smart Prediction Bot Started 🚀\n\n"
        "Use:\n"
        "/predict 9 9 3 6 2\n"
        "/result 7\n"
        "/stats"
    )

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_prediction

    try:
        user_numbers = list(map(int, context.args))

        best, confidence, strategies = strategy_engine(user_numbers)

        last_prediction = best

        msg = f"""
Prediction Ready

Number: {best}
Color: {get_color(best)}
Size: {get_size(best)}

Confidence: {confidence}%

Strategies Used:
{", ".join(strategies)}
"""
        await update.message.reply_text(msg)

    except:
        await update.message.reply_text("Example:\n/predict 9 9 3 6 2")

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

        predicted_number = last_prediction
        predicted_color = get_color(predicted_number)
        predicted_size = get_size(predicted_number)

        win_types = []

        if number == predicted_number:
            win_types.append("Number")

        if color == predicted_color:
            win_types.append("Color")

        if size == predicted_size:
            win_types.append("Size")

        if win_types:
            msg = f"WIN ✅ ({', '.join(win_types)} matched)"
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

Rounds Recorded: {total}
Recent Results: {' '.join(numbers)}
"""
    await update.message.reply_text(msg)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("predict", predict))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("stats", stats))

app.run_polling()
