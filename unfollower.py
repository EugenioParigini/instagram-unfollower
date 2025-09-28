# -*- coding: utf-8 -*-
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- CONFIGURACIÓN ---
# Las credenciales se obtienen de las variables de entorno (GitHub Secrets)
# ¡NUNCA escribas tu usuario y contraseña directamente aquí!
INSTAGRAM_USERNAME = os.environ.get("INSTA_USER")
INSTAGRAM_PASSWORD = os.environ.get("INSTA_PASS")

# Lista de usuarios que NUNCA quieres dejar de seguir.
# Añade aquí los nombres de usuario que quieres proteger.
WHITELIST = ["instagram", "google", "nasa"]

# --- LÓGICA DEL SCRIPT ---

class InstagramUnfollowerBot:
    """
    Bot para automatizar el proceso de dejar de seguir a usuarios
    de Instagram que no te siguen de vuelta.
    """
    def __init__(self, username, password):
        self.username = username
        self.password = password
        chrome_options = Options()
        # Estas opciones son necesarias para ejecutar en un entorno de servidor como GitHub Actions
        chrome_options.add_argument("--headless") # No abre una ventana de navegador visual
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def _random_sleep(self, min_sec=2, max_sec=5):
        """Espera un tiempo aleatorio para simular comportamiento humano."""
        time.sleep(random.uniform(min_sec, max_sec))

    def login(self):
        """Inicia sesión en Instagram."""
        print("Iniciando sesión...")
        self.driver.get("https://www.instagram.com/accounts/login/")
        
        # Esperar a que los campos de usuario y contraseña estén disponibles
        user_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
        pass_input = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))

        user_input.send_keys(self.username)
        self._random_sleep(1, 2)
        pass_input.send_keys(self.password)
        self._random_sleep(1, 2)
        
        # El botón de login a veces cambia. Usamos un selector más robusto.
        login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
        print("Login exitoso.")
        self._random_sleep(5, 8) # Espera larga para que cargue la página principal

        # Manejar pop-ups como "Guardar información" o "Activar notificaciones"
        self._handle_popups()

    def _handle_popups(self):
        """Maneja los pop-ups que aparecen después de iniciar sesión."""
        try:
            # Pop-up "Guardar tu información de inicio de sesión"
            save_info_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Ahora no']")))
            save_info_button.click()
            print("Cerrado pop-up de 'Guardar información'.")
            self._random_sleep(3, 5)
        except TimeoutException:
            print("No se encontró el pop-up de 'Guardar información'.")

        try:
            # Pop-up "Activar notificaciones"
            notifications_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Ahora no']")))
            notifications_button.click()
            print("Cerrado pop-up de 'Notificaciones'.")
            self._random_sleep(3, 5)
        except TimeoutException:
            print("No se encontró el pop-up de 'Notificaciones'.")

    def _scroll_and_get_users(self, dialog_xpath):
        """
        Abre un diálogo (seguidores/seguidos), hace scroll hasta el final
        y extrae todos los nombres de usuario.
        """
        users = set()
        try:
            dialog = self.wait.until(EC.presence_of_element_located((By.XPATH, dialog_xpath)))
            
            last_height = 0
            while True:
                # Extraer usuarios visibles
                user_elements = dialog.find_elements(By.XPATH, ".//a[@role='link' and not(@href='')]")
                for el in user_elements:
                    # Nos aseguramos de que tenga un texto y no sea un enlace vacío.
                    if el.text:
                         users.add(el.text)

                # Hacer scroll
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                self._random_sleep(2, 3) # Pausa para cargar más usuarios
                
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", dialog)
                
                if new_height == last_height:
                    break # Se llegó al final
                last_height = new_height
        
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error al hacer scroll y obtener usuarios: {e}")

        return users


    def get_followers_and_following(self):
        """Navega al perfil y obtiene las listas de seguidores y seguidos."""
        print(f"Navegando al perfil de {self.username}...")
        profile_url = f"https://www.instagram.com/{self.username}/"
        self.driver.get(profile_url)

        # Obtener seguidores
        print("Obteniendo lista de seguidores...")
        followers_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[@href='/{self.username}/followers/']")))
        followers_link.click()
        # El diálogo de seguidores/seguidos suele estar dentro de un div con rol 'dialog'
        followers = self._scroll_and_get_users("//div[@role='dialog']//div[contains(@class, '_aano')]")
        print(f"Encontrados {len(followers)} seguidores.")
        # Cerrar el diálogo
        self.driver.find_element(By.XPATH, "//div[@role='dialog']/div/div/div/div[1]/div/div[2]/button").click()
        self._random_sleep()

        # Obtener seguidos
        print("Obteniendo lista de seguidos...")
        following_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[@href='/{self.username}/following/']")))
        following_link.click()
        following = self._scroll_and_get_users("//div[@role='dialog']//div[contains(@class, '_aano')]")
        print(f"Encontrados {len(following)} seguidos.")
        # Cerrar el diálogo
        self.driver.find_element(By.XPATH, "//div[@role='dialog']/div/div/div/div[1]/div/div[2]/button").click()
        self._random_sleep()
        
        return followers, following

    def unfollow_users(self, users_to_unfollow):
        """Deja de seguir a una lista de usuarios."""
        if not users_to_unfollow:
            print("No hay usuarios para dejar de seguir. ¡Buen trabajo!")
            return

        # Seleccionar una cantidad aleatoria para dejar de seguir en esta ejecución
        unfollow_count = random.randint(30, 40)
        print(f"Se dejarán de seguir a {unfollow_count} usuarios en esta sesión.")
        
        # Mezclar la lista para que no sea siempre en el mismo orden
        random.shuffle(users_to_unfollow)
        
        unfollowed_this_session = 0
        for user in users_to_unfollow:
            if unfollowed_this_session >= unfollow_count:
                print("Límite de unfollows para esta sesión alcanzado.")
                break
            
            print(f"Intentando dejar de seguir a: {user}")
            self.driver.get(f"https://www.instagram.com/{user}/")
            self._random_sleep(3, 6)
            
            try:
                # Buscar el botón "Siguiendo" o similar
                following_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Siguiendo' or text()='Following']"))
                )
                following_button.click()
                self._random_sleep(1, 3)

                # Confirmar el "Dejar de seguir"
                confirm_unfollow_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Dejar de seguir' or text()='Unfollow']"))
                )
                confirm_unfollow_button.click()
                print(f"Se ha dejado de seguir a {user}.")
                unfollowed_this_session += 1
                self._random_sleep(10, 20) # ¡Pausa larga e importante entre unfollows!

            except TimeoutException:
                print(f"No se pudo encontrar el botón de 'Siguiendo' para {user}. Puede que ya no lo sigas o que el perfil sea privado.")
            except Exception as e:
                print(f"Ocurrió un error inesperado al intentar dejar de seguir a {user}: {e}")

    def run(self):
        """Ejecuta el flujo completo del bot."""
        # Pausa inicial aleatoria para no ejecutar siempre a la misma hora exacta
        initial_wait = random.randint(0, 30) * 60 # Espera entre 0 y 30 minutos
        print(f"Esperando {initial_wait / 60} minutos antes de empezar...")
        time.sleep(initial_wait)
        
        try:
            self.login()
            followers, following = self.get_followers_and_following()
            
            # Los nombres pueden variar ligeramente, normalizamos a minúsculas
            followers_lower = {f.lower() for f in followers}
            following_lower = {f.lower() for f in following}
            whitelist_lower = {w.lower() for w in WHITELIST}
            
            # Calcular quiénes no te siguen de vuelta
            not_following_back = list(following_lower - followers_lower)
            
            # Quitar a los usuarios de la whitelist
            final_unfollow_list = [user for user in not_following_back if user not in whitelist_lower]
            
            print(f"\n--- Resumen ---")
            print(f"Total de seguidores: {len(followers)}")
            print(f"Total de seguidos: {len(following)}")
            print(f"Usuarios en la whitelist: {len(whitelist_lower)}")
            print(f"Usuarios a dejar de seguir (potenciales): {len(final_unfollow_list)}")
            
            self.unfollow_users(final_unfollow_list)
            
        except Exception as e:
            print(f"Ha ocurrido un error general en la ejecución: {e}")
        finally:
            print("Cerrando el navegador.")
            self.driver.quit()

if __name__ == "__main__":
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("Error: Las variables de entorno INSTA_USER y INSTA_PASS no están configuradas.")
    else:
        bot = InstagramUnfollowerBot(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        bot.run()
