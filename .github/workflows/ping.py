import os
import sys
import time
from playwright.sync_api import sync_playwright

# Cambia esto por la URL de tu app
STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "https://cronograma-mtto-cha-0019-sypmfynhwwrmomdv277ypw.streamlit.app/")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Visitando {STREAMLIT_URL} ...")
        page.goto(STREAMLIT_URL, timeout=60000, wait_until="networkidle")

        # Si la app estaba dormida, aparece un botón para despertarla
        try:
            wake_button = page.get_by_text("Yes, get this app back up!", exact=False)
            if wake_button.is_visible(timeout=5000):
                print("App dormida detectada. Haciendo clic para despertar...")
                wake_button.click()
                # Esperamos a que la app termine de arrancar
                time.sleep(30)
                page.wait_for_load_state("networkidle", timeout=60000)
                print("App despertada correctamente ✅")
            else:
                print("App ya estaba despierta ✅")
        except Exception:
            print("No se encontró botón de sleep. App ya estaba despierta ✅")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error inesperado: {e}")
        sys.exit(1)
