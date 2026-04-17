import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), BaseHTTPRequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(callback))

    print("Bot running...")
    app.run_polling()
