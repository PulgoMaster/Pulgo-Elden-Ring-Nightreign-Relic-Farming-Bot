"""
Entry point for the Elden Ring Nightreign Relic Bot.
Run this file to launch the UI.

  python main.py
"""

from ui.app import RelicBotApp


def main():
    app = RelicBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
