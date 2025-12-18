from Prueba import Scraper
import pandas as pd

# =========================
# CONFIGURACIÓN FIJA
# =========================
TARGET_USERNAME = "nayeli.nxx"
CHROMEDRIVER_PATH = r"D:\Usuario\Documentos\U\SEMESTRE_6\Desarrollo\Prueba\drivers\chromedriver.exe"
COOKIES_PATH = r"D:\Usuario\Documentos\U\SEMESTRE_6\Desarrollo\Prueba\cookies.json"

# =========================
# SCRAPING
# =========================
def scrape():
    print("Iniciando scraper...")

    scraper = Scraper(
        target=TARGET_USERNAME,
        chromedriver_path=CHROMEDRIVER_PATH,
        cookies_path=COOKIES_PATH
    )

    # 1️⃣ Obtener SOLO 100 seguidos
    seguidos = scraper.get_users(
        group="following",
        limit=100,
        verbose=True
    )

    print(f"\nTotal de seguidos obtenidos: {len(seguidos)}")

    # 2️⃣ Extraer información completa de cada perfil
    perfiles = []
    for user in seguidos:
        info = scraper.get_profile_info(user)
        perfiles.append(info)

    scraper.close()

    # 3️⃣ Guardar resultados en DataFrame
    df = pd.DataFrame(perfiles)

    print("\n=== RESULTADOS ===")
    print(df.to_string(index=False))

    # (opcional) Guardar a CSV
    df.to_csv("seguidos_perfiles.csv", index=False, encoding="utf-8-sig")
    print("\nArchivo guardado: seguidos_perfiles.csv")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    scrape()